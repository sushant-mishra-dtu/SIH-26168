"""Tests for the Allan-variance seeding of Q.

The estimator is checked against processes whose Allan deviation is known in closed form, not
against a previously-recorded output of itself. A regression test that pins last week's numbers
would have passed just as happily on the sign error, the 0.664 inversion, and the contaminated
fit band -- all three of which these catch.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.reference.inekf import FilterConfig, is_stationary
from eval.allan import (
    ACCEL_AXES,
    BIAS_INSTABILITY_COEFF,
    GYRO_AXES,
    MAX_TAU_FRACTION,
    MPS2_TO_MILLI_G,
    RAD_PER_S_SQRT_S_TO_DEG_PER_SQRT_HR,
    SLOPE_TOLERANCE,
    bias_instability,
    coefficients,
    find_stationary_segments,
    gauss_markov_bias_driving_noise,
    octave_taus,
    overlapping_allan_deviation,
    random_walk_coefficient,
)
from eval.loaders.columns import FEATURE_COLUMNS, LeakageError, assert_no_leakage, normalise
from eval.loaders.io_vnbd import SAMPLE_RATE_HZ, Sequence

DT = 1.0 / SAMPLE_RATE_HZ


# --------------------------------------------------------------------------------------------
# The estimator, against closed-form answers
# --------------------------------------------------------------------------------------------


def test_white_noise_gives_the_analytic_allan_deviation():
    """For white rate noise of per-sample sigma, `sigma_A(tau) = sigma sqrt(dt / tau)` exactly.

    This is the one case where the right answer is known independently of the implementation, so
    it is the test that actually pins the estimator's normalisation.
    """
    rng = np.random.default_rng(26168)
    sigma = 0.01
    x = rng.normal(0.0, sigma, size=200_000)

    curve = overlapping_allan_deviation(x, DT)
    expected = sigma * np.sqrt(DT / curve.tau_s)

    # Tolerance is the estimator's own predicted confidence, not a hand-picked rtol: at the longest
    # taus a 20 000 s record holds only ~10 independent clusters and 13% scatter is the correct
    # answer, not a defect. Checking against `rel_error` tests the error bars too.
    assert np.all(np.abs(curve.adev - expected) <= 3.0 * curve.rel_error * expected)
    # ...and at short tau, where the clusters are plentiful, it must be tight.
    tight = curve.tau_s <= 10.0
    assert np.allclose(curve.adev[tight], expected[tight], rtol=0.02)


def test_white_noise_slope_is_minus_one_half():
    rng = np.random.default_rng(7)
    curve = overlapping_allan_deviation(rng.normal(0.0, 0.02, 200_000), DT)
    _, slope = random_walk_coefficient(curve)
    assert slope == pytest.approx(-0.5, abs=SLOPE_TOLERANCE)


def test_random_walk_coefficient_recovers_sigma_at_tau_one_second():
    """`N = sigma sqrt(dt)`: the number FilterConfig wants, in rad/s/sqrt(Hz)."""
    rng = np.random.default_rng(99)
    sigma = 0.004
    curve = overlapping_allan_deviation(rng.normal(0.0, sigma, 200_000), DT)
    coefficient, _ = random_walk_coefficient(curve)
    assert coefficient == pytest.approx(sigma * math.sqrt(DT), rel=0.05)


def test_a_constant_offset_is_annihilated():
    """Gravity sits on the accelerometer's vertical axis at all times and must not appear in the
    curve. The second difference kills constants; this proves it rather than assuming it."""
    rng = np.random.default_rng(3)
    x = rng.normal(0.0, 0.01, 50_000)
    plain = overlapping_allan_deviation(x, DT)
    offset = overlapping_allan_deviation(x + 9.80665, DT)
    assert np.allclose(plain.adev, offset.adev, rtol=1e-9)


def test_integrated_white_noise_reads_as_plus_one_half_and_is_refused():
    """A rate random walk has slope +1/2. Its tau = 1 s value has the units of an ARW and is not
    one -- the whiteness gate is what stops it becoming one."""
    rng = np.random.default_rng(11)
    walk = np.cumsum(rng.normal(0.0, 0.001, 100_000))
    curve = overlapping_allan_deviation(walk, DT, axis="gyro_yaw", unit="rad/s")
    _, slope = random_walk_coefficient(curve)

    assert slope > 0.3
    assert coefficients(curve).random_walk_is_white is False


def test_taus_stop_at_the_max_fraction_of_the_record():
    n = 10_000
    taus = octave_taus(n, DT)
    assert taus.max() <= n * DT * MAX_TAU_FRACTION + 1e-9
    assert taus.min() == pytest.approx(DT)
    assert np.all(np.diff(taus) > 0)


def test_every_tau_is_an_exact_multiple_of_dt():
    for tau in octave_taus(50_000, DT):
        assert (tau / DT) == pytest.approx(round(tau / DT))


# --------------------------------------------------------------------------------------------
# Bias instability -- the 0.664 that is a division
# --------------------------------------------------------------------------------------------


def test_bias_instability_coefficient_is_the_ieee_value():
    assert BIAS_INSTABILITY_COEFF == pytest.approx(0.6643, abs=5e-4)
    assert BIAS_INSTABILITY_COEFF == pytest.approx(math.sqrt(2 * math.log(2) / math.pi))


def test_bias_instability_divides_by_the_coefficient():
    """`sigma_min = 0.664 B`, so `B = sigma_min / 0.664`. Multiplying instead understates B by
    2.27x, which is the direction that makes a filter over-trust a drifting bias."""
    rng = np.random.default_rng(5)
    curve = overlapping_allan_deviation(rng.normal(0.0, 0.01, 20_000), DT)
    b, tau, _, _ = bias_instability(curve)

    assert b == pytest.approx(curve.adev.min() / BIAS_INSTABILITY_COEFF)
    assert b > curve.adev.min()  # a division by 0.664 makes it larger, never smaller
    assert tau == pytest.approx(curve.tau_s[int(np.argmin(curve.adev))])


def test_bias_instability_flags_a_minimum_sitting_at_the_last_tau():
    """Pure white noise descends monotonically, so its minimum is always the last point -- the
    record simply never reached the floor. That has to be reported, not read as a measurement."""
    rng = np.random.default_rng(13)
    curve = overlapping_allan_deviation(rng.normal(0.0, 0.01, 40_000), DT)
    _, _, at_edge, _ = bias_instability(curve)
    assert at_edge is True


def test_gauss_markov_driving_noise_matches_the_closed_form():
    assert gauss_markov_bias_driving_noise(2.0e-4, 27.7) == pytest.approx(
        2.0e-4 * math.sqrt(2.0 / 27.7)
    )
    with pytest.raises(ValueError):
        gauss_markov_bias_driving_noise(1e-4, 0.0)


# --------------------------------------------------------------------------------------------
# Units -- the conversion the FilterConfig docstring turns on
# --------------------------------------------------------------------------------------------


def test_gyro_arw_conversion_reproduces_the_placeholder_being_replaced():
    """The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5 deg/sqrt(hr)
    phone range ERROR_BUDGET section 9 states. That inconsistency is R-2; this pins the arithmetic
    that establishes it."""
    assert 3.0e-3 * RAD_PER_S_SQRT_S_TO_DEG_PER_SQRT_HR == pytest.approx(10.31, abs=0.02)


def test_accel_bias_instability_conversion_to_milli_g():
    assert 0.00332469 * MPS2_TO_MILLI_G == pytest.approx(0.339, abs=0.002)
    assert 9.80665 * MPS2_TO_MILLI_G == pytest.approx(1000.0)


# --------------------------------------------------------------------------------------------
# Segment finding
# --------------------------------------------------------------------------------------------


def _sequence(accel: np.ndarray, gyro: np.ndarray, t_s: np.ndarray, name: str = "T") -> Sequence:
    imu = pd.DataFrame(
        {
            **{a: accel[:, i] for i, a in enumerate(ACCEL_AXES)},
            **{g: gyro[:, i] for i, g in enumerate(GYRO_AXES)},
            "time_since_start_ms": t_s * 1000.0,
        }
    )
    gnss = pd.DataFrame({"gps_lat": [0.0], "gps_lon": [0.0]})
    return Sequence(name=name, imu=imu, gnss=gnss, split="train")


def _still(n: int, seed: int = 1, accel_sigma: float = 0.01, gyro_sigma: float = 1e-4):
    rng = np.random.default_rng(seed)
    accel = rng.normal(0.0, accel_sigma, (n, 3))
    accel[:, 2] += 9.80665
    gyro = rng.normal(0.0, gyro_sigma, (n, 3))
    return accel, gyro


def test_finds_a_long_quiet_segment():
    n = 4_000  # 400 s at 10 Hz
    accel, gyro = _still(n)
    seq = _sequence(accel, gyro, np.arange(n) * DT)

    found = find_stationary_segments(seq, min_duration_s=120.0)

    assert len(found) == 1
    assert found[0].duration_s == pytest.approx(399.9, abs=0.2)
    assert found[0].dt_s == pytest.approx(DT)
    assert found[0].is_quiet is True


def test_moving_data_yields_no_segment():
    rng = np.random.default_rng(2)
    n = 4_000
    accel = rng.normal(0.0, 1.5, (n, 3))
    gyro = rng.normal(0.0, 0.3, (n, 3))
    assert find_stationary_segments(_sequence(accel, gyro, np.arange(n) * DT)) == []


def test_a_recorder_pause_splits_the_segment_rather_than_spanning_it():
    """S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so a run
    containing one is rejected outright -- averaging across it would report the pause as signal."""
    n = 4_000
    accel, gyro = _still(n)
    t = np.arange(n) * DT
    t[n // 2 :] += 285.0  # the pause

    found = find_stationary_segments(_sequence(accel, gyro, t), min_duration_s=120.0)

    assert found == []


def test_burst_mode_duplicate_timestamps_are_rejected():
    """The far side of S-I's pause logs at ~1 ms with 39% of samples sharing a timestamp."""
    n = 4_000
    accel, gyro = _still(n)
    t = np.arange(n) * DT
    t[n // 2 :] = t[n // 2] + np.repeat(np.arange(n - n // 2) // 3, 1) * 0.001

    assert find_stationary_segments(_sequence(accel, gyro, t), min_duration_s=120.0) == []


def test_short_segments_are_below_the_minimum():
    n = 800  # 80 s
    accel, gyro = _still(n)
    assert find_stationary_segments(_sequence(accel, gyro, np.arange(n) * DT)) == []


def test_a_vibrating_cabin_is_stationary_but_not_quiet():
    """Idling with an occupant passes the ZUPT detector and must still be excluded from noise
    characterisation: its Allan curve measures the cabin, not the gyroscope."""
    n = 4_000
    # Loud enough that both quiet margins fail, quiet enough that the ZUPT detector still fires:
    # mean |gyro| is ~1.6 sigma = 0.008 rad/s, under the 0.01 rad/s threshold (D-115); accel
    # variance is 0.0144, under 0.02, and both are more than a tenth of their thresholds.
    accel, gyro = _still(n, accel_sigma=0.12, gyro_sigma=0.005)
    found = find_stationary_segments(_sequence(accel, gyro, np.arange(n) * DT))

    assert len(found) == 1
    assert found[0].is_quiet is False


def test_segment_finder_agrees_with_the_filters_own_detector():
    """The vectorised criterion must be the same criterion as `is_stationary`, not a lookalike.

    Every accepted segment is re-checked window by window through the filter's own function; a
    drift between the two would mean Q was characterised on samples the filter will not ZUPT on.
    """
    cfg = FilterConfig()
    n = 4_000
    accel, gyro = _still(n)
    seq = _sequence(accel, gyro, np.arange(n) * DT)

    found = find_stationary_segments(seq, min_duration_s=120.0, window_s=10.0)
    assert found

    window = int(10.0 * SAMPLE_RATE_HZ)
    seg = found[0]
    for start in range(seg.start, seg.stop - window, window):
        assert is_stationary(accel[start : start + window], gyro[start : start + window], cfg)


# --------------------------------------------------------------------------------------------
# The leakage guard, against the headers IO-VNBD actually ships
# --------------------------------------------------------------------------------------------

SHIPPED_S_HEADERS = [
    "GPS LATITUDE (degrees)", " GPS LONGITUDE (degrees)", " GPS ALTITUDE (m)",
    " GPS SPEED (Kmh)", " GPS ACCURACY (m)", " GPS ORIENTATION (\xb0)",
    "GPS SATELLITES IN RANGE", " TIME SINCE START (ms)",
    " DATE (YYYY-MO-DD HH-MI-SS_SSS)",
    " ACCELEROMETER X (m/s\xb2) ", " ACCELEROMETER Y (m/s\xb2)", " ACCELEROMETER Z (m/s\xb2)",
    " GRAVITY X (m/s\xb2)", " GRAVITY Y (m/s\xb2)", " GRAVITY Z (m/s\xb2)",
    " GYROSCOPE Yaw (rad/s)", " GYROSCOPE Pitch (rad/s)", " GYROSCOPE Roll (rad/s)",
    " MAGNETIC FIELD X (μT)", " MAGNETIC FIELD Y (μT)", " MAGNETIC FIELD Z (μT)",
    " ORIENTATION (Yaw) (\xb0)", " ORIENTATION (Pitch) (\xb0)", " ORIENTATION (Roll ) (\xb0)",
]


def test_the_headers_iovnbd_actually_ships_pass_the_guard():
    """Before the aliases, every one of these normalised to a name that was not on the allowlist,
    so the guard rejected every real 'S-' file and nothing in the repo had ever loaded the
    dataset."""
    assert_no_leakage(SHIPPED_S_HEADERS, context="test")


def test_the_three_orientation_columns_stay_three_columns():
    """Generic paren-stripping collapsed all three to the single name 'orientation'."""
    names = {normalise(c) for c in SHIPPED_S_HEADERS if c.strip().startswith("ORIENTATION (")}
    assert names == {"orientation_yaw", "orientation_pitch", "orientation_roll"}


def test_both_shipped_gyro_spellings_reach_the_same_canonical_names():
    """The categorised folder writes Yaw/Pitch/Roll and the uncategorised folder writes X/Y/Z for
    byte-identical columns (verified on S-S1, which ships in both)."""
    yaw_pitch_roll = [
        normalise(c)
        for c in ("GYROSCOPE Yaw (rad/s)", "GYROSCOPE Pitch (rad/s)", "GYROSCOPE Roll (rad/s)")
    ]
    xyz = [
        normalise(c)
        for c in ("GYROSCOPE X (rad/s)", "GYROSCOPE Y (rad/s)", "GYROSCOPE Z (rad/s)")
    ]
    assert yaw_pitch_roll == xyz == ["gyro_yaw", "gyro_pitch", "gyro_roll"]


def test_the_satellite_column_ships_with_and_without_the_gps_prefix():
    assert normalise("GPS SATELLITES IN RANGE") == normalise("SATELLITES IN RANGE") == "gps_sats"


def test_a_truncated_date_format_string_still_normalises():
    assert normalise("DATE (YYYY-MO-DD HH-MI-SS_SSS") == "date"


def test_the_v_streams_time_column_is_not_laundered_by_the_alias():
    """'Time Since Start of Day (seconds)' is a 'V-' column and a different quantity. If the alias
    were anchored loosely it would map onto an allowed name and pass."""
    assert normalise("Time Since Start of Day (seconds)") != "time_since_start_ms"
    with pytest.raises(LeakageError):
        assert_no_leakage(["Time Since Start of Day (seconds)"])


def test_the_v_stream_header_is_still_rejected_wholesale():
    """The aliases must not have widened the guard. These are the real 'V-' column names."""
    for column in (
        " Wheel Speed Front Left (rad/sec)",
        " Steering Angle (degrees)",
        " Engine Speed (rev/min)",
        " Brake Pressure (psi)",
        " Accelerator Pedal Position (0 or 1)",
    ):
        with pytest.raises(LeakageError):
            assert_no_leakage([column])


def test_the_allan_axes_are_all_permitted_features():
    """Nothing this module reads may be outside the inertial feature set."""
    assert set(GYRO_AXES) | set(ACCEL_AXES) <= FEATURE_COLUMNS


# --------------------------------------------------------------------------------------------
# FilterConfig must not drift from the artefact it was seeded from
# --------------------------------------------------------------------------------------------

SUMMARY = Path(__file__).resolve().parents[1] / "eval" / "figures" / "allan_summary.json"


@pytest.mark.skipif(not SUMMARY.exists(), reason="run `python -m eval.allan` to generate it")
def test_filter_config_matches_the_measured_summary():
    """The four noise defaults must equal what `eval/allan.py` last measured, to 3 significant
    figures.

    Without this, the artefact and the config are two independent copies of the same four numbers
    and nothing notices when they diverge -- which is the failure mode that put a 10.3 deg/sqrt(hr)
    placeholder in a filter whose own error budget said 0.5-5 (R-2).
    """
    measured = json.loads(SUMMARY.read_text(encoding="utf-8"))["summary"]
    cfg = FilterConfig()

    for attribute, key in (
        ("gyro_arw", "gyro_arw_rad_s_sqrt_hz"),
        ("accel_vrw", "accel_vrw_mps2_sqrt_hz"),
        ("gyro_bias_rw", "gyro_bias_rw_rad_s2_sqrt_hz"),
        ("accel_bias_rw", "accel_bias_rw_mps3_sqrt_hz"),
    ):
        assert getattr(cfg, attribute) == pytest.approx(measured[key], rel=5e-3), attribute


@pytest.mark.skipif(not SUMMARY.exists(), reason="run `python -m eval.allan` to generate it")
def test_the_measured_gyro_arw_is_inside_the_error_budgets_phone_range():
    """ERROR_BUDGET section 9.3 states 0.5-5 deg/sqrt(hr) for phone MEMS. A measurement outside it
    means either the measurement or the budget is wrong, and both need saying out loud."""
    measured = json.loads(SUMMARY.read_text(encoding="utf-8"))["summary"]
    assert 0.5 <= measured["gyro_arw_deg_sqrt_hr"] <= 5.0


@pytest.mark.skipif(not SUMMARY.exists(), reason="run `python -m eval.allan` to generate it")
def test_every_analysed_segment_was_quiet_and_uniformly_sampled():
    report = json.loads(SUMMARY.read_text(encoding="utf-8"))
    quiet = [s for s in report["segments"] if s["is_quiet"]]

    assert quiet, "no quiet segment survived"
    for segment in quiet:
        assert segment["dt_s"] == pytest.approx(DT, abs=5e-3)
        assert segment["max_gap_s"] <= 0.5
        assert segment["duplicate_dt_fraction"] <= 0.02
        assert segment["duration_s"] >= 120.0
