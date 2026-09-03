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
#: against the vehicle stream. Removing them originally shrank the long-outage set from 9 sequences
#: to 3 and the mandatory plot set from 4 to 2.
#:
#: D-092 executed the re-pick of replacements from measured synchronised stems with an "S-" file,
#: expanding LONG_OUTAGE to 7 sequences (459 60 s windows); see `LONG_OUTAGE` below.
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

#: Stems with an "S-" file and a paired "V-" file that `align_to_sequence` nevertheless refuses:
#: the two files do not describe the same drive at the same time, so the stem has no truth.
#: Measured over the whole 72-stem pool -- `python -m eval.cadence --all-paired` -- and recorded
#: here so a future re-pick does not offer one of them again. See D-092.
#:
#: `Vw7` and `Vw8` match **zero** of their fixes at an offset of about -165 s, which is not the
#: BST hour D-091 removed and is undiagnosed. `Vtb8` and `Vtb11` sit at 33.7 m and 35.1 m against
#: a 10 m limit. `Vtb3`'s residual is 8.5 m but its best fit is at a lag of -2.70 s against a
#: 0.5 s limit -- the whole `Vtb` family carries a systematic +1.6 to +2.1 s lag, which
#: `AlignmentReport` calls "a finding about the dataset, and not something this module may
#: silently subtract away". Widening the limit to admit them is the H-3 failure, not a fix.
REFUSED_TRUTH_PAIRING: frozenset[str] = frozenset({"Vtb3", "Vtb8", "Vtb11", "Vw7", "Vw8", "S3b"})

#: Stems shorter than the warmup plus one outage, which therefore host no window at any length
#: the protocol uses. Arithmetic, not preference: `generate_outages` already returns nothing for
#: them, and naming them here makes the omission visible instead of silent. `Vw17` is 32.9 s and
#: `Vta9` 15.6 s, against the 30 s warmup plus a 10 s outage.
TOO_SHORT_FOR_ANY_OUTAGE: frozenset[str] = frozenset({"Vw17", "Vta9"})

#: Long-outage evaluation, 30/60/120/180 s.
#:
#: **Re-picked 2026-09-02 (D-092), executing D-044's open TODO.** `S3a` returns: it was refused
#: with 0 of 254 fixes matched, which D-091 showed to be a one-hour BST/UTC clock error rather
#: than a pairing failure, and it now aligns at 4.92 m. `Vtb3` is dropped -- see
#: `REFUSED_TRUTH_PAIRING`. `Vta1a` stays. `Vw4`, `Vw2` and `Vta16` are promoted from the
#: previously unallocated pool, and `S3c` and `Vta1b` come with their families.
#:
#: Membership here is a *measurable* property -- the pair aligns, the stream integrates, the
#: recording is long enough -- which is why promotion into this set is legitimate and promotion
#: into `CHALLENGING` is not: a scenario label is a claim about what happened on the road, and no
#: source in this repo says which stem is a roundabout.
LONG_OUTAGE: tuple[str, ...] = (
    "S3a",
    "S3c",
    "Vta1a",
    "Vta1b",
    "Vta16",
    "Vw2",
    "Vw4",
)

#: Challenging scenarios, 10 s outages. Grouped because they are reported per-scenario, not pooled
#: -- a mean over roundabouts and motorway is a number that describes nothing.
#: Dropped for want of an "S-" stream: Vfb02d, Vfb02e, Vtb13.
#:
#: **Nothing is promoted into this set (D-092).** Every group name is a claim about what the
#: vehicle was doing -- a roundabout, a hard brake, a wet road -- and the only source for which
#: stem is which is the paper's own list, reproduced in EVALUATION.md section 3. No document in
#: this repo describes the 53 previously unallocated stems, so filling a thinned group from them
#: would be inventing the label. Entries are therefore only ever *removed* here, with the reason
#: recorded in `REFUSED_TRUTH_PAIRING` or `TOO_SHORT_FOR_ANY_OUTAGE`.
CHALLENGING: MappingProxyType[str, tuple[str, ...]] = MappingProxyType(
    {
        "roundabout": ("Vta11",),
        # Vw17 (32.9 s) and Vta9 (15.6 s) host no 10 s window after the 30 s warmup.
        "hard_brake": ("Vw16b",),
        "accel_change": ("Vta12",),
        # Vw7 and Vw8 match zero fixes at about -165 s; see REFUSED_TRUTH_PAIRING.
        "sharp_corner": ("Vw6",),
        # **EMPTY, and deliberately kept rather than deleted.** Both Vtb8 and Vtb11 are refused by
        # truth pairing at 33.7 m and 35.1 m, and no stem in the pool is documented as wet. The
        # consequence is that **the wet-road scenario cannot be reported at all**, which belongs
        # in the write-up's honest-limits section rather than in a silently shorter table.
        "wet_road": (),
        "motorway_control": ("Vw12",),
    }
)

#: Plots the submission must contain. Named here so a missing figure fails the run rather than
#: being noticed the night before.
#:
#: `S3a` returns with D-091. `Vta11` is dropped **not** because it is unusable -- it grades two
#: 10 s windows -- but because it is 51.0 s long and `eval.run.REPLAY_LENGTH_S` is 60 s, so it can
#: never produce the window the renderer plots. `Vw4` replaces it as the second long-outage plot.
#:
#: **Open, and not resolved here:** EVALUATION.md section 3 also requires "at least one roundabout
#: scenario" plot, and the only roundabout stem is Vta11, which cannot host a 60 s replay. That
#: plot is currently unproducible; closing it needs either a scenario-length replay window or a
#: longer roundabout recording, and both are protocol decisions. See D-092.
MANDATORY_PLOT_SEQUENCES: tuple[str, ...] = ("S3a", "Vw4")

# --------------------------------------------------------------------------------------------
# Training set
# --------------------------------------------------------------------------------------------

#: **Pinned to an explicit list of stems (D-092).** EVALUATION.md section 3 previously defined
#: this as the five named stems "plus Vta/Vtb/Vw/Vfa/Vfb subsets not listed above" -- an
#: open-ended clause that lived only in prose. `assert_split_disjoint` compares two tuples, so a
#: held-out stem drawn from that unnamed remainder would have overlapped training and no check in
#: this repo could have seen it. Promoting `Vw4`, `Vw2` and `Vta16` into `LONG_OUTAGE` is exactly
#: that move, so the clause is replaced by the enumeration below and the check becomes real.
#:
#: `S3c` has **left** this set: it shares the parent recording `S3` with the held-out `S3a`, and
#: a family straddling the split is the leakage that flatters a result without appearing in it.
#: The same rule keeps `Vw14a/b/c` together here and `Vta1a/Vta1b` together in the held-out set.
#:
#: Stems in neither tuple are `unassigned`, which `split_of` treats as ordinary: IO-VNBD has more
#: sequences than we evaluate on, and the refused and too-short ones stay out of both.
#: Dropped for want of an "S-" stream: St1, Y2.
TRAIN: tuple[str, ...] = (
    # Driver A / B, the long parent recordings. S2, S4 and M restart their clock mid-file
    # (D-013), so `assert_uniform_grid` refuses to integrate them as single sequences; that is a
    # limit on how they can be consumed, not a reason to leave the split ambiguous about them.
    "M",
    "S1",
    "S2",
    "S4",
    # The Vw14 family, kept whole.
    "Vw14a",
    "Vw14b",
    "Vw14c",
    # Driver E, previously unallocated and now named. Every one aligns and integrates.
    "Vta2",
    "Vta4",
    "Vta10",
    "Vta14",
    "Vta15",
    "Vta19",
    "Vw3",
    "Vw5",
    "Vw9",
    "Vw10",
    "Vw11",
    "Vw13",
    # `Vw16a` is deliberately absent and left unassigned: it shares the parent recording `Vw16`
    # with the held-out hard-brake stem `Vw16b`. It cannot join the held-out set either, because
    # that would assert it is a hard brake and no source in this repo says so. Nine 10 s windows
    # forgone to keep the family whole -- `assert_no_family_straddles_the_split` caught this.
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


def stem_family(sequence: str) -> str:
    """The parent recording a stem belongs to: `Vw14a` -> `Vw14`, `S3a` -> `S3`, `Vw4` -> `Vw4`.

    IO-VNBD splits several recordings into lettered segments. They are the same drive, the same
    driver and often the same stretch of road, so they are not independent samples.
    """
    return sequence[:-1] if len(sequence) > 1 and sequence[-1].isalpha() else sequence


def assert_no_family_straddles_the_split() -> None:
    """No parent recording may have one segment in TRAIN and another in the held-out set.

    `assert_split_disjoint` catches the same *stem* on both sides. It cannot catch `Vw14b` held
    out while `Vw14a` and `Vw14c` train, which is the same drive on the same road minutes apart --
    a model that memorised it would score well on the held-out segment and the split would look
    clean. This is the check that made `S3c` move out of TRAIN when `S3a` was recovered (D-092).
    """
    train_families = {stem_family(s) for s in TRAIN}
    test_families = {stem_family(s) for s in test_sequences()}
    straddling = sorted(train_families & test_families)
    if straddling:
        offenders = {
            fam: sorted(s for s in TRAIN + test_sequences() if stem_family(s) == fam)
            for fam in straddling
        }
        raise AssertionError(
            f"parent recording(s) split across train and test: {offenders}. Lettered stems are "
            "segments of one drive, so this is train/test leakage that assert_split_disjoint "
            "cannot see. Move the whole family to one side."
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
