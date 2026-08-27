"""The frozen train/test split.

**Defined in code, not in a notebook.** A split that lives in a notebook cell is a split that
quietly changes when someone re-runs the cell, and the first symptom is a result nobody can
reproduce.

Source: docs/EVALUATION.md section 3. Changing anything here after the Gate 0 freeze requires a
DECISION_LOG entry naming which results it invalidated.

**Naming.** Sequences are named by their *bare stem* -- "S3a", "Vta11", "M" -- not by the "V-"
prefixed spelling used in the paper and in EVALUATION.md section 3. The prefix denotes the
*stream*, not the sequence: every stem ships as a paired "V-<stem>.csv" (ECU/CAN) and
"S-<stem>.csv" (smartphone). We consume the "S-" side only, so carrying a "V-" prefix here made
the loader's leakage guard reject the entire held-out set. See D-044.
"""

from __future__ import annotations

from types import MappingProxyType

# --------------------------------------------------------------------------------------------
# Sequences with no smartphone stream
# --------------------------------------------------------------------------------------------

#: Stems that exist **only** as "V-" ECU/CAN files in IO-VNBD -- there is no "S-<stem>.csv" in
#: either the synchronised or the unsynchronised folder. Since PS 26168 disallows the "V-" stream,
#: these sequences are unusable for us at any outage length.
#:
#: They were in the protocol drafted from the paper (EVALUATION.md section 3), which is written
#: against the vehicle stream. Removing them shrank the long-outage set from 9 sequences to 3 and
#: the mandatory plot set from 4 to 2.
#:
#: TODO(seat D): re-pick replacements from the stems that do have an "S-" file, then update
#: EVALUATION.md section 3 and log the new split in DECISION_LOG.md. Until that happens the
#: long-outage numbers rest on three sequences and should be reported as such.
UNAVAILABLE_S_STREAM: frozenset[str] = frozenset(
    {
        "St1",
        "St6",
        "St7",
        "Y2",
        "Vtb13",
        "Vfb01c",
        "Vfb02a",
        "Vfb02b",
        "Vfb02d",
        "Vfb02e",
        "Vfb02g",
    }
)

# --------------------------------------------------------------------------------------------
# Held-out test sets
# --------------------------------------------------------------------------------------------

#: Long-outage evaluation, 30/60/120/180 s.
#: Dropped for want of an "S-" stream: St6, St7, Vfb01c, Vfb02a, Vfb02b, Vfb02g.
LONG_OUTAGE: tuple[str, ...] = (
    "S3a",
    "Vtb3",
    "Vta1a",
)

#: Challenging scenarios, 10 s outages. Grouped because they are reported per-scenario, not pooled
#: -- a mean over roundabouts and motorway is a number that describes nothing.
#: Dropped for want of an "S-" stream: Vfb02d, Vfb02e, Vtb13.
CHALLENGING: MappingProxyType[str, tuple[str, ...]] = MappingProxyType(
    {
        "roundabout": ("Vta11",),
        "hard_brake": ("Vw16b", "Vw17", "Vta9"),
        "accel_change": ("Vta12",),
        "sharp_corner": ("Vw6", "Vw7", "Vw8"),
        "wet_road": ("Vtb8", "Vtb11"),
        "motorway_control": ("Vw12",),
    }
)

#: Plots the submission must contain. Named here so a missing figure fails the run rather than
#: being noticed the night before.
#: Dropped for want of an "S-" stream: St6, St7 -- two of the four. TODO(seat D) above.
MANDATORY_PLOT_SEQUENCES: tuple[str, ...] = ("S3a", "Vta11")

# --------------------------------------------------------------------------------------------
# Training set
# --------------------------------------------------------------------------------------------

#: Dropped for want of an "S-" stream: St1, Y2.
TRAIN: tuple[str, ...] = (
    "S1",
    "S2",
    "S3c",
    "S4",
    "M",
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


def assert_split_is_loadable() -> None:
    """No split may name a sequence that has no smartphone stream.

    A split entry with no "S-" file does not fail loudly at load time -- ``load_split`` falls back
    to the "V-" file, which the leakage guard then rejects with a message about wheel speed. That
    reads as a leakage bug rather than a missing-data bug, which is the wrong thing to go looking
    for. Fail here instead, where the cause is named.
    """
    named = set(TRAIN) | set(test_sequences()) | set(MANDATORY_PLOT_SEQUENCES)
    unusable = sorted(named & UNAVAILABLE_S_STREAM)
    if unusable:
        raise AssertionError(
            f"split names sequence(s) with no 'S-' smartphone stream: {unusable}. "
            "IO-VNBD ships these on the 'V-' ECU stream only, which PS 26168 disallows. "
            "Pick replacements and record them in DECISION_LOG.md."
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
