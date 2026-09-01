"""GNSS cadence, and whether the paired `V-` track can stand in as ground truth.

**Why this is a tracked tool and not a scratch script.** The measurement it produces is the
evidence for a protocol change: `docs/EVALUATION.md` §2 says "1 Hz GNSS", the `S-` smartphone GPS
updates roughly every nine seconds, and CTE/CRSE/drift-% are all defined on 1 s epochs. Under §7.1
and D-042 a number whose provenance is a file on one laptop is deleted rather than debugged, so
the number that moves the protocol has to come from something committed, stamped and re-runnable.

Two artefacts, both stamped:

* ``gnss_cadence.csv`` -- per stem: distinct `S-` fixes, span, median and maximum gap. This is the
  measurement that says the protocol as drafted is not loadable.
* ``truth_alignment.csv`` -- per stem: the residual between the paired 10 Hz `V-` VBOX track and
  the `S-` stream's own fixes. This is the measurement that says the replacement is sound. Two
  receivers quoted at ±3 m, differenced, should agree to a few metres; a misalignment of even one
  second puts ~16 m of motorway into the residual, so the check is sharp.
* ``copy_divergence.csv`` -- every stem that ships twice in the synchronised folder under two
  different checksums. Found while wiring the pairing and reported here because it bears on the
  same gate: all 72 `S-` stems diverge, no `V-` stem does, and `load_split` currently picks
  between them by glob order.

Run::

    python -m eval.cadence --data-root data --out-dir eval/figures

Protocol: `docs/EVALUATION.md` §1.2, §2. Truth loader: `eval/loaders/truth.py`.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from eval.loaders.io_vnbd import Sequence, load_sequence
from eval.loaders.truth import (
    DEFAULT_MANIFEST,
    AlignmentReport,
    CopyDivergence,
    TruthPairingError,
    align_to_sequence,
    divergent_copies,
    load_truth,
    manifest_path_for,
    paired_truth_path,
)
from eval.splits import TRAIN, test_sequences
from idr.stamp import seed_everything


@dataclass(frozen=True)
class CadenceRow:
    """What one `S-` stem's GPS actually does, as opposed to what the protocol assumed."""

    sequence: str
    split: str
    n_samples: int
    imu_duration_s: float
    n_fixes: int
    fix_span_s: float
    median_gap_s: float
    max_gap_s: float
    meets_1hz: bool


def measure_cadence(seq: Sequence) -> CadenceRow:
    """Fix cadence for one loaded sequence.

    Gaps come from the fix timestamps, not from differencing indices: fixes are ~9 s apart and
    unevenly spaced, so an index difference says nothing about elapsed time.
    """
    t = seq.fix_times_s()
    gaps = np.diff(t) if t.size > 1 else np.array([np.nan])
    median_gap = float(np.median(gaps))
    return CadenceRow(
        sequence=seq.name,
        split=seq.split,
        n_samples=seq.n_samples,
        imu_duration_s=seq.duration_s,
        n_fixes=int(t.size),
        fix_span_s=float(t[-1] - t[0]) if t.size > 1 else 0.0,
        median_gap_s=median_gap,
        max_gap_s=float(np.max(gaps)) if t.size > 1 else float("nan"),
        # 1.5 s, not 1.0: a 1 Hz stream jitters a little, and the question this answers is
        # "does this stem update every second or every nine", which no tolerance in between
        # changes the answer to.
        meets_1hz=bool(t.size > 1 and median_gap <= 1.5),
    )


def _fixed(value: object) -> object:
    """Six significant figures on floats into a CSV, so the artefact is byte-reproducible.

    Same reason as `eval.allan._fixed`: the last digits of a float move between numpy/BLAS builds,
    and Gate 0's "same commit and seed -> identical output" check must fail on a real difference
    rather than on a machine one.
    """
    return f"{value:.6g}" if isinstance(value, float) else value


def _write_csv(
    path: Path,
    rows: list,
    caption: str,
    *,
    derived: dict[str, Callable[[object], object]] | None = None,
) -> None:
    """Write a dataclass table, plus any derived verdicts named in ``derived``.

    Verdicts are properties rather than fields, and `asdict` drops those -- which would have left
    `truth_alignment.csv` carrying six residual numbers and not the one column saying whether the
    stem may be graded against `V-` truth at all. The artefact has to answer the question it was
    generated to answer without the reader recomputing a threshold from memory.
    """
    extra = derived or {}
    fields = [f.name for f in type(rows[0]).__dataclass_fields__.values()]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# {caption}"])
        w.writerow(fields + list(extra))
        for row in rows:
            values = [_fixed(v) for v in asdict(row).values()]
            w.writerow(values + [_fixed(fn(row)) for fn in extra.values()])


def summarise(
    cadence: list[CadenceRow],
    alignment: list[AlignmentReport],
    divergence: list[CopyDivergence] | None = None,
) -> dict[str, object]:
    """The handful of numbers the DECISION_LOG row and EVALUATION.md section 2 quote."""
    medians = [r.median_gap_s for r in cadence if np.isfinite(r.median_gap_s)]
    usable = [a for a in alignment if a.is_usable]
    residuals = [a.residual_median_m for a in alignment if np.isfinite(a.residual_median_m)]
    diverging = divergence or []
    return {
        "n_sequences": len(cadence),
        "s_gnss_median_gap_s": float(np.median(medians)) if medians else float("nan"),
        "s_gnss_max_gap_s": float(max(r.max_gap_s for r in cadence)) if cadence else float("nan"),
        "n_meeting_1hz": sum(r.meets_1hz for r in cadence),
        "n_aligned": len(alignment),
        "n_alignment_usable": len(usable),
        "truth_residual_median_m": float(np.median(residuals)) if residuals else float("nan"),
        "truth_residual_worst_median_m": float(max(residuals)) if residuals else float("nan"),
        "n_divergent_s_copies": sum(d.stream == "S-" for d in diverging),
        "n_divergent_v_copies": sum(d.stream == "V-" for d in diverging),
    }


def run(
    sequences: tuple[str, ...], data_root: Path, manifest: Path, *, skip_truth: bool = False
) -> tuple[list[CadenceRow], list[AlignmentReport], list[str]]:
    """Measure every named stem. Problems are collected and reported, not raised.

    A stem whose paired file is missing or whose alignment fails is a finding about the protocol,
    and the run that discovers it should still report the other seventy.
    """
    cadence: list[CadenceRow] = []
    alignment: list[AlignmentReport] = []
    problems: list[str] = []

    for name in sequences:
        try:
            # strict_checksum off: every `S-` stem ships as two different files and the
            # categorised copy is chosen deliberately. See truth.divergent_copies.
            path = manifest_path_for(
                name, "S-", data_root, manifest=manifest, strict_checksum=False
            )
            seq = load_sequence(path, name)
        except (TruthPairingError, OSError, ValueError) as exc:
            problems.append(f"{name}: could not load 'S-' stream: {exc}")
            continue
        cadence.append(measure_cadence(seq))

        if skip_truth:
            continue
        try:
            truth = load_truth(paired_truth_path(name, data_root, manifest=manifest), name)
            alignment.append(align_to_sequence(seq, truth))
        except (TruthPairingError, OSError, ValueError) as exc:
            problems.append(f"{name}: no usable 'V-' truth: {exc}")

    return cadence, alignment, problems


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data-root", type=Path, default=Path("data"))
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out-dir", type=Path, default=Path("eval/figures"))
    p.add_argument("--seed", type=int, default=26168)
    p.add_argument(
        "--sequences",
        nargs="+",
        default=None,
        help="stems to measure (default: the frozen split -- held-out plus train)",
    )
    p.add_argument(
        "--skip-truth",
        action="store_true",
        help="measure 'S-' cadence only, without opening the paired 'V-' files",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp = seed_everything(args.seed)
    names = tuple(args.sequences) if args.sequences else tuple(test_sequences()) + tuple(TRAIN)

    cadence, alignment, problems = run(
        names, args.data_root, args.manifest, skip_truth=args.skip_truth
    )
    if not cadence:
        print("no sequence could be loaded; nothing measured")
        for line in problems:
            print(f"  ! {line}")
        return 2

    print(f"{stamp.caption()}\n")
    print(f"{'sequence':10s} {'split':12s} {'fixes':>7s} {'span_s':>9s} {'median_gap':>11s} "
          f"{'max_gap':>9s}  1Hz")
    for row in cadence:
        print(
            f"{row.sequence:10s} {row.split:12s} {row.n_fixes:7d} {row.fix_span_s:9.1f} "
            f"{row.median_gap_s:11.2f} {row.max_gap_s:9.1f}  {'yes' if row.meets_1hz else 'NO'}"
        )

    if alignment:
        print(f"\n{'sequence':10s} {'matched':>8s} {'res_med_m':>10s} {'res_p95_m':>10s} "
              f"{'res_max_m':>10s} {'best_lag_s':>11s} {'res@lag_m':>10s}  usable")
        for a in alignment:
            print(
                f"{a.sequence:10s} {a.n_matched:8d} {a.residual_median_m:10.2f} "
                f"{a.residual_p95_m:10.2f} {a.residual_max_m:10.2f} {a.best_lag_s:11.2f} "
                f"{a.residual_at_best_lag_m:10.2f}  {'yes' if a.is_usable else 'NO'}"
            )

    for line in problems:
        print(f"  ! {line}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    caption = stamp.caption()
    _write_csv(args.out_dir / "gnss_cadence.csv", cadence, caption)
    if alignment:
        _write_csv(
            args.out_dir / "truth_alignment.csv",
            alignment,
            caption,
            derived={"is_usable": lambda r: r.is_usable},
        )
    divergence = divergent_copies(manifest=args.manifest)
    if divergence:
        _write_csv(
            args.out_dir / "copy_divergence.csv",
            divergence,
            caption,
            derived={"delta_bytes": lambda r: r.delta_bytes},
        )
    summary = summarise(cadence, alignment, divergence)
    (args.out_dir / "cadence_summary.json").write_text(
        json.dumps({"stamp": caption, "problems": problems, "summary": summary}, indent=2),
        encoding="utf-8",
    )
    stamp.to_json(args.out_dir / "cadence_stamp.json")

    print(f"\n{json.dumps(summary, indent=2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
