"""Tests for the implemented parts of the reference filter: detectors and gating.

Propagation and the update family are Sprint 1. The gating conditions are tested now because they
are where a plausible-looking filter goes quietly wrong -- an ungated NHC through a slip produces
smooth, confident, incorrect output that no position plot reveals until it is compared to truth.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from core.reference.inekf import (
    ERROR_STATE_DIM,
    IDX_ACCEL_BIAS,
    IDX_ATTITUDE,
    IDX_GYRO_BIAS,
    IDX_MOUNT,
    IDX_POSITION,
    IDX_VELOCITY,
    FilterConfig,
    InEKF,
    NavState,
    chi2_gate,
    detect_mount_disturbance,
    initial_covariance,
    is_stationary,
    nhc_is_valid,
)

CFG = FilterConfig()
RNG = np.random.default_rng(0)


# ------------------------------------------------------------------------------------------
# State layout
# ------------------------------------------------------------------------------------------


def test_error_state_slices_tile_the_vector_without_gaps_or_overlap():
    """A mis-indexed error state corrupts the wrong block of the covariance, which shows up as a
    filter that 'almost works' -- the hardest failure mode to diagnose."""
    covered = np.zeros(ERROR_STATE_DIM, dtype=int)
    for sl in (IDX_ATTITUDE, slice(3, 6), slice(6, 9), slice(9, 12), slice(12, 15), IDX_MOUNT):
        covered[sl] += 1
    assert (covered == 1).all()


def test_yaw_is_read_from_the_rotation_matrix():
    s = NavState()
    assert s.yaw == pytest.approx(0.0)
    theta = 0.4
    s.R = np.array(
        [[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]]
    )
    assert s.yaw == pytest.approx(theta)


# ------------------------------------------------------------------------------------------
# Stationary detection
# ------------------------------------------------------------------------------------------


def test_stationary_phone_is_detected():
    """Gravity dominates accelerometer *magnitude* even at rest, which is why the test is on
    variance. A magnitude threshold would never fire."""
    accel = np.tile([0.0, 0.0, 9.80665], (10, 1)) + RNG.normal(0, 0.01, (10, 3))
    gyro = RNG.normal(0, 0.001, (10, 3))
    assert is_stationary(accel, gyro, CFG)


def test_driving_is_not_stationary():
    accel = np.tile([0.0, 0.0, 9.80665], (10, 1)) + RNG.normal(0, 1.5, (10, 3))
    gyro = RNG.normal(0, 0.3, (10, 3))
    assert not is_stationary(accel, gyro, CFG)


def test_turning_at_constant_speed_is_not_stationary():
    """Smooth cornering has low accel variance but high gyro -- the case a variance-only detector
    would misclassify as a stop, injecting a false ZUPT mid-turn."""
    accel = np.tile([0.0, 0.0, 9.80665], (10, 1)) + RNG.normal(0, 0.01, (10, 3))
    gyro = np.tile([0.0, 0.0, 0.5], (10, 1))
    assert not is_stationary(accel, gyro, CFG)


def test_stationary_rejects_malformed_windows():
    with pytest.raises(ValueError, match=r"\(n, 3\)"):
        is_stationary(np.zeros((10,)), np.zeros((10, 3)), CFG)


# ------------------------------------------------------------------------------------------
# NHC gating
# ------------------------------------------------------------------------------------------


def test_nhc_applies_on_a_straight_at_speed():
    assert nhc_is_valid(speed_mps=16.7, yaw_rate=0.01, lateral_accel=0.1, cfg=CFG)


@pytest.mark.parametrize(
    ("speed", "yaw_rate", "lat_accel", "why"),
    [
        (0.2, 0.0, 0.0, "stopped: no direction of travel to be lateral to"),
        (16.7, 1.2, 0.0, "hard cornering"),
        (16.7, 0.0, 6.0, "approaching slip"),
    ],
)
def test_nhc_is_gated_off_when_the_assumption_breaks(speed, yaw_rate, lat_accel, why):
    assert not nhc_is_valid(speed, yaw_rate, lat_accel, CFG), why


# ------------------------------------------------------------------------------------------
# chi-squared gate -- the mechanism that makes GNSS optional rather than a mode switch
# ------------------------------------------------------------------------------------------


def test_consistent_fix_is_accepted():
    assert chi2_gate(np.array([0.5, 0.3, 0.1]), np.eye(3) * 4.0, CFG.chi2_gate_3dof)


def test_multipath_outlier_is_rejected():
    """A 50 m jump on tunnel exit, against a 2 m-sigma covariance."""
    assert not chi2_gate(np.array([50.0, 10.0, 2.0]), np.eye(3) * 4.0, CFG.chi2_gate_3dof)


def test_singular_covariance_rejects_rather_than_crashes():
    assert not chi2_gate(np.array([1.0, 1.0, 1.0]), np.zeros((3, 3)), CFG.chi2_gate_3dof)


def test_inflated_covariance_admits_a_larger_correction():
    """After a long outage the filter is genuinely uncertain, so a big correction is consistent --
    this is what makes re-acquisition smooth instead of a snap."""
    innovation = np.array([20.0, 0.0, 0.0])
    assert not chi2_gate(innovation, np.eye(3) * 4.0, CFG.chi2_gate_3dof)
    assert chi2_gate(innovation, np.eye(3) * 400.0, CFG.chi2_gate_3dof)


# ------------------------------------------------------------------------------------------
# Mount disturbance
# ------------------------------------------------------------------------------------------


def test_bump_is_detected():
    gyro = RNG.normal(0, 0.01, (20, 3))
    gyro[10] += 8.0  # phone knocked
    assert detect_mount_disturbance(gyro, CFG)


def test_normal_driving_is_not_a_bump():
    gyro = np.column_stack([np.zeros(20), np.zeros(20), np.linspace(0, 0.4, 20)])
    assert not detect_mount_disturbance(gyro, CFG)


# ------------------------------------------------------------------------------------------
# Unimplemented surface, and the gating property that makes GNSS optional
# ------------------------------------------------------------------------------------------


def test_filter_initialises_with_a_well_formed_covariance():
    f = InEKF()
    assert f.P.shape == (ERROR_STATE_DIM, ERROR_STATE_DIM)
    assert np.allclose(f.P, f.P.T), "covariance must be symmetric"
    assert (np.linalg.eigvalsh(f.P) > 0).all(), "covariance must be positive definite"


# ------------------------------------------------------------------------------------------
# P0, per block (D-055). Every case below is hand-computed from the document section named in
# its docstring -- never from `initial_covariance`'s own output, which would only assert that
# the function is the function.
# ------------------------------------------------------------------------------------------


def _sd(block: slice) -> np.ndarray:
    return np.sqrt(np.diag(initial_covariance()))[block]


def test_p0_is_what_the_constructor_installs():
    """The two must not drift apart: a `P0` nobody uses is documentation, not a prior."""
    assert np.array_equal(InEKF().P, initial_covariance())
    assert np.array_equal(InEKF(CFG).P, initial_covariance(CFG))


def test_p0_position_is_the_gnss_fix_it_starts_from():
    """docs/EVALUATION.md section 2: GNSS reference accuracy +/- 3 m. The filter is initialised
    at a fix, so the position prior is the fix's own accuracy.

    The flat `1e-3 * I` this replaces was sigma = 3.16 cm -- 95x too tight, not too loose as the
    plan's R-3 row says. Too tight is the dangerous direction: it makes the chi-squared gate
    reject good fixes, and that reads as a sensor fault rather than as tuning.
    """
    assert _sd(IDX_POSITION) == pytest.approx(3.0)
    assert np.sqrt(1e-3) == pytest.approx(0.0316, abs=1e-4)  # what it used to be


def test_p0_velocity_is_two_gnss_fixes_differenced():
    """sqrt(2) * 3 m / 1 s = 4.243 m/s. Velocity at initialisation comes from differencing two
    fixes, so its noise is the position noise of both over one epoch."""
    assert _sd(IDX_VELOCITY) == pytest.approx(np.sqrt(2.0) * 3.0 / 1.0)
    assert _sd(IDX_VELOCITY)[0] == pytest.approx(4.2426, abs=1e-4)


def test_p0_roll_and_pitch_are_bounded_by_what_the_stop_detector_admits():
    """sqrt(0.05) / 9.80665 = 0.0228 rad = 1.31 deg.

    Levelling from gravity is only as good as the residual specific force at the epoch it is done,
    and `zupt_accel_var_thresh` is exactly how much of that the stop detector still admits. The
    *sensor* floor is 60x tighter -- 0.34 mg of accel bias instability is 0.019 deg -- and using
    the floor would assert an alignment accuracy the detector does not guarantee.
    """
    expected = np.sqrt(CFG.zupt_accel_var_thresh) / 9.80665
    assert _sd(slice(0, 2)) == pytest.approx(expected)
    assert np.rad2deg(expected) == pytest.approx(1.306, abs=1e-3)
    assert np.rad2deg(0.34e-3 * 9.80665 / 9.80665) == pytest.approx(0.0195, abs=1e-3)


def test_p0_yaw_is_gnss_course_over_ground_at_the_reference_speed():
    """(sqrt(2) * 3 m / 1 s) / 16.7 m/s = 0.254 rad = 14.6 deg.

    Course over ground needs motion, so yaw is *not* observable at the stationary epoch that fixes
    roll and pitch -- the prior stands until the vehicle moves. Wide, and honestly so: a
    right-invariant filter driven by body-frame constraints has an exactly zero attitude column
    (D-028), so nothing but GNSS or map feedback will narrow it.
    """
    expected = (np.sqrt(2.0) * 3.0 / 1.0) / 16.7
    assert _sd(IDX_ATTITUDE)[2] == pytest.approx(expected)
    assert np.rad2deg(expected) == pytest.approx(14.556, abs=1e-3)


def test_p0_bias_blocks_are_the_allan_runs_measured_bias_instabilities():
    """docs/ERROR_BUDGET.md section 9.1 (D-045): gyro 42 deg/hr, accel 0.34 mg. Measured on
    IO-VNBD's own stationary segments, on the phones that produced the graded data."""
    assert _sd(IDX_GYRO_BIAS) == pytest.approx(42.0 * (np.pi / 180.0) / 3600.0)
    assert _sd(IDX_GYRO_BIAS)[0] == pytest.approx(2.0362e-4, abs=1e-8)
    assert _sd(IDX_ACCEL_BIAS) == pytest.approx(0.34e-3 * 9.80665)
    assert _sd(IDX_ACCEL_BIAS)[0] == pytest.approx(3.3343e-3, abs=1e-7)


def test_p0_mount_block_is_the_knock_not_the_requirement():
    """5 deg, from docs/ERROR_BUDGET.md section 5's knock -- **not** section 5's ~1.15 deg
    requirement.

    Nothing has estimated `R_sv`: the PCA initialiser is P-11 and `mount_rw` is zero (D-048), so
    the block starts from no measurement and cannot re-inflate. A prior at the requirement would
    have the filter open by asserting that the budget is already met, and would let the gate
    reject the NHC updates that would correct a real misalignment. The flat prior it replaces was
    1.81 deg, which is 2.8x tighter and sits *below* even the 1.15 deg requirement's own margin.
    """
    assert _sd(IDX_MOUNT) == pytest.approx(np.deg2rad(5.0))
    assert np.rad2deg(_sd(IDX_MOUNT)[2]) == pytest.approx(5.0)
    assert np.rad2deg(np.sqrt(1e-3)) == pytest.approx(1.812, abs=1e-3)  # what it used to be


def test_p0_is_diagonal_because_a_prior_has_learned_no_correlations_yet():
    p0 = initial_covariance()
    assert np.array_equal(p0, np.diag(np.diag(p0)))


def test_p0_tracks_a_supplied_gnss_accuracy():
    """The harness passes the `S-` stream's own per-sample `gps_accuracy_m` where it has one, so
    the three blocks derived from it must move with it rather than being frozen at 3 m."""
    cfg = dataclasses.replace(CFG, gnss_sigma_m=12.0)
    sd = np.sqrt(np.diag(initial_covariance(cfg)))
    assert sd[IDX_POSITION] == pytest.approx(12.0)
    assert sd[IDX_VELOCITY] == pytest.approx(np.sqrt(2.0) * 12.0)
    assert sd[2] == pytest.approx(np.sqrt(2.0) * 12.0 / 16.7)
    assert sd[0:2] == pytest.approx(np.sqrt(CFG.zupt_accel_var_thresh) / 9.80665)  # unaffected


# ------------------------------------------------------------------------------------------
# ZARU's chi-squared gate (D-057)
# ------------------------------------------------------------------------------------------


def test_zaru_at_a_genuine_stop_is_applied():
    f = InEKF()
    b_before = f.state.b_g.copy()
    assert f.update_zaru(np.array([2.0e-4, -1.0e-4, 3.0e-4])) is True
    assert not np.array_equal(b_before, f.state.b_g)


def test_zaru_at_a_false_stop_is_rejected_and_changes_nothing():
    """The measured failure D-053 recorded and P-04 diagnosed: `is_stationary` averages over
    0.5 s, so at the step the vehicle pulls away the window still holds four stopped samples and
    one moving one and the detector still says "stopped". The true yaw rate there was 0.05 rad/s
    and the innovation carried a chi-squared distance of 1456 against the 11.345 threshold.
    """
    f = InEKF()
    state_before = (f.state.b_g.copy(), f.state.R.copy(), f.state.v.copy())
    p_before = f.P.copy()

    assert f.update_zaru(np.array([0.0, 0.0, 0.05])) is False

    for before, after in zip(
        state_before, (f.state.b_g, f.state.R, f.state.v), strict=True
    ):
        assert np.array_equal(before, after), "a rejected ZARU must not move the state"
    assert np.array_equal(p_before, f.P), "a rejected ZARU must not move the covariance"


def test_zaru_sigma_is_derived_from_the_allan_run_not_typed():
    """`zaru_sigma` is the gyro white noise per sample, so it is `gyro_arw * sqrt(rate)` and not a
    free parameter. Derived in `FilterConfig` so the two cannot drift apart (D-056)."""
    assert CFG.zaru_sigma == pytest.approx(CFG.gyro_arw * np.sqrt(CFG.imu_rate_hz), rel=1e-12)
    assert CFG.zaru_sigma == pytest.approx(1.2997e-3, abs=1e-6)


def test_zupt_is_deliberately_not_gated():
    """The asymmetry is measured, not assumed (D-057): gating ZUPT takes its NEES from 18.93 to
    44.74, because `zupt_sigma` = 0.02 m/s collapses the velocity block until legitimate
    innovations fall outside the gate and lock out permanently. Physically, at the first moving
    sample the *speed* is necessarily near zero so a false ZUPT is nearly harmless, while the
    *yaw rate* is not bounded at all.

    Asserted as behaviour rather than left as a comment: a ZUPT whose innovation is far outside
    its own covariance is still applied.
    """
    f = InEKF()
    f.state.v = np.array([15.0, 0.0, 0.0])  # 15 m/s against a 0.02 m/s sigma
    v_before = f.state.v.copy()
    assert f.update_zupt() is None, "update_zupt does not gate, so it returns nothing"
    assert not np.array_equal(v_before, f.state.v)


@pytest.mark.parametrize(("method", "sprint"), [("update_speed", "Sprint 2")])
def test_unimplemented_surface_fails_loudly_rather_than_silently(method, sprint):
    """Placeholders raise. A stub that returns None would let the harness produce plausible
    all-zero trajectories and report them as results.

    `propagate` left this list when P-02 implemented it, and `update_gnss`, `update_nhc` and
    `update_zupt` left it in P-03. That is this case's job: it is a tripwire that fires the moment
    a placeholder becomes real, and each entry leaves the same way -- by being implemented, with
    its own behavioural tests replacing this one. `update_speed` is the last one standing; it is
    seat M's speed head fused in P-09, and until then it must raise rather than return None.

    The behaviour this used to guard for the update family is now guarded properly, by SE_2(3)
    tests 7-11 in tests/test_se23_derivation.py.
    """
    f = InEKF()
    args = {"update_speed": (10.0, 0.5)}[method]
    with pytest.raises(NotImplementedError, match=sprint):
        getattr(f, method)(*args)


def test_a_rejected_gnss_fix_changes_absolutely_nothing():
    """The architectural claim, asserted rather than described.

    There is no tunnel mode and no re-initialisation on re-acquisition; a fix that fails the gate
    simply is not applied. If a future edit adds a "fall back to a weaker correction" branch, the
    state or the covariance moves here and this fails. Kept in this file rather than with tests
    7-11 because it is a property of the *gating*, which is what this file tests.
    """
    f = InEKF()
    f.state.p = np.array([10.0, -4.0, 1.0])
    for _ in range(20):
        f.propagate(np.array([0.0, 0.0, 0.2]), np.array([0.3, -0.1, -9.7]), 0.1)
    state_before = (f.state.R.copy(), f.state.v.copy(), f.state.p.copy(), f.state.b_g.copy())
    p_before = f.P.copy()

    accepted = f.update_gnss(f.state.p + np.array([500.0, 0.0, 0.0]), np.eye(3) * 4.0)

    assert accepted is False
    for before, after in zip(
        state_before, (f.state.R, f.state.v, f.state.p, f.state.b_g), strict=True
    ):
        assert np.array_equal(before, after), "a rejected fix must not move the state at all"
    assert np.array_equal(p_before, f.P), "a rejected fix must not move the covariance either"
