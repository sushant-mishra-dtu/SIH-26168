"""Protocol invariants: the split, the outage sweep, and run determinism.

These guard the mistakes that are invisible in the results -- a train/test overlap or an
overlapping outage window does not look wrong, it just makes the numbers better.
"""

from __future__ import annotations

import pytest

from eval.outages.inject import (
    OUTAGE_LENGTHS_S,
    assert_non_overlapping,
    generate_outages,
    generate_sweep,
    mask_gnss,
)
from eval.splits import (
    CHALLENGING,
    LONG_OUTAGE,
    MANDATORY_PLOT_SEQUENCES,
    TRAIN,
    assert_split_disjoint,
    assert_split_is_loadable,
    split_of,
)
from eval.splits import test_sequences as held_out_sequences  # aliased: pytest collects `test_*`
from idr.stamp import make_stamp, seed_everything

# ------------------------------------------------------------------------------------------
# Split
# ------------------------------------------------------------------------------------------


def test_split_is_disjoint():
    assert_split_disjoint()


def test_split_names_only_sequences_that_have_a_smartphone_stream():
    """Eleven IO-VNBD stems ship on the "V-" ECU stream only. A split entry naming one of them
    surfaces as a leakage error at load time, which sends you debugging the wrong thing."""
    assert_split_is_loadable()


def test_no_sequence_is_in_two_challenging_groups():
    seen: set[str] = set()
    for group in CHALLENGING.values():
        assert not (seen & set(group)), "a sequence appears in two scenario groups"
        seen.update(group)


def test_mandatory_plot_sequences_are_held_out():
    """A mandatory plot drawn from the training set would be meaningless."""
    for seq in MANDATORY_PLOT_SEQUENCES:
        assert split_of(seq) == "test", f"{seq} must be held out"


def test_long_outage_set_matches_the_documented_protocol():
    for seq in ("S3a", "Vtb3", "Vta1a"):
        assert seq in LONG_OUTAGE
    assert not set(LONG_OUTAGE) & set(TRAIN)


def test_split_of_reports_unassigned_rather_than_guessing():
    assert split_of("Vta29") == "unassigned"


def test_held_out_set_is_the_union_of_long_and_challenging():
    held_out = set(held_out_sequences())
    expected = set(LONG_OUTAGE).union(*(set(g) for g in CHALLENGING.values()))
    assert held_out == expected
    assert not held_out & set(TRAIN)


# ------------------------------------------------------------------------------------------
# Outages
# ------------------------------------------------------------------------------------------


def test_outage_lengths_are_the_mandated_sweep():
    assert OUTAGE_LENGTHS_S == (10, 30, 60, 120, 180)


def test_outages_are_non_overlapping_and_correctly_sized():
    # 10 minutes at 10 Hz = 6,000 samples; 30 s warmup leaves 5,700 for 60 s windows.
    outages = generate_outages("S3a", 6000, 60)
    assert len(outages) == 9
    assert all(o.n_samples == 600 for o in outages)
    assert all(o.n_epochs == 60 for o in outages)
    assert_non_overlapping(outages)


def test_warmup_is_respected():
    """Starting an outage at sample zero measures filter initialisation, not dead reckoning."""
    outages = generate_outages("S3a", 6000, 60, warmup_s=30)
    assert outages[0].start_idx == 300


def test_short_sequence_yields_no_outages_rather_than_a_partial_one():
    assert generate_outages("tiny", 500, 180) == []


def test_sweep_counts_vary_by_length():
    """Sequences too short for 180 s contribute nothing at that length -- the same mechanism that
    makes the published per-length counts differ."""
    sweep = generate_sweep({"a": 6000, "b": 1200}, (30, 180))
    assert len(sweep[30]) > len(sweep[180])
    for windows in sweep.values():
        assert_non_overlapping(windows)


def test_overlap_detector_actually_detects_overlap():
    """A guard never observed to fire is not known to work."""
    from eval.outages.inject import Outage

    bad = [Outage("s", 0, 600, 60), Outage("s", 300, 900, 60)]
    with pytest.raises(AssertionError, match="overlapping"):
        assert_non_overlapping(bad)


def test_gnss_mask_is_false_exactly_during_outages():
    outages = generate_outages("S3a", 6000, 60)
    mask = mask_gnss(6000, outages)
    assert mask[:300].all()  # warmup: GNSS available
    assert not mask[300:900].any()  # first outage: fully denied
    assert mask.sum() == 6000 - sum(o.n_samples for o in outages)


# ------------------------------------------------------------------------------------------
# Determinism and provenance
# ------------------------------------------------------------------------------------------


def test_same_seed_gives_identical_draws():
    import numpy as np

    seed_everything(0)
    a = np.random.rand(64)
    seed_everything(0)
    b = np.random.rand(64)
    assert np.array_equal(a, b)


def test_different_seeds_diverge():
    import numpy as np

    seed_everything(0)
    a = np.random.rand(64)
    seed_everything(1)
    b = np.random.rand(64)
    assert not np.array_equal(a, b)


def test_stamp_records_seed_and_commit():
    s = make_stamp(42)
    assert s.seed == 42
    assert s.commit
    assert "seed 42" in s.caption()


def test_dirty_tree_is_flagged_as_unreproducible():
    from idr.stamp import Stamp

    dirty = Stamp("abc123-dirty", 0, "t", "3.11.0", "test", "1.26")
    clean = Stamp("abc123", 0, "t", "3.11.0", "test", "1.26")
    nogit = Stamp("nogit", 0, "t", "3.11.0", "test", "1.26")
    assert not dirty.is_reproducible()
    assert not nogit.is_reproducible()
    assert clean.is_reproducible()
