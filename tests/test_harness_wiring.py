"""End-to-end wiring for `eval/run.py`, on a synthetic sequence.

**Why synthetic.** The IO-VNBD CSVs are Git-LFS objects this container cannot fetch (D-059), so
the Gate 1 numbers cannot be produced here. What *can* be established, and is worth as much, is
that the wiring is correct: axis mapping, the two clocks, epoch alignment, the GNSS mask, the
truth lookup and the metrics composition all agree. Those are the failures that produce a
plausible number rather than an error, and they are exactly what the first item in Gate 1's fixed
diagnosis order -- **timestamps** -- is about.

Every fixture here is built from a known drive, so the expected answers are known independently of
the code. Nothing in this file asserts filter *accuracy*: that is a measurement against real data,
not a property a synthetic scenario can establish.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from core.reference.inekf import FilterConfig, InEKF
from eval.loaders.io_vnbd import SAMPLE_RATE_HZ, Sequence
from eval.loaders.truth import TruthTrack, align_to_sequence
from eval.metrics.core import OutageMetrics
from eval.outages.inject import Outage
from eval.run import (
    EPOCH_STRIDE,
    GATE1_LENGTH_S,
    HOLD_BIASES_IN_OUTAGE,
    METHODS,
    ZARU_SIGMA_FROM_WINDOW,
    SequenceUnusable,
    WindowResult,
    assert_uniform_grid,
    evaluate_sequence,
    fix_arrays,
    gate1_by_mount_class,
    gate1_ratio,
    imu_stream,
    initialise_filter,
    summarise_by_method_and_length,
    truth_clock_offset_s,
    window_trajectory,
    write_artefacts,
)
from idr.stamp import seed_everything

G = 9.80665
DEG_PER_M = 1.0 / 111_320.0
LAT0, LON0 = 51.5, -1.25
START_OF_DAY_S = 9 * 3600 + 30 * 60  # 09:30:00, arbitrary but not midnight


#: The fixture's calendar date. 2019-10-11 is inside British Summer Time (2019's transition is
#: 27 October), so the `S-` side must be written in **local** time to be the file it imitates --
#: which is what makes this fixture exercise D-091's conversion rather than sidestep it.
FIXTURE_DATE = "2019-10-11"
FIXTURE_UTC_OFFSET_S = 3600.0


def _date_strings(utc_seconds_of_day: np.ndarray) -> list[str]:
    """The shipped `DATE (YYYY-MO-DD HH-MI-SS_SSS)` spelling, in UK local time.

    Takes UTC and adds the offset, because that is the direction the real files are written in:
    AndroSensor stamps civil time while the paired VBOX stamps UTC (D-091). Passing UTC straight
    through would make the fixture the one file in the dataset whose `date` column is UTC, and
    every clock assertion built on it would be testing a case that does not ship.
    """
    out = []
    for s in np.asarray(utc_seconds_of_day, dtype=float) + FIXTURE_UTC_OFFSET_S:
        h, rem = divmod(float(s), 3600.0)
        m, sec = divmod(rem, 60.0)
        whole = int(sec)
        ms = int(round((sec - whole) * 1000))
        out.append(f"{FIXTURE_DATE} {int(h):02d}-{int(m):02d}-{whole:02d}_{ms:03d}")
    return out


def synthetic_drive(
    *,
    seconds: float = 300.0,
    mps: float = 15.0,
    accel_bias_x: float = 0.0,
    fix_interval_s: float = 9.0,
    name: str = "SYNTH",
    t_rel_start_s: float = 0.0,
):
    """A level vehicle driving due north at a constant speed, as a `Sequence` + `TruthTrack` pair.

    The two carry *different clocks on purpose*, which is the property most worth testing: the
    `S-` side counts milliseconds from the start of the recording and the `V-` side counts seconds
    since midnight, offset by `START_OF_DAY_S`. A harness that quietly treats one as the other
    produces a trajectory that looks like a drive and is graded against the wrong stretch of road.

    `t_rel_start_s` is the value the `S-` relative clock *opens* at. It defaults to zero, which is
    what this fixture assumed for its whole life and is why nothing here could see the harness
    deriving epochs from the row index; eleven of the fourteen real held-out stems open non-zero.
    """
    n = int(seconds * SAMPLE_RATE_HZ) + 1
    t_rel = t_rel_start_s + np.arange(n, dtype=float) / SAMPLE_RATE_HZ
    t_tod = START_OF_DAY_S + t_rel

    lat = LAT0 + mps * t_rel * DEG_PER_M
    lon = np.full(n, LON0)
    truth = TruthTrack(name=name, t_s=t_tod, lat=lat, lon=lon, source="synthetic (tests)")

    accel = np.tile([accel_bias_x, 0.0, -G], (n, 1))
    gyro = np.zeros((n, 3))
    imu = pd.DataFrame(
        {
            "accel_x": accel[:, 0], "accel_y": accel[:, 1], "accel_z": accel[:, 2],
            "gyro_yaw": gyro[:, 0], "gyro_pitch": gyro[:, 1], "gyro_roll": gyro[:, 2],
            # The `GRAVITY` channel every real `S-` file ships, pointing **up** (D-085). Without
            # it the mount initialiser has no vertical and is skipped, which is what this fixture
            # used to do -- silently, and so it could not exercise D-094's PCA path at all.
            "gravity_x": np.zeros(n), "gravity_y": np.zeros(n), "gravity_z": np.full(n, G),
            "time_since_start_ms": t_rel * 1000.0,
        }
    )

    stride = int(fix_interval_s * SAMPLE_RATE_HZ)
    idx = np.arange(0, n, stride)
    gnss = pd.DataFrame(
        {
            "gps_lat": lat[idx], "gps_lon": lon[idx],
            "gps_altitude_m": np.full(idx.size, 100.0),
            "gps_accuracy_m": np.full(idx.size, 3.0),
            "sample_idx": idx,
            "time_since_start_ms": t_rel[idx] * 1000.0,
            "date": _date_strings(t_tod[idx]),
        }
    )
    return Sequence(name=name, imu=imu, gnss=gnss, split="test"), truth


# ------------------------------------------------------------------------------------------
# The two clocks -- item one in Gate 1's fixed diagnosis order
# ------------------------------------------------------------------------------------------


def test_the_truth_clock_offset_is_recovered_from_the_fixes():
    """The `S-` and `V-` clocks differ by `START_OF_DAY_S` here, and nothing but the fixes' own
    `date`/`time_since_start_ms` pair can say so."""
    seq, _ = synthetic_drive()
    assert truth_clock_offset_s(seq) == pytest.approx(START_OF_DAY_S, abs=1e-3)


def test_the_offset_is_recovered_when_the_relative_clock_does_not_open_at_zero():
    """`truth_clock_offset_s` differences the two clocks, so a non-zero opening must cancel."""
    seq, _ = synthetic_drive(t_rel_start_s=1118.51)
    assert truth_clock_offset_s(seq) == pytest.approx(START_OF_DAY_S, abs=1e-3)


def test_an_excerpt_whose_clock_opens_late_is_graded_against_the_road_it_drove():
    """The epoch of a window comes from the row's own timestamp, never from its row index.

    Vta11, Vta12, Vta9, Vtb3, Vtb8, Vtb11, Vw6, Vw7, Vw8, Vw16b and Vw17 are excerpts that keep
    the parent recording's clock: `time_since_start_ms` opens at 1118 s on Vta11 and 13365 s on
    Vw8. Deriving the epoch as `start_idx / SAMPLE_RATE_HZ + offset` assumes that opening is
    zero, so it addressed truth 1118 s -- and on Vw8 3.7 hours -- before the window actually
    occurred. The truth track raises rather than interpolating across that gap, which is why this
    surfaced as a hard failure on the first real sweep and not as a quietly wrong number.
    """
    start = 1118.51
    seq, truth = synthetic_drive(t_rel_start_s=start)
    results = evaluate_sequence(seq, truth, (60,))

    assert results, "the sweep produced no windows to grade"
    assert all(np.isfinite(r.metrics.drift_pct) for r in results)

    # The opening value is a property of the recording, not of the road, so the same drive must
    # yield the same number of graded windows either way.
    at_zero = evaluate_sequence(*synthetic_drive(t_rel_start_s=0.0), (60,))
    assert len(results) == len(at_zero)

    # What separates: each method must score the same whether the clock opens at zero or at
    # `start`, because it is the same road either way. The absolute bound is chosen against the
    # failure it has to catch -- addressing the window 1118 s early points it at a stretch of road
    # 16.8 km away, which does not perturb a drift figure, it replaces it. The methods differ
    # hugely from each other here (the filter has no speed input on this fixture and sits at
    # ~100 %, the strapdown is exact at ~1e-9 %), so they are compared like for like.
    assert [r.method for r in results] == [r.method for r in at_zero]
    for late, zero in zip(results, at_zero, strict=True):
        assert late.metrics.drift_pct == pytest.approx(zero.metrics.drift_pct, abs=1e-3)


def test_a_sequence_whose_fixes_carry_no_date_is_refused():
    seq, _ = synthetic_drive()
    seq = Sequence(seq.name, seq.imu, seq.gnss.drop(columns=["date"]), seq.split)
    with pytest.raises(SequenceUnusable, match="cannot be placed against"):
        truth_clock_offset_s(seq)


def test_the_synthetic_pair_aligns_and_is_usable_as_truth():
    """If this fails the fixture is wrong, and every assertion built on it means nothing."""
    seq, truth = synthetic_drive()
    report = align_to_sequence(seq, truth)
    assert report.is_usable
    assert report.residual_median_m == pytest.approx(0.0, abs=1e-6)
    assert report.best_lag_s == pytest.approx(0.0, abs=1e-9)


# ------------------------------------------------------------------------------------------
# Reading a Sequence into arrays
# ------------------------------------------------------------------------------------------


def test_the_gyro_axis_mapping_is_the_one_d101_established():
    """Proper right-handed triad (+gyro_yaw, -gyro_roll, +gyro_pitch) established by D-101
    (superseding D-047). `gyro_pitch` is the vertical body rate across synchronised stems."""
    seq, _ = synthetic_drive()
    seq.imu["gyro_yaw"] = 1.0
    seq.imu["gyro_pitch"] = 2.0
    seq.imu["gyro_roll"] = 3.0
    gyro, _, _ = imu_stream(seq)
    assert gyro[0] == pytest.approx([1.0, -3.0, 2.0])


def test_dt_comes_from_the_timestamps_and_a_backwards_clock_is_refused():
    """Five `S-` stems restart their clock mid-recording; integrating across the break is silent
    and wrong, so the harness stops instead (D-013)."""
    t = np.arange(100, dtype=float) / SAMPLE_RATE_HZ
    dt = assert_uniform_grid("OK", t)
    assert dt == pytest.approx(np.full(99, 0.1))

    t[50] = t[49] - 1.0
    with pytest.raises(SequenceUnusable, match="timestamps go backwards"):
        assert_uniform_grid("BROKEN", t)


def test_a_stream_off_the_10_hz_grid_is_refused_rather_than_integrated():
    t = np.arange(100, dtype=float) * 0.5  # 2 Hz
    with pytest.raises(SequenceUnusable, match="strays"):
        assert_uniform_grid("SLOW", t)


def test_the_gate_reads_the_receivers_own_reported_accuracy():
    """`gps_accuracy_m` is the phone's own statement about the fix, so the covariance the chi2
    gate reads is per-fix rather than a constant."""
    seq, _ = synthetic_drive()
    seq.gnss.loc[2, "gps_accuracy_m"] = 25.0
    seq.gnss.loc[3, "gps_accuracy_m"] = np.nan
    _, _, sigma = fix_arrays(seq, LAT0, LON0)
    assert sigma[0] == pytest.approx(3.0)
    assert sigma[2] == pytest.approx(25.0)
    assert sigma[3] == pytest.approx(3.0), "a missing accuracy falls back to the config default"


# ------------------------------------------------------------------------------------------
# Epoch slicing
# ------------------------------------------------------------------------------------------


def test_a_window_slices_one_displacement_per_epoch():
    pos = np.column_stack([np.arange(1000, dtype=float), np.zeros(1000)])
    traj = window_trajectory(pos, Outage("S", 300, 900, 60))
    assert traj.n_epochs == 60
    assert traj.displacements_ned == pytest.approx(np.tile([float(EPOCH_STRIDE), 0.0], (60, 1)))


def test_a_window_past_the_end_of_the_sequence_is_an_error():
    pos = np.zeros((400, 2))
    with pytest.raises(ValueError, match="past the end"):
        window_trajectory(pos, Outage("S", 300, 900, 60))


# ------------------------------------------------------------------------------------------
# The whole pipeline
# ------------------------------------------------------------------------------------------


def test_every_method_produces_a_finite_scored_window():
    """The wiring end to end: loader arrays -> filter and both baselines -> one metrics path.

    Asserts shape, coverage and finiteness -- not accuracy. Filter accuracy on IO-VNBD is the Gate
    1 measurement and it cannot be made here.
    """
    seq, truth = synthetic_drive(seconds=200.0)
    results = evaluate_sequence(seq, truth, [60])

    assert results, "no windows scored"
    methods = {r.method for r in results}
    assert methods == {"filter", "strapdown", "gnss_available"}
    for r in results:
        assert r.length_s == 60
        assert r.metrics.n_epochs == 60
        assert r.metrics.duration_s == 60.0
        assert np.isfinite(r.metrics.drift_pct)
        assert np.isfinite(r.metrics.cte_m)
        assert np.isfinite(r.metrics.yaw_rmse_rad)
        assert r.metrics.distance_m == pytest.approx(900.0, rel=1e-2)


def test_the_naive_strapdown_still_costs_the_budgets_176_m_through_the_whole_pipeline():
    """The same closed form as tests/test_baselines.py, but reached through the loader, the two
    clocks and the truth lookup rather than through hand-built arrays. If any of those is wrong
    this number moves."""
    bias = 0.010 * G
    seq, truth = synthetic_drive(seconds=200.0, accel_bias_x=bias)
    results = evaluate_sequence(seq, truth, [60])
    strapdown = [r for r in results if r.method == "strapdown"]
    assert strapdown
    for r in strapdown:
        assert r.metrics.drift_pct == pytest.approx(100.0 * 176.5 / 900.0, rel=5e-2)


def test_gnss_is_applied_outside_the_outage_and_never_inside_it():
    """The architectural claim, exercised: during an injected outage the GNSS update is simply not
    called. A filter run whose mask is all-closed must apply no fix at all."""
    from eval.run import run_filter

    seq, truth = synthetic_drive(seconds=200.0)
    gyro, accel, t_rel = imu_stream(seq)
    dt = assert_uniform_grid(seq.name, t_rel)
    idx, ned, sigma = fix_arrays(seq, float(truth.lat[0]), float(truth.lon[0]))
    n = gyro.shape[0]

    closed = run_filter(gyro, accel, dt, idx, ned, sigma, np.zeros(n, dtype=bool))
    assert closed.n_gnss_applied == 0 and closed.n_gnss_rejected == 0

    open_run = run_filter(gyro, accel, dt, idx, ned, sigma, np.ones(n, dtype=bool))
    assert open_run.n_gnss_applied + open_run.n_gnss_rejected == idx.size


def test_the_gate_1_ratio_carries_the_window_count_it_rests_on():
    """A ratio quoted without its sample size is the number a judge asks about second."""
    seq, truth = synthetic_drive(seconds=200.0)
    by_method = summarise_by_method_and_length(evaluate_sequence(seq, truth, [60]))
    gate = gate1_ratio(by_method)

    assert gate["measured"] is True
    assert gate["length_s"] == GATE1_LENGTH_S
    assert gate["range_required"] == [3.0, 5.0]
    assert gate["n_windows_filter"] >= 1
    assert gate["n_windows_gnss_available"] >= 1


def test_gate_1_reports_that_it_could_not_be_measured_rather_than_a_number():
    """No 60 s windows means no Gate 1 number. Saying so is the only correct output."""
    seq, truth = synthetic_drive(seconds=200.0)
    by_method = summarise_by_method_and_length(evaluate_sequence(seq, truth, [10]))
    gate = gate1_ratio(by_method)
    assert gate["measured"] is False


def test_gate1_by_mount_class_key_set_and_membership():
    """D-115: Gate 1 ratio partitioned by mount class.

    Quiet mount carries S3a and S3c; vibrating mount carries the remaining LONG_OUTAGE stems
    (such as Vw4). Verify key set is exactly {'quiet', 'vibrating'} and windows partition correctly.
    """

    def _synthetic_metric(drift: float) -> OutageMetrics:
        return OutageMetrics(
            cte_m=1.0,
            crse_m=1.0,
            drift_pct=drift,
            yaw_rmse_rad=0.01,
            yaw_max_rad=0.02,
            distance_m=100.0,
            duration_s=60.0,
            n_epochs=60,
        )

    results = [
        WindowResult("filter", "S3a", 60, 0, _synthetic_metric(12.0)),
        WindowResult("gnss_available", "S3a", 60, 0, _synthetic_metric(2.0)),
        WindowResult("filter", "Vw4", 60, 0, _synthetic_metric(40.0)),
        WindowResult("gnss_available", "Vw4", 60, 0, _synthetic_metric(4.0)),
    ]

    by_mount = gate1_by_mount_class(results)
    assert set(by_mount.keys()) == {"quiet", "vibrating"}

    expected_fields = {
        "filter_drift_pct_median",
        "gnss_available_drift_pct_median",
        "ratio",
        "in_range",
        "n_windows_filter",
        "n_windows_gnss_available",
    }
    assert set(by_mount["quiet"].keys()) == expected_fields
    assert set(by_mount["vibrating"].keys()) == expected_fields

    # S3a lands in quiet
    quiet = by_mount["quiet"]
    assert quiet["n_windows_filter"] == 1
    assert quiet["n_windows_gnss_available"] == 1
    assert quiet["filter_drift_pct_median"] == pytest.approx(12.0)
    assert quiet["gnss_available_drift_pct_median"] == pytest.approx(2.0)
    assert quiet["ratio"] == pytest.approx(6.0)

    # Vw4 lands in vibrating
    vibrating = by_mount["vibrating"]
    assert vibrating["n_windows_filter"] == 1
    assert vibrating["n_windows_gnss_available"] == 1
    assert vibrating["filter_drift_pct_median"] == pytest.approx(40.0)
    assert vibrating["gnss_available_drift_pct_median"] == pytest.approx(4.0)
    assert vibrating["ratio"] == pytest.approx(10.0)

    # Also check gate1_ratio passes it through
    by_method = summarise_by_method_and_length(results)
    gate = gate1_ratio(by_method, results=results)
    assert "by_mount_class" in gate
    assert gate["by_mount_class"] == by_mount


def test_artefacts_carry_the_stamp_inside_the_file_not_in_its_name(tmp_path):
    """H-5. A filename is renamed, copied, and pasted into a slide, and the provenance is lost at
    the first of those."""
    seq, truth = synthetic_drive(seconds=200.0)
    results = evaluate_sequence(seq, truth, [60])
    stamp = seed_everything(0)

    summary = write_artefacts(tmp_path, stamp, results)
    written = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert written["stamp"] == stamp.caption()
    assert written["crse_convention"] == "sum_abs"
    assert written["n_windows"] == len(results)
    assert summary["gate1"]["measured"] is True
    # D-130: the artefact says which bias-hold variant produced it, and the value is the
    # module constant `replay_window` reads -- never a per-call flag.
    assert written["biases_held_in_outage"] is HOLD_BIASES_IN_OUTAGE
    assert written["zaru_sigma_from_window"] is ZARU_SIGMA_FROM_WINDOW, (
        "the artefact says which ZARU R produced it (D-131), as it does for the bias hold"
    )

    csv_text = (tmp_path / "windows.csv").read_text(encoding="utf-8")
    assert csv_text.startswith(f"# {stamp.caption()}")
    assert "yaw_rmse_deg" in csv_text, "H-6: yaw travels with every position number"


def test_an_unusable_truth_pairing_stops_the_sequence_rather_than_grading_it():
    """A `V-` track that does not describe this drive is a reason to drop the stem loudly, not to
    report a number against the wrong stretch of road."""
    seq, truth = synthetic_drive(seconds=200.0)
    shifted = TruthTrack(
        name=truth.name,
        t_s=truth.t_s,
        lat=truth.lat + 0.01,  # ~1.1 km north of the drive
        lon=truth.lon,
        source=truth.source,
    )
    with pytest.raises(SequenceUnusable, match="not usable as truth"):
        evaluate_sequence(seq, shifted, [60])


# ------------------------------------------------------------------------------------------
# Windows the truth track does not cover (D-089)
# ------------------------------------------------------------------------------------------


def _truth_with_hole(truth: TruthTrack, *, from_rel_s: float, to_rel_s: float) -> TruthTrack:
    """The same track with its samples between two relative times deleted.

    This is Vw12's failure built to order: `align_to_sequence` still passes -- the surviving
    samples describe the same drive at the same time, and losing three seconds costs at most one
    of the ~9 s-spaced `S-` fixes a match -- but the epochs inside the hole have no truth sample
    within `MAX_EPOCH_OFFSET_S`, so `index_at` raises for the windows that span it and only those.
    """
    keep = ~(
        (truth.t_s >= START_OF_DAY_S + from_rel_s) & (truth.t_s <= START_OF_DAY_S + to_rel_s)
    )
    return TruthTrack(
        name=truth.name,
        t_s=truth.t_s[keep],
        lat=truth.lat[keep],
        lon=truth.lon[keep],
        source=truth.source,
    )


#: Relative seconds of the hole. Chosen to sit inside the second 60 s window (samples 900-1500,
#: i.e. 90-150 s) so there are covered windows on both sides of it -- a hole in the first window
#: would not distinguish "dropped the window" from "started grading late".
HOLE_FROM_S, HOLE_TO_S = 120.0, 123.0


def test_a_window_the_truth_does_not_cover_is_dropped_and_the_rest_still_grade():
    """D-089. A 3 s hole leaves 4 of the window's 61 epochs uncovered -- Vw12's failure to scale
    (3 of 11, worst gap 2.305 s) -- and that is not a reason to lose the other five windows.

    Before this, `TruthPairingError` escaped `evaluate_sequence` entirely, passed straight through
    `main()`'s `except SequenceUnusable`, and killed the sweep -- discarding, on the first real
    run, the 1260 windows already computed for three earlier stems.
    """
    seq, truth = synthetic_drive(seconds=400.0)
    holed = _truth_with_hole(truth, from_rel_s=HOLE_FROM_S, to_rel_s=HOLE_TO_S)
    assert align_to_sequence(seq, holed).is_usable, "the hole must not refuse the whole stem"

    intact = evaluate_sequence(seq, truth, [60])
    dropped: list = []
    results = evaluate_sequence(seq, holed, [60], dropped=dropped)

    assert len(dropped) == 1, "exactly the window spanning the hole"
    assert dropped[0].sequence == seq.name
    assert dropped[0].length_s == 60
    assert dropped[0].start_idx == 900
    assert "no truth sample within" in dropped[0].reason

    assert results, "the covered windows must still grade"
    starts = {r.start_idx for r in results}
    assert 900 not in starts, "the uncovered window must contribute no result"
    assert starts == {r.start_idx for r in intact} - {900}

    # Every surviving window scores exactly what it scored against the intact track: dropping one
    # window must not perturb another, and the filter runs over the whole stream either way.
    kept = {(r.method, r.start_idx): r.metrics.drift_pct for r in intact if r.start_idx != 900}
    assert {(r.method, r.start_idx): r.metrics.drift_pct for r in results} == kept


def test_a_dropped_window_never_leaves_a_partial_set_of_methods():
    """The failure that would misreport without a wrong number anywhere in it.

    Three paths inside one window reach the truth track, so a `try` around any single one of them
    would append `filter` and not `strapdown`. Every count in `summary.json` is per method and per
    length, and a window contributing two methods instead of three makes those counts disagree
    while each individual metric stays correct.
    """
    seq, truth = synthetic_drive(seconds=400.0)
    holed = _truth_with_hole(truth, from_rel_s=HOLE_FROM_S, to_rel_s=HOLE_TO_S)
    dropped: list = []
    results = evaluate_sequence(seq, holed, [60], dropped=dropped)

    per_method = {m: sorted(r.start_idx for r in results if r.method == m) for m in METHODS}
    assert len(set(map(tuple, per_method.values()))) == 1, (
        f"methods graded different windows: {per_method}"
    )
    assert len(results) == len(METHODS) * len(per_method["filter"])


def test_a_dropped_window_is_counted_in_the_summary_beside_the_results(tmp_path):
    """D-067: the omission travels with the number. A run that graded five windows and dropped one
    is a different result from one that graded five, and no metric shows the difference."""
    seq, truth = synthetic_drive(seconds=400.0)
    holed = _truth_with_hole(truth, from_rel_s=HOLE_FROM_S, to_rel_s=HOLE_TO_S)
    dropped: list = []
    results = evaluate_sequence(seq, holed, [60], dropped=dropped)

    stamp = seed_everything(0)
    write_artefacts(tmp_path, stamp, results, None, dropped)
    written = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))

    assert written["n_dropped_windows"] == 1
    assert written["n_windows"] == len(results)
    row = written["dropped_windows"][0]
    assert (row["sequence"], row["length_s"], row["start_idx"]) == (seq.name, 60, 900)
    assert "no truth sample within" in row["reason"]


def test_a_run_with_no_gaps_reports_zero_dropped_rather_than_omitting_the_field(tmp_path):
    """A count that is absent when it is zero cannot be distinguished from a count nobody wrote."""
    seq, truth = synthetic_drive(seconds=200.0)
    dropped: list = []
    results = evaluate_sequence(seq, truth, [60], dropped=dropped)
    assert dropped == []

    written = write_artefacts(tmp_path, seed_everything(0), results, None, dropped)
    assert written["n_dropped_windows"] == 0
    assert written["dropped_windows"] == []


def test_a_dropped_window_is_announced_even_when_no_sink_collects_it(capsys):
    """A caller that omits the sink gets a smaller result set. It must not get a quiet one."""
    seq, truth = synthetic_drive(seconds=400.0)
    holed = _truth_with_hole(truth, from_rel_s=HOLE_FROM_S, to_rel_s=HOLE_TO_S)
    evaluate_sequence(seq, holed, [60])
    assert "DROPPED WINDOW" in capsys.readouterr().err


def test_a_window_the_vehicle_never_moved_over_is_dropped_not_divided_by(capsys):
    """D-093. `drift_pct` is `error / distance`, and a parked vehicle has no distance.

    Found on the first sweep of the re-picked split: S3c has one 10 s window whose eleven truth
    epochs all carry the identical fix, and the bare `ValueError` it raised escaped
    `evaluate_sequence` and killed the run after S3a had already produced 1191 results -- D-089's
    failure from a second cause. The stationary window here is built the same way: the truth track
    holds one position for the whole window while the `S-` clock keeps running.
    """
    seq, truth = synthetic_drive(seconds=400.0)
    frozen_from, frozen_to = 90.0, 152.0  # covers the second 60 s window end to end
    hold = (truth.t_s >= START_OF_DAY_S + frozen_from) & (truth.t_s <= START_OF_DAY_S + frozen_to)
    lat = truth.lat.copy()
    lat[hold] = lat[hold][0]
    parked = TruthTrack(
        name=truth.name, t_s=truth.t_s, lat=lat, lon=truth.lon, source=truth.source
    )

    dropped: list = []
    results = evaluate_sequence(seq, parked, [60], dropped=dropped)

    assert [d.start_idx for d in dropped] == [900]
    assert dropped[0].kind == "zero_distance"
    assert "must be excluded from the sweep" in dropped[0].reason
    assert "DROPPED WINDOW" in capsys.readouterr().err

    assert results, "the windows either side of the stop must still grade"
    assert 900 not in {r.start_idx for r in results}
    per_method = {m: sorted(r.start_idx for r in results if r.method == m) for m in METHODS}
    assert len(set(map(tuple, per_method.values()))) == 1, "a dropped window must take all methods"


def test_a_real_metric_defect_is_not_swallowed_as_a_dropped_window():
    """The reason `ZeroDistanceOutage` is a named subclass rather than a bare `ValueError`.

    `evaluate_outage` also raises plain `ValueError` for a shape mismatch, an empty yaw sequence
    and an unhandled CRSE convention -- all real defects. If the per-window catch took the base
    class, every one of them would become a silently smaller result set.
    """
    import numpy as np

    from eval.metrics.core import ZeroDistanceOutage, evaluate_outage

    assert issubclass(ZeroDistanceOutage, ValueError)
    with pytest.raises(ValueError) as exc:
        evaluate_outage(
            est_disp=np.zeros((3, 2)),
            true_disp=np.zeros((4, 2)),  # deliberate shape mismatch
            est_yaw=np.zeros(3),
            true_yaw=np.zeros(3),
            distance_m=100.0,
            duration_s=3.0,
        )
    assert not isinstance(exc.value, ZeroDistanceOutage), (
        "a shape mismatch must not be catchable as a dropped window"
    )


# ------------------------------------------------------------------------------------------
# Filter initialisation (D-094)
# ------------------------------------------------------------------------------------------


def test_the_filter_is_started_from_the_gnss_fixes_and_not_from_identity():
    """`run_filter` used to construct `InEKF(cfg)` and propagate from R = R_sv = I, v = 0, p = 0.

    On real data that integrates gravity into the horizontal axes and the run diverges. This
    fixture cannot show the divergence -- `synthetic_drive` builds a level phone driving due
    north, which is the one case where identity is correct -- so what it checks is that the
    initialiser reads the fixes at all and agrees with them.
    """
    seq, truth = synthetic_drive(seconds=200.0, mps=15.0)
    _, accel, _ = imu_stream(seq)
    fix_idx, fix_ned, _ = fix_arrays(seq, float(truth.lat[0]), float(truth.lon[0]))

    f = InEKF(FilterConfig())
    init = initialise_filter(f, seq, accel, fix_idx, fix_ned)

    assert init.n_warmup_fixes >= 2
    assert init.speed_mps == pytest.approx(15.0, rel=0.02), "speed from the differenced fixes"
    assert init.yaw_rad == pytest.approx(0.0, abs=1e-6), "driving due north"
    assert f.state.p[:2] == pytest.approx(fix_ned[0][:2], abs=1e-6), "position is the first fix"


def test_initialisation_reads_only_the_warmup_and_never_the_truth_track():
    """Two properties that are easy to lose and invisible once lost.

    The initialiser must not see a sample from beyond the warmup, because every outage starts
    later and that would initialise a window with its own future. And it must not touch truth:
    `initial_state_from_truth` exists for the strapdown *baseline* (D-064), which is handed truth
    deliberately because it is a floor rather than a system.
    """
    import inspect

    import eval.run as run_mod

    params = set(inspect.signature(run_mod.initialise_filter).parameters)
    assert not params & {"truth", "truth_track"}, (
        "the filter must be initialised from the `S-` stream, never from ground truth -- "
        "`initial_state_from_truth` is the strapdown baseline's, and only its (D-064)"
    )

    seq, truth = synthetic_drive(seconds=400.0, mps=15.0)
    _, accel, _ = imu_stream(seq)
    fix_idx, fix_ned, _ = fix_arrays(seq, float(truth.lat[0]), float(truth.lon[0]))
    f = InEKF(FilterConfig())
    init = initialise_filter(f, seq, accel, fix_idx, fix_ned, warmup_s=run_mod.WARMUP_S)
    # 30 s of warmup at a 9 s fix interval: fixes at 0, 9, 18, 27 s and no more.
    assert init.n_warmup_fixes == 4


def test_the_mount_block_of_p0_carries_the_measured_spread_not_the_fallback():
    """D-073 returns a spread precisely so `P0` does not have to fall back to a stated 5 degrees,
    and until now nothing outside `tests/test_mount.py` ever called it."""
    seq, truth = synthetic_drive(seconds=200.0, mps=15.0, accel_bias_x=0.4)
    _, accel, _ = imu_stream(seq)
    fix_idx, fix_ned, _ = fix_arrays(seq, float(truth.lat[0]), float(truth.lon[0]))
    f = InEKF(FilterConfig())
    init = initialise_filter(f, seq, accel, fix_idx, fix_ned)

    assert np.isfinite(init.mount_spread_rad), "the PCA initialiser must have run"
    assert f.P[15, 15] == pytest.approx(init.mount_spread_rad**2, rel=1e-9)


# --------------------------------------------------------------------------------------------
# D-115: process noise read from the stream, and the Doppler velocity as a measurement
# --------------------------------------------------------------------------------------------


def test_the_white_level_of_a_white_stream_is_its_sigma():
    """`stream_white_level` is the residual from a 5-sample centred mean, corrected for the
    1 - 1/5 of the variance the mean removes; on white noise it returns sigma to a few percent,
    and a slow ramp -- the vehicle's own dynamics -- does not register as noise."""
    from eval.run import stream_white_level

    rng = np.random.default_rng(3)
    sigma = np.array([0.5, 2.0, 0.05])
    x = rng.normal(0.0, 1.0, (20_000, 3)) * sigma
    assert stream_white_level(x) == pytest.approx(sigma, rel=0.03)
    ramp = np.linspace(0.0, 30.0, 20_000)[:, None] * np.array([1.0, -1.0, 0.5])
    assert stream_white_level(x + ramp) == pytest.approx(sigma, rel=0.03)
    x[100] = np.nan
    assert stream_white_level(x) == pytest.approx(sigma, rel=0.03), "NaN rows are dropped"


def test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it():
    """A rattling phone is filtered as one; a still one keeps the Allan-run floor (D-045)."""
    from eval.run import in_motion_config

    cfg = FilterConfig()
    rng = np.random.default_rng(5)
    dt = np.full(2999, 0.1)
    quiet_gyro = rng.normal(0.0, 1e-5, (3000, 3))
    quiet_accel = rng.normal(0.0, 1e-4, (3000, 3)) + np.array([0.0, 0.0, -G])
    same = in_motion_config(cfg, quiet_gyro, quiet_accel, dt, upto=300)
    assert same.gyro_arw == cfg.gyro_arw and same.accel_vrw == cfg.accel_vrw

    loud_gyro = rng.normal(0.0, np.deg2rad(12.0), (3000, 3))  # Vw4's yaw axis, per sample
    loud_accel = rng.normal(0.0, 2.3, (3000, 3)) + np.array([0.0, 0.0, -G])
    loud = in_motion_config(cfg, loud_gyro, loud_accel, dt, upto=300)
    assert loud.gyro_arw == pytest.approx(np.deg2rad(12.0) * np.sqrt(0.1), rel=0.15)
    assert loud.accel_vrw == pytest.approx(2.3 * np.sqrt(0.1), rel=0.15)
    assert loud.zaru_sigma == cfg.zaru_sigma, (
        "ZARU's R is a standstill figure and never the in-motion level: the config value is the "
        "Allan floor, and `_step_constraints` reads the stop's own level above it (D-131)"
    )
    assert cfg.gyro_arw == FilterConfig().gyro_arw, "the input config is not modified"
    assert in_motion_config(cfg, loud_gyro, loud_accel, dt, upto=3) is cfg, "too short: unchanged"


def test_step_constraints_tests_zaru_against_the_stops_own_gyro_level():
    """D-131 wiring. At a detected stop the harness reads ZARU's sigma from the detector's own
    window (`zaru_sigma_from_window`) and passes it to `update_zaru`; the config value is only
    the floor. On a synthetic standstill carrying 1 deg/s of idle vibration per axis -- S3a's
    level -- the desk figure refused 98.8 % of the offered ZARUs (D-130, 1,356 of 1,372); the
    window figure accepts them, and the sigma the pass used is reported next to the counts."""
    from eval.run import _mean_zaru_sigma, _step_constraints

    rng = np.random.default_rng(7)
    n = 300
    level = np.deg2rad(1.0)
    gyro = np.deg2rad([0.1, -0.05, 0.15]) + rng.normal(0.0, level, (n, 3))
    accel = np.array([0.0, 0.0, -G]) + rng.normal(0.0, 0.03, (n, 3))  # var 9e-4 << 0.02
    cfg = FilterConfig()
    f = InEKF(cfg)
    window = int(round(cfg.zupt_window_s * SAMPLE_RATE_HZ))
    counts: dict[str, float] = dict(zupt=0, zaru_ok=0, zaru_no=0, nhc=0)
    for k in range(n):
        _step_constraints(f, k, gyro, accel, cfg, window, counts)
    offered = counts["zaru_ok"] + counts["zaru_no"]
    assert counts["zupt"] == offered > 100, "ZUPT and ZARU are offered together (D-004)"
    assert counts["zaru_ok"] / offered > 0.95, f"{counts['zaru_no']} of {offered} refused"
    assert _mean_zaru_sigma(counts) == pytest.approx(level, rel=0.2)
    assert np.isnan(_mean_zaru_sigma(dict(zaru_ok=0, zaru_no=0))), "no stop: NaN, not 0"


def test_the_doppler_velocity_is_along_and_across_the_course():
    """Speed sigma along the course, cross-track sigma across it, rotated into north/east."""
    from eval.run import velocity_measurement

    cfg = FilterConfig(gnss_speed_sigma_mps=0.5, course_cross_track_sigma_mps=0.2)
    v, cov = velocity_measurement(cfg, np.pi / 2, 10.0)  # due east
    assert v == pytest.approx([0.0, 10.0], abs=1e-12)
    assert cov == pytest.approx(np.diag([0.2**2, 0.5**2]), abs=1e-12)
    v, cov = velocity_measurement(cfg, 0.0, 7.0)  # due north
    assert v == pytest.approx([7.0, 0.0], abs=1e-12)
    assert cov == pytest.approx(np.diag([0.5**2, 0.2**2]), abs=1e-12)

