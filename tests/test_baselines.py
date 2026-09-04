"""Tests for the two Gate 1 baselines.

Every numerical case here is hand-computed from closed-form physics or from arithmetic already
written down in `docs/ERROR_BUDGET.md`, never from the baselines' own output. A baseline checked
against itself proves the code is deterministic and nothing else, and Gate 1 is a *ratio* against
these numbers -- if a baseline is quietly wrong, the gate passes or fails for the wrong reason.
"""

from __future__ import annotations

import numpy as np
import pytest

from eval.baselines import (
    MIN_HEADING_DISPLACEMENT_M,
    BaselineTrajectory,
    course_over_ground,
    epoch_times,
    gnss_available,
    naive_strapdown,
    yaw_only_rotation,
)
from eval.outages.inject import PREDICTION_CADENCE_S, SAMPLE_RATE_HZ

G = 9.80665
DT = 1.0 / SAMPLE_RATE_HZ
STRIDE = SAMPLE_RATE_HZ  # IMU samples per 1 s prediction epoch


def _level_imu(n: int, *, accel_bias=(0.0, 0.0, 0.0), gyro_bias=(0.0, 0.0, 0.0)):
    """A perfectly still, level phone, plus whatever bias the case is about.

    A stationary accelerometer reads specific force, which is `-g` in the body z of a level
    vehicle with NED's z pointing down: `propagate_nominal` adds gravity back, so this integrates
    to no motion at all before any bias is added.
    """
    accel = np.tile([0.0, 0.0, -G], (n, 1)) + np.asarray(accel_bias, dtype=float)
    gyro = np.tile(np.asarray(gyro_bias, dtype=float), (n, 1))
    return gyro, accel


# ------------------------------------------------------------------------------------------
# Naive strapdown -- H-2's stated exception, and the arithmetic it exists to measure
# ------------------------------------------------------------------------------------------


def test_a_still_level_phone_does_not_move():
    """The null case. If this drifts, every number below it is measuring the integrator."""
    gyro, accel = _level_imu(600)
    traj = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=np.eye(3),
        initial_velocity_ned=np.zeros(3),
        epoch_stride=STRIDE,
    )
    assert traj.n_epochs == 60
    assert np.allclose(traj.displacements_ned, 0.0, atol=1e-9)


def test_ten_milli_g_of_accel_bias_costs_the_176_m_the_budget_says():
    """docs/ERROR_BUDGET.md section 2, made into a measurement rather than an example.

    Closed form for a constant unmodelled specific force `b` from rest: `x = 0.5 * b * t^2`. At
    10 mg = 0.0980665 m/s^2 over 60 s that is 0.5 * 0.0980665 * 3600 = **176.5 m**, which is the
    figure the budget and the README both quote as the reason acceleration is never
    double-integrated for speed. This is the one place in the repo that does it, and this is what
    it costs.
    """
    bias = 0.010 * G  # 10 mg, in m/s^2
    gyro, accel = _level_imu(600, accel_bias=(bias, 0.0, 0.0))
    traj = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=np.eye(3),
        initial_velocity_ned=np.zeros(3),
        epoch_stride=STRIDE,
    )
    north = float(traj.displacements_ned[:, 0].sum())
    assert north == pytest.approx(0.5 * bias * 60.0**2, rel=1e-6)
    assert north == pytest.approx(176.5, abs=0.1)


def test_constant_velocity_integrates_to_constant_displacement():
    """15 m/s north, no specific force beyond gravity: 15 m per 1 s epoch, exactly."""
    gyro, accel = _level_imu(300)
    traj = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=np.eye(3),
        initial_velocity_ned=np.array([15.0, 0.0, 0.0]),
        epoch_stride=STRIDE,
    )
    assert traj.displacements_ned == pytest.approx(np.tile([15.0, 0.0], (30, 1)))
    assert traj.yaw_rad == pytest.approx(np.zeros(30))


def test_a_pitch_gyro_bias_leaks_gravity_into_the_horizontal_as_the_cubic_says():
    """The mechanism that makes gyro bias the dominant term (docs/ERROR_BUDGET.md section 3),
    against its closed form.

    A gyro bias `w` about the body y axis tilts the *estimated* attitude by `theta = w t` while the
    vehicle stays level, so the strapdown resolves the accelerometer's `-g` body reading into the
    navigation frame with a pitch error and leaks `-g sin(theta) ~ -g w t` into north. Integrating
    twice:

        p_north(t) = -g w t^3 / 6

    At `w = 1e-3` rad/s over 30 s that is **-44.13 m** -- from a bias of 0.057 deg/s, on a vehicle
    that never moved. Measured -44.128 m, 4.5e-5 relative, the residual being `sin(theta)` against
    `theta` at `theta_max` = 0.03 rad.
    """
    w, t = 1e-3, 30.0
    n = int(t * SAMPLE_RATE_HZ)
    gyro, accel = _level_imu(n, gyro_bias=(0.0, w, 0.0))
    traj = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=np.eye(3),
        initial_velocity_ned=np.zeros(3),
        epoch_stride=STRIDE,
    )
    north = float(traj.displacements_ned[:, 0].sum())
    assert north == pytest.approx(-G * w * t**3 / 6.0, rel=1e-3)
    assert north == pytest.approx(-44.13, abs=0.01)


def test_a_yaw_gyro_bias_alone_does_not_bend_a_straight_strapdown_run():
    """**Deliberately asserting the null result**, because the obvious intuition is wrong and a
    future "fix" would be a real regression.

    Yaw is a rotation *about* the gravity vector, so a yaw error cannot mis-resolve gravity, and a
    strapdown carrying only gravity as specific force keeps its navigation-frame velocity exactly.
    The heading estimate is wrong the whole time and the position is not. The lateral
    `0.5 * b_g * v * t^2` in docs/ERROR_BUDGET.md section 3 is the error of a system that steers a
    *measured speed* by a gyro heading -- which is our method -- not of a pure strapdown, and the
    two must not be conflated when the four-trajectory figure puts them side by side.
    """
    gyro, accel = _level_imu(300, gyro_bias=(0.0, 0.0, 0.01))
    traj = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=np.eye(3),
        initial_velocity_ned=np.array([15.0, 0.0, 0.0]),
        epoch_stride=STRIDE,
    )
    assert traj.displacements_ned == pytest.approx(np.tile([15.0, 0.0], (30, 1)), abs=1e-9)


def test_the_initial_heading_rotates_the_whole_trajectory():
    """Due east at 15 m/s must come out as (0, 15) per epoch, not (15, 0)."""
    gyro, accel = _level_imu(100)
    rot = yaw_only_rotation(np.pi / 2)
    traj = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=rot,
        initial_velocity_ned=rot @ np.array([15.0, 0.0, 0.0]),
        epoch_stride=STRIDE,
    )
    assert traj.displacements_ned == pytest.approx(np.tile([0.0, 15.0], (10, 1)), abs=1e-9)
    assert traj.yaw_rad == pytest.approx(np.full(10, np.pi / 2))


def test_a_partial_epoch_is_refused_rather_than_silently_truncated():
    gyro, accel = _level_imu(605)
    with pytest.raises(ValueError, match="whole number"):
        naive_strapdown(
            gyro, accel, DT,
            initial_rotation=np.eye(3),
            initial_velocity_ned=np.zeros(3),
            epoch_stride=STRIDE,
        )


# ------------------------------------------------------------------------------------------
# GNSS-available -- zero-order hold at the measured 9 s cadence
# ------------------------------------------------------------------------------------------


def test_a_1_hz_receiver_reproduces_the_fixes_exactly():
    """With a fix on every epoch boundary the hold is the identity, so this isolates the lookup
    from the staircase the real 9 s cadence produces."""
    t_fix = np.arange(11, dtype=float)
    ned = np.column_stack([15.0 * t_fix, np.zeros(11)])
    traj = gnss_available(t_fix, ned, epoch_times(0.0, 10))
    assert traj.n_epochs == 10
    assert traj.displacements_ned == pytest.approx(np.tile([15.0, 0.0], (10, 1)))


def test_the_9_s_cadence_produces_a_staircase_and_the_hold_is_hand_checked():
    """Fixes at t = 0 and t = 9, epochs at t = 0..10. Hand-computed: epochs 1-8 hold fix 0 and so
    displace by 0; epoch 9 steps the whole 135 m at once; epoch 10 holds fix 1 and displaces 0.

    This is the shape of the real baseline -- median inter-fix interval 9.0 s
    (`eval.loaders.io_vnbd.GNSS_MEDIAN_INTERVAL_S`) -- and the reason its CTE and CRSE are a
    statement about the receiver's update rate rather than about its accuracy.
    """
    t_fix = np.array([0.0, 9.0])
    ned = np.array([[0.0, 0.0], [135.0, 0.0]])
    traj = gnss_available(t_fix, ned, epoch_times(0.0, 10))

    expected = np.zeros((10, 2))
    expected[8, 0] = 135.0  # the epoch spanning t = 8 -> 9
    assert traj.displacements_ned == pytest.approx(expected)
    assert float(traj.displacements_ned[:, 0].sum()) == pytest.approx(135.0)


def test_the_hold_never_reaches_forward_to_a_later_fix():
    """A window opening before the first fix has nothing to hold. Holding the *next* fix backwards
    would hand that epoch a position it did not have, which is a leak in time rather than in
    columns -- and just as invalidating."""
    with pytest.raises(ValueError, match="before the first fix"):
        gnss_available(np.array([5.0, 15.0]), np.zeros((2, 2)), epoch_times(0.0, 10))


def test_fixes_must_be_ordered():
    with pytest.raises(ValueError, match="strictly increasing"):
        gnss_available(np.array([0.0, 9.0, 4.0]), np.zeros((3, 2)), epoch_times(0.0, 10))


def test_no_fixes_at_all_is_an_error_not_an_empty_trajectory():
    with pytest.raises(ValueError, match="no GNSS fixes"):
        gnss_available(np.zeros(0), np.zeros((0, 2)), epoch_times(0.0, 10))


# ------------------------------------------------------------------------------------------
# Course over ground -- the only heading a lat/lon truth track can offer
# ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("north", "east", "expected_deg"),
    [(1.0, 0.0, 0.0), (0.0, 1.0, 90.0), (-1.0, 0.0, 180.0), (0.0, -1.0, -90.0), (1.0, 1.0, 45.0)],
)
def test_course_over_ground_is_ned_bearing(north, east, expected_deg):
    got = course_over_ground(np.array([[north, east]]))
    assert np.rad2deg(got[0]) == pytest.approx(expected_deg)


def test_a_stop_holds_the_previous_heading_rather_than_reading_noise_as_a_turn():
    """`atan2` of a sub-centimetre displacement is a uniformly-distributed angle, and a yaw RMSE
    that swallows one reports a large heading error at exactly the moment -- a stop -- when
    heading is least at risk."""
    disp = np.array([[10.0, 10.0], [1e-6, -1e-6], [0.0, 0.0], [10.0, 10.0]])
    got = course_over_ground(disp)
    assert got == pytest.approx(np.full(4, np.pi / 4))


def test_the_held_heading_before_any_motion_is_the_one_supplied():
    got = course_over_ground(np.zeros((3, 2)), initial_yaw_rad=1.25)
    assert got == pytest.approx(np.full(3, 1.25))


def test_the_hold_threshold_is_two_orders_below_the_nhc_speed_floor():
    """MIN_HEADING_DISPLACEMENT_M over one 1 s epoch is a speed, and it must sit far below the
    repo's existing statement of when direction of travel stops meaning anything."""
    from core.reference.inekf import FilterConfig

    speed = MIN_HEADING_DISPLACEMENT_M / PREDICTION_CADENCE_S
    assert speed == pytest.approx(0.01)
    assert speed < FilterConfig().nhc_min_speed / 50


# ------------------------------------------------------------------------------------------
# Shape contract -- both baselines feed one metrics path, so they must agree on shape
# ------------------------------------------------------------------------------------------


def test_epoch_times_are_boundaries_not_epochs():
    """`n` displacements need `n + 1` positions. Off by one here silently shortens every window."""
    t = epoch_times(30.0, 60)
    assert t.size == 61
    assert t[0] == 30.0 and t[-1] == 90.0


def test_a_trajectory_must_carry_one_heading_per_epoch():
    with pytest.raises(ValueError, match="one heading per epoch"):
        BaselineTrajectory(np.zeros((5, 2)), np.zeros(6))


def test_a_trajectory_refuses_non_finite_values():
    with pytest.raises(ValueError, match="non-finite"):
        BaselineTrajectory(np.array([[np.nan, 0.0]]), np.zeros(1))


def test_both_baselines_emit_the_same_shape_for_the_same_window():
    """Gate 1 divides one of these by the other, so a shape disagreement is a wrong ratio rather
    than a crash."""
    gyro, accel = _level_imu(600)
    strapdown = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=np.eye(3),
        initial_velocity_ned=np.zeros(3),
        epoch_stride=STRIDE,
    )
    t_fix = np.arange(0.0, 70.0, 9.0)
    gnss = gnss_available(
        t_fix, np.column_stack([15.0 * t_fix, np.zeros(t_fix.size)]), epoch_times(0.0, 60)
    )
    assert strapdown.displacements_ned.shape == gnss.displacements_ned.shape == (60, 2)
    assert strapdown.yaw_rad.shape == gnss.yaw_rad.shape == (60,)


# ------------------------------------------------------------------------------------------
# Scoring -- baselines in, OutageMetrics out, through the one metrics path and no other
# ------------------------------------------------------------------------------------------


def _straight_north_truth(name: str = "SYNTH", *, seconds: float = 120.0, mps: float = 15.0):
    """A synthetic 10 Hz `V-`-shaped truth track driving due north at a constant speed.

    Built here rather than loaded because the IO-VNBD CSVs are Git-LFS objects this container
    cannot fetch (D-059), and because a synthetic track is the only way to know the answer
    independently of the code under test. `TruthTrack` is constructed directly, which is exactly
    the surface `load_truth` produces -- the loader itself is covered by tests/test_truth.py.
    """
    from eval.loaders.truth import TruthTrack

    n = int(seconds * 10) + 1
    t = np.arange(n, dtype=float) * 0.1
    deg_per_m = 1.0 / 111_320.0  # nominal; only sets the scale, every assertion is a relationship
    lat = 51.5 + mps * t * deg_per_m
    lon = np.full(n, -1.25)
    return TruthTrack(name=name, t_s=t, lat=lat, lon=lon, source="synthetic (tests)")


def test_a_perfect_estimate_scores_zero_on_every_metric():
    """The plumbing check: epoch alignment, displacement convention, yaw derivation and the
    distance denominator all have to agree before any baseline's number means anything. Handing
    `score` the truth's own displacements must give exactly zero, not nearly zero."""
    from eval.baselines import score
    from eval.outages.inject import Outage

    truth = _straight_north_truth()
    outage = Outage("SYNTH", start_idx=300, end_idx=900, length_s=60)
    times = epoch_times(30.0, 60)
    true_disp = truth.displacements_ned(times)
    perfect = BaselineTrajectory(true_disp, course_over_ground(true_disp))

    m = score(perfect, truth, outage)
    assert m.n_epochs == 60
    assert m.duration_s == 60.0
    assert m.cte_m == pytest.approx(0.0, abs=1e-9)
    assert m.crse_m == pytest.approx(0.0, abs=1e-9)
    assert m.drift_pct == pytest.approx(0.0, abs=1e-9)
    assert m.yaw_rmse_rad == pytest.approx(0.0, abs=1e-12)
    assert m.distance_m == pytest.approx(900.0, rel=1e-3)  # 15 m/s for 60 s


def test_drift_percent_composes_as_final_error_over_truth_distance():
    """A known constant shortfall per epoch, hand-composed: `n` epochs each short by `d` metres
    give a final error of `n * d`, and drift-% is that over the truth path length.

    The geodesy underneath is not re-tested here -- `idr/geo.py` is checked against the canonical
    Vincenty reference in tests/test_geo.py -- so `distance_m` is taken from the truth track and
    the assertion is about `score`'s composition.
    """
    from eval.baselines import score
    from eval.outages.inject import Outage

    truth = _straight_north_truth()
    outage = Outage("SYNTH", start_idx=300, end_idx=900, length_s=60)
    times = epoch_times(30.0, 60)
    true_disp = truth.displacements_ned(times)

    shortfall = 0.25  # m per epoch, north
    est = true_disp - np.array([shortfall, 0.0])
    m = score(BaselineTrajectory(est, course_over_ground(est)), truth, outage)

    length = truth.distance_m(times[0], times[-1])
    assert m.cte_m == pytest.approx(-60 * shortfall)  # signed: we fell short
    assert m.crse_m == pytest.approx(60 * shortfall)  # sum of absolutes
    assert m.drift_pct == pytest.approx(100.0 * 60 * shortfall / length)


def test_the_naive_strapdown_bias_error_shows_up_as_drift_percent():
    """The 10 mg case again, this time all the way through to the graded number.

    Truth covers 900 m in 60 s; a 10 mg accelerometer bias adds 176.5 m of error, so drift is
    176.5 / 900 = **19.6%** -- comfortably over the 10% PS 26168 grades, which is the entire point
    of carrying this baseline in every figure.
    """
    from eval.baselines import score
    from eval.outages.inject import Outage

    truth = _straight_north_truth()
    outage = Outage("SYNTH", start_idx=300, end_idx=900, length_s=60)
    times = epoch_times(30.0, 60)
    true_disp = truth.displacements_ned(times)

    bias = 0.010 * G
    gyro, accel = _level_imu(600, accel_bias=(bias, 0.0, 0.0))
    traj = naive_strapdown(
        gyro, accel, DT,
        initial_rotation=np.eye(3),
        initial_velocity_ned=np.array([float(true_disp[0, 0]), 0.0, 0.0]),
        epoch_stride=STRIDE,
    )
    m = score(traj, truth, outage)
    assert m.drift_pct == pytest.approx(100.0 * 176.5 / 900.0, rel=2e-2)
    assert m.drift_pct > 10.0


def test_initial_state_from_truth_reads_heading_and_speed_off_the_first_epoch():
    from eval.baselines import initial_state_from_truth

    truth = _straight_north_truth()
    rot, v0 = initial_state_from_truth(truth, 30.0)
    assert float(np.arctan2(rot[1, 0], rot[0, 0])) == pytest.approx(0.0, abs=1e-9)
    assert v0 == pytest.approx([15.0, 0.0, 0.0], rel=1e-3)


def test_the_gnss_available_baseline_scores_its_own_hold_error():
    """The Gate 1 denominator, end to end.

    Fixes every 9 s at the measured `S-` cadence, sitting exactly on truth. Hand-reasoned: the
    metrics compare *displacements*, so what survives is the difference in staleness between the
    two window boundaries. The window opens at t = 30 s holding the fix from t = 27 s -- 3 s, or
    45 m, stale -- and closes at t = 90 s exactly on a fix, so the net error is that opening 45 m
    and drift is 45 / 900 = **5.0%**.

    Note what that says: with GNSS *available* throughout, a phone-only system is still 5% out
    over 60 s, purely because the receiver speaks every 9 s. That is the honest Gate 1 denominator,
    and it is a property of the update rate rather than of the receiver's accuracy -- which is
    also why it is phase-sensitive: shift the window by 6 s and the two stalenesses swap.

    CTE and CRSE here are dominated by the staircase, not by receiver accuracy, which is why
    `gnss_available` says so at length and why the write-up must not quote them beside the
    filter's without that sentence.
    """
    from eval.baselines import gnss_available, score
    from eval.outages.inject import Outage

    truth = _straight_north_truth()
    outage = Outage("SYNTH", start_idx=300, end_idx=900, length_s=60)
    times = epoch_times(30.0, 60)

    t_fix = np.arange(0.0, 100.0, 9.0)
    fix_ned = truth.ned_at(t_fix)
    # Into the window's own local frame: `score` compares displacements, so only the steps matter.
    traj = gnss_available(t_fix, fix_ned, times)

    m = score(traj, truth, outage)
    assert m.drift_pct == pytest.approx(100.0 * 45.0 / 900.0, rel=2e-2)
    assert m.n_epochs == 60
