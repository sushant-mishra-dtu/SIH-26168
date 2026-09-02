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

from eval.loaders.io_vnbd import SAMPLE_RATE_HZ, Sequence
from eval.loaders.truth import TruthTrack, align_to_sequence
from eval.outages.inject import Outage
from eval.run import (
    EPOCH_STRIDE,
    GATE1_LENGTH_S,
    METHODS,
    SequenceUnusable,
    assert_uniform_grid,
    evaluate_sequence,
    fix_arrays,
    gate1_ratio,
    imu_stream,
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


def _date_strings(seconds_of_day: np.ndarray) -> list[str]:
    """The shipped `DATE (YYYY-MO-DD HH-MI-SS_SSS)` spelling, which `seconds_of_day` parses."""
    out = []
    for s in seconds_of_day:
        h, rem = divmod(float(s), 3600.0)
        m, sec = divmod(rem, 60.0)
        whole = int(sec)
        ms = int(round((sec - whole) * 1000))
        out.append(f"2019-10-11 {int(h):02d}-{int(m):02d}-{whole:02d}_{ms:03d}")
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


def test_the_gyro_axis_mapping_is_the_one_d047_established():
    """`gyro_yaw` is device **x**, not the vertical axis (D-047). Getting this wrong is silent:
    the filter still runs and the trajectory still looks like a drive."""
    seq, _ = synthetic_drive()
    seq.imu["gyro_yaw"] = 1.0
    seq.imu["gyro_pitch"] = 2.0
    seq.imu["gyro_roll"] = 3.0
    gyro, _, _ = imu_stream(seq)
    assert gyro[0] == pytest.approx([1.0, 2.0, 3.0])


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
