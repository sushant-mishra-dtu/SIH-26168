"""Training entry point for the Onyekpe INS baseline reproduction (P-06).

    python -m models.train_baseline_rnn --data data/IO-VNBD --seed 0

**Read `HYPERPARAMETERS` before running this.** The published papers state some of the settings
below and are silent on others, and every silence is a choice *we* are making. The table
distinguishes the two explicitly, and each omission carries a DECISION_LOG id rather than sitting
as a bare constant in a config file -- a reproduction whose gaps are invisible is not a
reproduction, it is a model with a citation attached.

Requires the `ml` extra (`pip install -e ".[ml]"`). torch is deliberately absent from CI: the
harness is the critical path and must never block on a 2 GB download.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

# --------------------------------------------------------------------------------------------
# What the papers state, and what they do not
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Hyperparameter:
    name: str
    value: str
    source: str
    #: "" where the paper states it; a DECISION_LOG id where we had to choose.
    decision: str = ""

    @property
    def is_our_choice(self) -> bool:
        return bool(self.decision)


#: Every setting the reproduction depends on. `--audit` prints it, and the phase requires it to be
#: read before anything trains. Sources: docs/DATASETS.md section 3, itself transcribed from
#: Onyekpe et al., "Learning to Localise Automated Vehicles in Challenging Environments" and the
#: WhONet paper (arXiv 2104.02581).
HYPERPARAMETERS: tuple[Hyperparameter, ...] = (
    Hyperparameter("window", "1 s = 10 samples at 10 Hz", "stated (INS paper)"),
    Hyperparameter("model", "vanilla RNN, 1 hidden layer, 72 units", "stated (INS paper)"),
    Hyperparameter("dropout", "0.05", "stated (INS paper)"),
    Hyperparameter("batch size", "128", "stated (INS paper)"),
    Hyperparameter("learning rate", "7e-4", "stated (INS paper)"),
    Hyperparameter("optimiser", "Adamax", "stated (WhONet paper), NOT surfaced in the INS paper"),
    Hyperparameter("loss", "MAE", "stated (WhONet paper), NOT surfaced in the INS paper"),
    Hyperparameter("input scaling", "features scaled 0-1", "stated (INS paper)"),
    Hyperparameter("framework", "Keras/TF; we reimplement in PyTorch", "stated"),
    # ---- silences ----
    Hyperparameter("epochs", "TBD", "OMITTED by both papers", decision="D-070"),
    Hyperparameter("early stopping / patience", "TBD", "OMITTED", decision="D-070"),
    Hyperparameter("train/validation split", "TBD", "OMITTED", decision="D-070"),
    Hyperparameter("weight initialisation", "TBD", "OMITTED", decision="D-070"),
    Hyperparameter("gradient clipping", "TBD", "OMITTED", decision="D-070"),
    Hyperparameter(
        "scaler fitting set", "TBD", "OMITTED -- and it is a leakage risk", decision="D-071"
    ),
    Hyperparameter("LR schedule", "TBD", "OMITTED", decision="D-070"),
    Hyperparameter("shuffling / window stride", "TBD", "OMITTED", decision="D-070"),
    Hyperparameter(
        "GNSS input noise sigma", "TBD", "stated as present, magnitude OMITTED",
        decision="D-070",
    ),
)


def audit_table() -> str:
    """The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in the report."""
    width = max(len(h.name) for h in HYPERPARAMETERS)
    lines = [
        "Onyekpe INS baseline -- what the papers state and what we are choosing",
        "",
        f"{'setting'.ljust(width)}  {'value'.ljust(34)}  source",
        f"{'-' * width}  {'-' * 34}  {'-' * 46}",
    ]
    for h in HYPERPARAMETERS:
        marker = f"  [{h.decision}]" if h.is_our_choice else ""
        lines.append(f"{h.name.ljust(width)}  {h.value.ljust(34)}  {h.source}{marker}")
    stated = sum(not h.is_our_choice for h in HYPERPARAMETERS)
    ours = sum(h.is_our_choice for h in HYPERPARAMETERS)
    lines += [
        "",
        f"{stated} stated, {ours} ours. Every one of the {ours} is a way this reproduction can "
        "differ from",
        "the published number for a reason that is not the method. Report the gap; do not close "
        "it by",
        "search. A reproduction that lands 20% off with a stated reason is a result; one that "
        "lands",
        "exactly on the published number with no explanation is usually a leak.",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="train-baseline-rnn",
        description="Reproduce the Onyekpe INS baseline at its published hyperparameters",
    )
    p.add_argument("--data", default="data/IO-VNBD")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--audit",
        action="store_true",
        help="print the stated-vs-omitted hyperparameter table and exit, training nothing",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(audit_table())
    if args.audit:
        return 0

    try:
        import torch  # noqa: F401
    except ImportError:
        print(
            '\ntorch is not installed. This baseline needs the `ml` extra: pip install -e ".[ml]"'
            "\nIt is deliberately absent from CI -- the harness is the critical path and must not "
            "block on a 2 GB download.",
            file=sys.stderr,
        )
        return 4

    # ------------------------------------------------------------------------------------
    # Training is NOT implemented, and this is not an oversight.
    #
    # The nine omissions above are unresolved: each needs a DECISION_LOG row naming what we
    # chose and why, and the phase is explicit that the list is reviewed *before* anything
    # trains. Writing a training loop now would fix all nine silently in a config file, which
    # is the exact failure the audit exists to prevent.
    #
    # It is also blocked on data. The IO-VNBD CSVs are Git-LFS objects that cannot be fetched
    # in the container this was written in (D-059), so there is nothing to fit and no
    # published number to compare against.
    #
    # A stub that returned an untrained model's loss would produce a plausible number. That is
    # worse than nothing, and it is why this raises instead.
    # ------------------------------------------------------------------------------------
    raise NotImplementedError(
        "P-06 training: resolve the nine omitted hyperparameters into DECISION_LOG rows first "
        "(run with --audit to list them), then implement the loop against a machine that has "
        "the IO-VNBD files. See D-070 and D-072."
    )


if __name__ == "__main__":
    raise SystemExit(main())
