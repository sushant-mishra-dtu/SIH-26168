"""Harness entry point. One command regenerates every number.

    idr-eval --data data/IO-VNBD --seed 0 --out eval/figures

If regenerating the results needs manual steps, the figures will silently drift from the numbers
in the text. That is the failure this file exists to prevent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.metrics.core import CRSE_CONVENTION, OutageMetrics, summarise
from eval.outages.inject import OUTAGE_LENGTHS_S, assert_non_overlapping, generate_sweep
from eval.splits import LONG_OUTAGE, assert_split_disjoint, test_sequences
from idr.stamp import seed_everything

DEFAULT_SEED = 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="idr-eval", description="IDR 26168 evaluation harness")
    p.add_argument("--data", type=Path, default=Path("data/IO-VNBD"), help="dataset root")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", type=Path, default=Path("eval/figures"))
    p.add_argument(
        "--lengths",
        type=int,
        nargs="+",
        default=list(OUTAGE_LENGTHS_S),
        help="outage lengths in seconds (changing these needs a DECISION_LOG entry)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the protocol and plan the sweep without loading data",
    )
    return p


def plan_sweep(sequence_lengths: dict[str, int], lengths: list[int]) -> dict[int, list]:
    """Generate and validate the outage sweep. Validation is not optional."""
    sweep = generate_sweep(sequence_lengths, tuple(lengths))
    for windows in sweep.values():
        assert_non_overlapping(windows)
    return sweep


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp = seed_everything(args.seed)

    # Protocol invariants, checked before any data is touched. A run that violates the split is
    # worse than a run that does not happen.
    assert_split_disjoint()

    print(f"[idr-eval] {stamp.caption()}")
    print(f"[idr-eval] CRSE convention: {CRSE_CONVENTION.value}")
    if not stamp.is_reproducible():
        print(
            "[idr-eval] WARNING: working tree is dirty or not a git repo. Artefacts from this run "
            "cannot be regenerated from a commit and must not reach the submission.",
            file=sys.stderr,
        )

    if args.dry_run:
        # Nominal lengths so the sweep can be planned before the dataset lands.
        nominal = {name: 20 * 60 * 10 for name in test_sequences()}
        sweep = plan_sweep(nominal, args.lengths)
        print(f"[idr-eval] dry run over {len(nominal)} held-out sequences:")
        for length_s, windows in sorted(sweep.items()):
            print(f"    {length_s:>4} s -> {len(windows):>5} non-overlapping windows")
        print(f"[idr-eval] long-outage plot set: {', '.join(LONG_OUTAGE)}")
        return 0

    if not args.data.exists():
        print(
            f"[idr-eval] dataset not found at {args.data}\n"
            "           See docs/DATASETS.md, then record the download in data/manifest/.\n"
            "           Use --dry-run to validate the protocol without data.",
            file=sys.stderr,
        )
        return 2

    # ---------------------------------------------------------------------------------------
    # TODO(seat D, Sprint 0): load held-out sequences, run the filter across each outage window,
    # collect OutageMetrics per window, then write results + figures stamped with `stamp`.
    # The metric, outage and split layers below are complete and tested; this is the wiring.
    # ---------------------------------------------------------------------------------------
    results: list[OutageMetrics] = []
    if not results:
        print(
            "[idr-eval] no results: the filter is not wired in yet (Sprint 0 task).",
            file=sys.stderr,
        )
        return 3

    args.out.mkdir(parents=True, exist_ok=True)
    summary = summarise(results)
    (args.out / "summary.json").write_text(
        json.dumps({"stamp": stamp.caption(), "summary": summary}, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
