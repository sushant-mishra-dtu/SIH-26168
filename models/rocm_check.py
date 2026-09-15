"""Training-host probe.

    python -m models.rocm_check
    python -m models.rocm_check --out eval/figures/train_host/rx7700xt.json

Answers one question about a machine that claims to be able to train: *does PyTorch actually
reach the GPU, and how fast is it once it gets there?* It prints a report and, with ``--out``,
writes a stamped JSON so the answer is a recorded measurement rather than a memory.

This exists because of the D-116 rule -- record first, then set. The team phone stopped being
"assumed 100 Hz" the day it was measured at 125.0 Hz; a training box should not get a softer
standard. Nothing in `docs/TRAINING_ENVIRONMENT.md` is claimed as measured until this has run on
the host and its output is committed beside the claim.

Imports torch *inside* the functions that need it, like the rest of `models/`, so this module and
its ``--help`` still work in the CI job that has no torch.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from idr.stamp import make_stamp

SEED = 26168

# One matmul of this size is 2*N^3 flops. Big enough that kernel launch overhead is noise on any
# GPU worth training on, small enough that fp32 operands fit in 8 GB with room to spare.
BENCH_N = 4096
BENCH_WARMUP = 3
BENCH_ITERS = 20

# gfx1101 is Navi 32 -- the RX 7700 XT and 7800 XT. It is not on ROCm's officially supported list;
# the override maps it onto the gfx1100 (7900 XTX) kernels, which is the ordinary way these cards
# are made to work. Recorded here so the probe can say whether the host has it set.
KNOWN_OVERRIDES = {"gfx1101": "11.0.0", "gfx1102": "11.0.0", "gfx1103": "11.0.0"}


@dataclass
class HostReport:
    """What the probe found. Every field is measured on the host or read from it, never assumed."""

    stamp: dict[str, object]
    is_wsl: bool
    kernel: str
    rocm_tools: dict[str, str | None]
    gfx_override: str | None
    torch: dict[str, object] = field(default_factory=dict)
    devices: list[dict[str, object]] = field(default_factory=list)
    benchmarks: list[dict[str, object]] = field(default_factory=list)
    deterministic_matmul: bool | None = None
    notes: list[str] = field(default_factory=list)


def is_wsl() -> bool:
    """True on WSL. The kernel string carries 'microsoft' on both WSL1 and WSL2."""
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _run(cmd: list[str]) -> str | None:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=30)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def rocm_tools() -> dict[str, str | None]:
    """Which ROCm userspace tools are on PATH, and the agent list rocminfo reports.

    A torch that cannot see the GPU with rocminfo present is a torch problem; a torch that cannot
    see the GPU with rocminfo absent is an install problem. The distinction is the first thing you
    want when this fails, so it is collected whether or not torch imports.
    """
    found: dict[str, str | None] = {
        tool: shutil.which(tool) for tool in ("rocminfo", "rocm-smi", "hipcc", "amd-smi")
    }
    if found["rocminfo"]:
        out = _run(["rocminfo"])
        if out:
            agents = sorted({
                line.split()[-1] for line in out.splitlines() if "gfx" in line and "Name:" in line
            })
            found["rocminfo_agents"] = ",".join(agents) if agents else "none found"
    return found


def probe_torch(report: HostReport) -> None:
    """Fill the torch and device fields. Leaves them empty if torch is not installed."""
    try:
        import torch
    except ImportError:
        report.notes.append(
            "torch is not installed -- `pip install -e \".[ml]\"` against the ROCm wheel index. "
            "See docs/TRAINING_ENVIRONMENT.md section 2."
        )
        return

    report.torch = {
        "version": torch.__version__,
        "hip": torch.version.hip,  # set on a ROCm build, None on a CUDA or CPU build
        "cuda": torch.version.cuda,  # None on a ROCm build
        "is_available": bool(torch.cuda.is_available()),
    }

    if not torch.cuda.is_available():
        report.notes.append(
            "torch imports but reports no device. On a ROCm build with rocminfo listing an agent "
            "this is usually the missing HSA_OVERRIDE_GFX_VERSION for an unsupported gfx target."
        )
        return

    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        arch = getattr(props, "gcnArchName", "")
        entry: dict[str, object] = {
            "index": i,
            "name": props.name,
            "arch": arch,
            "total_memory_gib": round(props.total_memory / 1024**3, 2),
            "multi_processor_count": props.multi_processor_count,
        }
        base = arch.split(":")[0]
        if base in KNOWN_OVERRIDES and report.gfx_override is None:
            entry["override_expected"] = KNOWN_OVERRIDES[base]
            report.notes.append(
                f"device {i} reports {base}, which is not officially supported; "
                f"if a kernel faults, export HSA_OVERRIDE_GFX_VERSION={KNOWN_OVERRIDES[base]}."
            )
        report.devices.append(entry)


def benchmark(device: str = "cuda") -> list[dict[str, object]]:
    """Sustained matmul throughput, fp32 and fp16, as TFLOP/s.

    Not a training figure and not comparable to a vendor number -- it is a floor check. A card that
    cannot beat a laptop CPU here has a broken install, and that is worth finding out before a
    multi-hour run rather than during one.
    """
    import torch

    results: list[dict[str, object]] = []
    flops = 2.0 * BENCH_N**3
    for dtype, label in ((torch.float32, "fp32"), (torch.float16, "fp16")):
        try:
            a = torch.randn(BENCH_N, BENCH_N, device=device, dtype=dtype)
            b = torch.randn(BENCH_N, BENCH_N, device=device, dtype=dtype)
            for _ in range(BENCH_WARMUP):
                a @ b
            torch.cuda.synchronize()
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record()
            for _ in range(BENCH_ITERS):
                a @ b
            end.record()
            torch.cuda.synchronize()
            seconds = start.elapsed_time(end) / 1000.0 / BENCH_ITERS
            results.append({
                "dtype": label,
                "n": BENCH_N,
                "seconds_per_matmul": round(seconds, 6),
                "tflops": round(flops / seconds / 1e12, 2),
            })
            del a, b
            torch.cuda.empty_cache()
        except RuntimeError as exc:  # a kernel fault or an OOM, both worth recording verbatim
            results.append({"dtype": label, "n": BENCH_N, "error": str(exc)[:400]})
    return results


def deterministic_matmul(device: str = "cuda") -> bool:
    """Whether the same seed twice gives bit-identical output on this device.

    `idr.stamp.seed_everything` asks for deterministic algorithms with `warn_only=True`, so a
    kernel with no deterministic implementation falls back silently rather than raising. That is
    the right default for the harness and the wrong assumption for a submission number, so the
    answer is measured rather than trusted -- see docs/TRAINING_ENVIRONMENT.md section 5.
    """
    import torch

    def once() -> torch.Tensor:
        torch.manual_seed(SEED)
        torch.cuda.manual_seed_all(SEED)
        x = torch.randn(512, 512, device=device)
        w = torch.randn(512, 512, device=device)
        return (x @ w).sum(dim=0)

    return bool(torch.equal(once(), once()))


def collect() -> HostReport:
    report = HostReport(
        stamp=asdict(make_stamp(SEED)),
        is_wsl=is_wsl(),
        kernel=platform.release(),
        rocm_tools=rocm_tools(),
        gfx_override=os.environ.get("HSA_OVERRIDE_GFX_VERSION"),
    )
    probe_torch(report)
    if report.devices:
        report.benchmarks = benchmark()
        try:
            report.deterministic_matmul = deterministic_matmul()
        except RuntimeError as exc:
            report.notes.append(f"determinism check faulted: {str(exc)[:200]}")
    return report


def render(report: HostReport) -> str:
    lines = ["training host", "=" * 60]
    lines.append(f"  platform          {report.stamp['platform']}")
    lines.append(f"  kernel            {report.kernel}{'  (WSL)' if report.is_wsl else ''}")
    lines.append(f"  python            {report.stamp['python']}")
    lines.append(f"  commit            {report.stamp['commit']}")
    lines.append(f"  HSA_OVERRIDE      {report.gfx_override or 'unset'}")
    lines.append("")
    lines.append("rocm userspace")
    for tool, where in report.rocm_tools.items():
        lines.append(f"  {tool:<17} {where or 'NOT FOUND'}")
    lines.append("")
    if not report.torch:
        lines.append("torch             NOT INSTALLED")
    else:
        lines.append("torch")
        lines.append(f"  version           {report.torch['version']}")
        lines.append(f"  hip / cuda        {report.torch['hip']} / {report.torch['cuda']}")
        lines.append(f"  device visible    {report.torch['is_available']}")
    for dev in report.devices:
        lines.append("")
        lines.append(f"device {dev['index']}")
        lines.append(f"  name              {dev['name']}")
        lines.append(f"  arch              {dev['arch']}")
        lines.append(f"  memory            {dev['total_memory_gib']} GiB")
        lines.append(f"  compute units     {dev['multi_processor_count']}")
    for bench in report.benchmarks:
        lines.append("")
        if "error" in bench:
            lines.append(f"matmul {bench['dtype']}      FAILED: {bench['error']}")
        else:
            lines.append(
                f"matmul {bench['dtype']} n={bench['n']}   "
                f"{bench['tflops']} TFLOP/s  ({bench['seconds_per_matmul'] * 1e3:.1f} ms)"
            )
    if report.deterministic_matmul is not None:
        lines.append("")
        verdict = "yes" if report.deterministic_matmul else "NO -- see section 5"
        lines.append(f"seeded run is bit-identical   {verdict}")
    if report.notes:
        lines.append("")
        lines.append("notes")
        for note in report.notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the report as stamped JSON here; commit it beside the claim it supports",
    )
    args = parser.parse_args(argv)

    report = collect()
    print(render(report))

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
        if not report.stamp["commit"] or str(report.stamp["commit"]).endswith("-dirty"):
            print("WARNING: dirty tree -- this report names no commit it can be regenerated from.")

    return 0 if report.devices else 1


if __name__ == "__main__":
    sys.exit(main())
