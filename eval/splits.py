"""The frozen train/test split.

**Defined in code, not in a notebook.** A split that lives in a notebook cell is a split that
quietly changes when someone re-runs the cell, and the first symptom is a result nobody can
reproduce.

Source: docs/EVALUATION.md section 3. Changing anything here after the Gate 0 freeze requires a
DECISION_LOG entry naming which results it invalidated.
"""

from __future__ import annotations

from types import MappingProxyType

# --------------------------------------------------------------------------------------------
# Held-out test sets
# --------------------------------------------------------------------------------------------

#: Long-outage evaluation, 30/60/120/180 s.
LONG_OUTAGE: tuple[str, ...] = (
    "V-St6", "V-St7", "V-S3a", "Vtb3", "Vfb01c", "Vfb02a", "Vta1a", "Vfb02b", "Vfb02g",
)

#: Challenging scenarios, 10 s outages. Grouped because they are reported per-scenario, not pooled
#: -- a mean over roundabouts and motorway is a number that describes nothing.
CHALLENGING: MappingProxyType[str, tuple[str, ...]] = MappingProxyType(
    {
        "roundabout": ("Vta11", "Vfb02d"),
        "hard_brake": ("Vw16b", "Vw17", "Vta9"),
        "accel_change": ("Vfb02e", "Vta12"),
        "sharp_corner": ("Vw6", "Vw7", "Vw8"),
        "wet_road": ("Vtb8", "Vtb11", "Vtb13"),
        "motorway_control": ("Vw12",),
    }
)

#: Plots the submission must contain. Named here so a missing figure fails the run rather than
#: being noticed the night before.
MANDATORY_PLOT_SEQUENCES: tuple[str, ...] = ("V-St6", "V-St7", "V-S3a", "Vta11")

# --------------------------------------------------------------------------------------------
# Training set
# --------------------------------------------------------------------------------------------

TRAIN: tuple[str, ...] = (
    "V-S1", "V-S2", "V-S3c", "V-S4", "V-St1", "V-M", "V-Y2",
)


def test_sequences() -> tuple[str, ...]:
    """Every held-out sequence, deduplicated and ordered."""
    seqs = set(LONG_OUTAGE)
    for group in CHALLENGING.values():
        seqs.update(group)
    return tuple(sorted(seqs))


def assert_split_disjoint() -> None:
    """No sequence may appear in both train and test.

    Checked in CI. This is the cheapest possible test for the most expensive possible mistake:
    a train/test overlap invalidates every number downstream of it, and it is invisible in the
    results -- it just makes them look good.
    """
    overlap = set(TRAIN) & set(test_sequences())
    if overlap:
        raise AssertionError(
            f"train/test overlap: {sorted(overlap)}. Every metric computed under this split is "
            "invalid. Fix the split, then re-run the full sweep."
        )


def split_of(sequence: str) -> str:
    """'train', 'test', or 'unassigned'.

    'unassigned' is not an error -- IO-VNBD has many more sequences than we evaluate on -- but an
    unassigned sequence must never reach a metric.
    """
    if sequence in TRAIN:
        return "train"
    if sequence in test_sequences():
        return "test"
    return "unassigned"
