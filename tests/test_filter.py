"""Tests for the implemented parts of the reference filter: detectors and gating.

Propagation and the update family are Sprint 1. The gating conditions are tested now because they
are where a plausible-looking filter goes quietly wrong -- an ungated NHC through a slip produces
smooth, confident, incorrect output that no position plot reveals until it is compared to truth.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.reference.inekf import (
    ERROR_STATE_DIM,
    IDX_ATTITUDE,
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


def test_one_rotating_sample_in_the_window_stops_the_detector_firing():
    """D-057, and the whole of the NEES failure that blocked Gate 1.

    The window straddling a pull-away is the dangerous case: the car is already yawing, but four
    of the five samples were taken while it was stopped, and a *mean* gyro statistic divides the
    one real sample by five. Hand-computed for this window: mean is
    `(4 x 0 + 0.05) / 5 = 0.010` rad/s, **under** the 0.02 threshold, so the mean statistic fires
    ZUPT and ZARU at 0.05 rad/s of genuine rotation. The maximum is 0.05, which does not.

    That single firing lands where the stop has just driven `P` on the gyro-bias block to its
    minimum, so the gain is tiny and the error it injects is not: a measured systematic
    8.0e-4 rad/s in `b_g_z`, 2.6 sigma of that block's own spread.
    """
    accel = np.tile([0.0, 0.0, 9.80665], (5, 1))
    gyro = np.zeros((5, 3))
    gyro[-1, 2] = 0.05  # the car has begun to turn; the rest of the window has not noticed

    assert float(np.mean(np.linalg.norm(gyro, axis=1))) < CFG.zupt_gyro_norm_thresh, (
        "the window this test is built on must be one the mean statistic accepts, "
        "or it is not testing the regression it claims to"
    )
    assert not is_stationary(accel, gyro, CFG)


def test_a_still_window_still_fires_under_the_maximum_statistic():
    """The other direction of D-057: strictness must not cost the stops we need.

    ZARU at every stop is what the yaw budget rests on (docs/ERROR_BUDGET.md section 3.2), so a
    detector that stops firing is worse than the false firing it fixed. This window carries one
    sample of the measured gyro white noise per axis -- `cfg.zaru_sigma`, 1.3e-3 rad/s -- at 4
    sigma, and its maximum is still an order of magnitude inside the threshold.
    """
    accel = np.tile([0.0, 0.0, 9.80665], (10, 1)) + RNG.normal(0, 0.01, (10, 3))
    gyro = np.full((10, 3), 4.0 * CFG.zaru_sigma)
    assert float(np.max(np.linalg.norm(gyro, axis=1))) < CFG.zupt_gyro_norm_thresh / 2
    assert is_stationary(accel, gyro, CFG)


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
# P0, per block (R-3, D-055)
#
# Every value below is computed here from the source it came from, not read back out of the
# implementation -- a test that asserts `P0 == initial_covariance(cfg)` would pass for any
# number at all, which is exactly how a flat 1e-3 survived three sprints.
# ------------------------------------------------------------------------------------------


def test_p0_is_not_flat():
    """The R-3 regression, stated as the thing that was wrong rather than as the fix.

    A flat prior is wrong in both directions at once, and the two ratios below are why: the mount
    angle starts *unknown* while roll and pitch are levelled off gravity, and a position seeded
    from a GNSS fix is metres uncertain while the velocity at a standstill is centimetres.
    """
    sd = np.sqrt(np.diag(InEKF().P))
    assert len(set(np.round(sd, 12))) > 1, "P0 is flat again"
    assert sd[IDX_MOUNT][0] > 30 * sd[IDX_ATTITUDE][0], "the mount block must start far looser"
    assert sd[8] > 100 * sd[5], "position starts at a fix; velocity starts at a standstill"


def test_p0_blocks_are_the_values_their_sources_give():
    """Each block against its own source, computed here.

    Sources, in order: one-sample gravity levelling off the measured accelerometer noise;
    ERROR_BUDGET section 5 (D-055, a judgement call); the ZUPT assertion the filter aligns on;
    EVALUATION.md section 2; and the two bias instabilities D-045 measured.
    """
    cfg = FilterConfig()
    sd = np.sqrt(np.diag(initial_covariance(cfg)))

    levelling = cfg.accel_vrw * np.sqrt(cfg.imu_rate_hz) / 9.80665
    assert sd[0] == pytest.approx(levelling) and sd[1] == pytest.approx(levelling)
    assert sd[2] == pytest.approx(np.deg2rad(5.0), rel=1e-3), "initial yaw: 5 deg, section 5"
    assert np.allclose(sd[IDX_VELOCITY], cfg.zupt_sigma)
    assert np.allclose(sd[6:9], 3.0), "position: the protocol's stated GNSS accuracy"
    # 42 deg/hr and 0.34 mg, converted here rather than trusted from the config comment.
    assert np.allclose(sd[9:12], 42.0 * np.pi / 180.0 / 3600.0, rtol=2e-3)
    assert np.allclose(sd[12:15], 0.34e-3 * 9.80665, rtol=5e-3)
    assert np.allclose(sd[IDX_MOUNT], np.deg2rad(5.0), rtol=1e-3)


def test_p0_position_block_takes_the_initialising_fixs_own_accuracy():
    """The default is the protocol's figure for a *reference-grade* receiver, and the phone's own
    fix is worse. A harness that has `gps_accuracy_m` must pass it, and it must be used."""
    p0 = initial_covariance(FilterConfig(), gnss_sigma_m=12.0)
    assert np.allclose(np.sqrt(np.diag(p0))[IDX_POSITION], 12.0)
    assert np.allclose(np.sqrt(np.diag(p0))[IDX_VELOCITY], FilterConfig().zupt_sigma), (
        "only the position block follows the fix"
    )


def test_p0_refuses_a_zero_sigma():
    """A zero block is not confidence, it is a state that no measurement can ever correct."""
    with pytest.raises(ValueError, match="positive"):
        initial_covariance(FilterConfig(), gnss_sigma_m=0.0)


def test_an_explicit_p0_is_used_and_shape_checked():
    p0 = np.eye(ERROR_STATE_DIM) * 7.0
    assert np.array_equal(InEKF(p0=p0).P, p0)
    with pytest.raises(ValueError, match="18x18"):
        InEKF(p0=np.eye(6))


def test_zaru_sigma_is_the_measured_gyro_white_noise_at_the_imu_rate():
    """D-056. Not a tuning knob: it is `ARW / sqrt(dt)`, and both terms are measured.

    The rate scaling is the half that matters beyond screening -- the same config on the 200 Hz
    FOG build must give a 4.47x larger sigma, not the 10 Hz constant it would have had if this
    were typed in.
    """
    cfg = FilterConfig()
    assert cfg.zaru_sigma == pytest.approx(4.11e-4 * np.sqrt(10.0))
    assert cfg.zaru_sigma == pytest.approx(1.2997e-3, abs=1e-6)
    fog = FilterConfig(imu_rate_hz=200.0)
    assert fog.zaru_sigma == pytest.approx(cfg.zaru_sigma * np.sqrt(20.0))


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
