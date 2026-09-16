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
    ACCEL_BIAS_INSTABILITY_MEASURED,
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
    right_invariant_from_plain,
    skew,
    zaru_sigma_from_window,
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
    with pytest.raises(ValueError, match=r"\(n, 3\)"):
        is_stationary(np.zeros((10, 3)), np.zeros((10,)), CFG)
    with pytest.raises(ValueError, match=r"3-vector"):
        is_stationary(np.zeros((10, 3)), np.zeros((10, 3)), CFG, gyro_bias=np.zeros(4))


def test_still_window_with_constant_offset_requires_bias_compensation():
    """A still phone with a 1.5 deg/s gyro offset (such as S3a's standstill level) fails the raw
    gyro norm threshold (0.01 rad/s = 0.573 deg/s) and is detected as stationary only when
    `gyro_bias` carries the offset."""
    accel = np.tile([0.0, 0.0, 9.80665], (20, 1)) + RNG.normal(0, 0.01, (20, 3))
    offset = np.deg2rad([1.5, 0.0, 0.0])  # 1.5 deg/s == 0.0262 rad/s > 0.01 rad/s
    gyro = np.tile(offset, (20, 1)) + RNG.normal(0, 0.001, (20, 3))

    # Without bias compensation (default None / zeros), raw mean exceeds threshold
    assert not is_stationary(accel, gyro, CFG)

    # With gyro_bias passed, bias-corrected mean is inside threshold
    assert is_stationary(accel, gyro, CFG, gyro_bias=offset)


def test_zupt_thresholds_pinned_to_measured_values():
    """Conservative stop thresholds measured against truth speed (D-115, Fix 1)."""
    assert CFG.zupt_accel_var_thresh == 0.02  # (m/s^2)^2, 12x below rolling p10 on S3a
    assert CFG.zupt_gyro_norm_thresh == 0.01  # rad/s (~0.57 deg/s), admits stops after bias
    assert CFG.zupt_window_s == 2.0  # seconds, eliminates high-speed false stops




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
    """sqrt(0.02) / 9.80665 = 0.0144 rad = 0.83 deg (1.31 deg at the pre-D-115 threshold of 0.05).

    Levelling from gravity is only as good as the residual specific force at the epoch it is done,
    and `zupt_accel_var_thresh` is exactly how much of that the stop detector still admits. The
    *sensor* floor is 57x tighter -- 0.25 mg of accel bias instability is 0.015 deg -- and using
    the floor would assert an alignment accuracy the detector does not guarantee.
    """
    expected = np.sqrt(CFG.zupt_accel_var_thresh) / 9.80665
    assert _sd(slice(0, 2)) == pytest.approx(expected)
    assert np.rad2deg(expected) == pytest.approx(0.826, abs=1e-3)
    assert np.rad2deg(ACCEL_BIAS_INSTABILITY_MEASURED / 9.80665) == pytest.approx(0.0145, abs=1e-3)


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


def test_p0_gyro_bias_block_is_the_measured_turn_on_bias_not_the_instability():
    """D-115 supersedes the D-045 entry here. `P0` carries the uncertainty of a bias nothing has
    estimated yet, which is the *turn-on* bias -- measured at 0.14 deg/s RMS, 0.20 deg/s worst
    axis, over 638 s of standstill on the TRAIN stems -- and not the bias *instability* (22
    deg/hr = 0.006 deg/s since D-120; D-045 read 42), which is how far an already-estimated bias
    wanders. With 42 deg/hr in the block a real 0.1 deg/s bias was a nine-sigma event and every
    ZARU on every held-out stem was rejected at its gate: 0 of 103 on Vta1a."""
    assert _sd(IDX_GYRO_BIAS) == pytest.approx(CFG.gyro_bias_turn_on)
    assert np.rad2deg(_sd(IDX_GYRO_BIAS)[0]) == pytest.approx(0.2)
    assert CFG.gyro_bias_turn_on > 22.0 * (np.pi / 180.0) / 3600.0


def test_p0_accel_bias_block_is_the_measured_turn_on_bias_not_the_instability():
    """`P0` carries the uncertainty of a bias nothing has estimated yet, which is the *turn-on*
    bias -- measured at 6.2 mg RMS across runs, 8.2 mg largest single run, over the 638 s of
    TRAIN standstill -- and not the bias *instability* (0.25 mg = 2.45 mm/s^2 since D-120; D-045
    read 0.34 mg), which is how far an already-estimated bias wanders. Measured as mean(|f|) - g,
    the one component independent of levelling."""
    assert _sd(IDX_ACCEL_BIAS) == pytest.approx(CFG.accel_bias_turn_on)
    assert _sd(IDX_ACCEL_BIAS)[0] == pytest.approx(0.08)
    assert CFG.accel_bias_turn_on > ACCEL_BIAS_INSTABILITY_MEASURED


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
    free parameter. Derived in `FilterConfig` so the two cannot drift apart (D-056). Since D-131
    it is the *floor* under the stop's own level (`zaru_sigma_from_window`), and what
    `update_zaru` uses when no sigma is passed; the identity and the value are unchanged."""
    assert CFG.zaru_sigma == pytest.approx(CFG.gyro_arw * np.sqrt(CFG.imu_rate_hz), rel=1e-12)
    assert CFG.zaru_sigma == pytest.approx(6.894e-4, abs=1e-6)


def test_zaru_sigma_from_window_is_the_stops_own_noise_floored_at_the_allan_figure():
    """D-131. At a standstill the detector's window is bias plus white noise, so its per-axis
    sample std is the noise ZARU's innovation carries. Measured on TRAIN S1 at the 3,066
    detector-positive standstill samples: innovation std [0.72, 0.38, 0.60] deg/s per axis, the
    window estimate [0.70, 0.35, 0.59]. The Allan desk figure is the floor, so a quantised gyro
    that repeats a value at rest reports the sensor's noise rather than zero."""
    rng = np.random.default_rng(11)
    sigma = np.deg2rad([0.7, 0.35, 0.6])
    bias = np.deg2rad([0.05, -0.06, 0.16])
    window = bias + rng.normal(0.0, 1.0, (4000, 3)) * sigma
    assert zaru_sigma_from_window(window, CFG) == pytest.approx(sigma, rel=0.05)
    assert zaru_sigma_from_window(window[:20], CFG) == pytest.approx(sigma, rel=0.5)
    still = np.tile(bias, (20, 1))
    assert zaru_sigma_from_window(still, CFG) == pytest.approx(np.full(3, CFG.zaru_sigma))
    for bad in (np.zeros((1, 3)), np.zeros((20, 2)), np.zeros(20)):
        with pytest.raises(ValueError, match="gyro window"):
            zaru_sigma_from_window(bad, CFG)


def test_zaru_against_the_stops_own_level_admits_the_idle_vibration_the_desk_figure_refused():
    """The counter D-131 fixes: S3a's aided pass offered 1,372 stops and the gate refused 1,356,
    because a ~1 deg/s idle-vibration sample was tested against R = (0.039 deg/s)^2 (D-130).
    The same sample against the window's own sigma is inside the gate. The sigma is floored at
    the desk figure, a scalar is accepted, and a malformed one is refused loudly.

    D-057's synthetic pull-away sample (0.05 rad/s of yaw at the first moving step) is still
    refused at TRAIN S1's level, 0.7 deg/s (chi-squared 15.5 against 11.345); at S3a's 1.4 deg/s
    it would pass (4.1). On the real stems no run-out sample reached 2.9 deg/s -- they measure
    0.2-2.7 deg/s and cost <= 0.008 deg/s of admitted mean on S1 -- so the gate is kept and the
    row records what it admits.
    """
    rng = np.random.default_rng(3)
    level = np.deg2rad([0.33, 1.3, 1.4])  # S3a's standstill level, a diagnostic figure
    window = rng.normal(0.0, 1.0, (20, 3)) * level
    idle = np.deg2rad([0.2, -1.1, 1.2])  # one idle sample, |z| = 1.6 deg/s
    assert InEKF().update_zaru(idle) is False, "the desk figure refuses idle vibration"
    f = InEKF()
    assert f.update_zaru(idle, sigma=zaru_sigma_from_window(window, CFG)) is True
    assert not np.array_equal(f.state.b_g, np.zeros(3)), "an applied ZARU moves b_g"
    assert InEKF().update_zaru(idle, sigma=np.deg2rad(1.4)) is True, "a scalar sigma is accepted"

    # the floor: a sigma below the desk figure is raised to it, so it changes nothing
    f_floor, f_default = InEKF(), InEKF()
    tiny = np.array([2.0e-4, -1.0e-4, 3.0e-4])
    assert f_floor.update_zaru(tiny, sigma=np.full(3, 1e-9)) is True
    assert f_default.update_zaru(tiny) is True
    assert np.array_equal(f_floor.state.b_g, f_default.state.b_g)
    assert np.array_equal(f_floor.P, f_default.P)

    pull_away = np.array([0.0, 0.0, 0.05])
    assert InEKF().update_zaru(pull_away, sigma=np.deg2rad(0.7)) is False
    assert InEKF().update_zaru(pull_away, sigma=np.deg2rad(1.4)) is True

    for bad in (np.zeros(2), np.array([np.nan, 1.0, 1.0]), np.zeros((3, 3)) + 1.0):
        with pytest.raises(ValueError, match="ZARU sigma"):
            InEKF().update_zaru(idle, sigma=bad)


def test_zaru_with_the_windows_own_sigma_is_consistent_on_a_vibrating_standstill():
    """The consistency argument for D-131, on the population it is for: a standstill whose gyro
    carries 1 / 0.4 / 0.7 deg/s of idle vibration per axis and a bias of 0.1-0.2 deg/s. ZARU at
    every step with `sigma` read from the trailing 2 s window, as `_step_constraints` does, must
    (a) accept at the gate's own rate rather than refuse 98.8 % as the desk figure did, (b) drive
    `b_g` to the truth, and (c) leave the bias block's covariance describing its own error:
    a 3-dof NEES near 3, with the per-axis error inside 3 sigma."""
    rng = np.random.default_rng(21)
    level = np.deg2rad([1.0, 0.4, 0.7])
    truth = np.deg2rad([0.15, -0.1, 0.2])
    n = 600
    gyro = truth + rng.normal(0.0, 1.0, (n, 3)) * level
    window = int(round(CFG.zupt_window_s * CFG.imu_rate_hz))
    f = InEKF()
    applied = refused = 0
    for k in range(window - 1, n):
        sigma = zaru_sigma_from_window(gyro[k - window + 1 : k + 1], CFG)
        if f.update_zaru(gyro[k], sigma=sigma):
            applied += 1
        else:
            refused += 1
    assert refused / (applied + refused) < 0.03, f"{refused} of {applied + refused} refused"
    err = f.state.b_g - truth
    sig = np.sqrt(np.diag(f.P)[IDX_GYRO_BIAS])
    assert np.all(np.abs(err) < 3.0 * sig), f"error {err} outside 3 sigma {sig}"
    nees = float(err @ np.linalg.solve(f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS], err))
    assert nees < 11.345, f"bias-block NEES {nees:.2f} is over-confident"
    assert np.all(sig < np.deg2rad(0.1)), f"b_g not pinned by 580 ZARUs: sigma {np.rad2deg(sig)}"


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


# ------------------------------------------------------------------------------------------
# D-115: the Doppler velocity update, the right-invariant prior, and the caller's override
# ------------------------------------------------------------------------------------------


def _aided_filter() -> InEKF:
    """A filter mid-drive: heading north-east at 12 m/s, 200 m from the origin, with its prior
    re-expressed in right-invariant coordinates as the harness does at alignment, then
    propagated for two seconds so the covariance has real cross terms rather than a prior's."""
    f = InEKF()
    f.state.v = np.array([12.0 * np.cos(0.7), 12.0 * np.sin(0.7), 0.0])
    f.state.p = np.array([150.0, -130.0, 2.0])
    f.P = right_invariant_from_plain(f.P, f.state.p, f.state.v)
    for _ in range(20):
        f.propagate(np.array([0.0, 0.0, 0.05]), np.array([0.2, 0.0, -9.75]), 0.1)
    return f


def test_gnss_velocity_update_pulls_the_velocity_onto_the_measurement():
    """`z = v_hat[:2] - v_gnss`, `H = [-v_hat^, I, 0...]` on the horizontal rows, with the same
    subtract-the-correction retraction as every other update (D-050). A 3 m/s speed error
    against a 0.5 m/s Doppler is corrected almost entirely -- the gain on the velocity block is
    close to one -- and the vertical velocity, which the update does not observe, is left with
    whatever the propagation gave it."""
    f = _aided_filter()
    true_v = f.state.v.copy()
    f.state.v = true_v + np.array([2.5, -1.7, 0.0])
    v_before = f.state.v.copy()
    accepted = f.update_gnss_velocity(true_v[:2], np.eye(2) * 0.25)
    assert accepted is True
    err_before = np.linalg.norm(v_before[:2] - true_v[:2])
    err_after = np.linalg.norm(f.state.v[:2] - true_v[:2])
    assert err_after < 0.1 * err_before, (err_before, err_after)


def test_gnss_velocity_update_is_ungated_by_default_and_gated_at_two_dof_on_request():
    """Ungated by default, for D-057's reason applied to the velocity: a refused Doppler fix is
    the first step of every runaway the aided pass has recorded (D-115). When the gate is
    switched on it is `chi2_gate_2dof`, not the 3-DOF one: a 2-vector innovation tested against
    the 3-DOF threshold would be 24% too permissive at 99%."""
    assert FilterConfig().gate_gnss_velocity is False
    f = _aided_filter()
    assert f.update_gnss_velocity(f.state.v[:2] + np.array([200.0, 0.0]), np.eye(2) * 0.25) is True

    f = _aided_filter()
    f.cfg = dataclasses.replace(f.cfg, gate_gnss_velocity=True)
    assert f.cfg.chi2_gate_2dof == pytest.approx(9.210)
    p_before = f.P.copy()
    v_before = f.state.v.copy()
    assert f.update_gnss_velocity(f.state.v[:2] + np.array([200.0, 0.0]), np.eye(2) * 0.25) is False
    assert np.array_equal(f.P, p_before)
    assert np.array_equal(f.state.v, v_before)
    with pytest.raises(ValueError):
        f.update_gnss_velocity(np.zeros(3), np.eye(2))
    with pytest.raises(ValueError):
        f.update_gnss_velocity(np.zeros(2), np.eye(3))


def test_the_caller_can_override_the_position_gate():
    """`gate=False` applies a fix the gate would refuse. The harness uses it after three
    consecutive rejections (`eval.run.GNSS_REJECTIONS_BEFORE_REANCHOR`), on the argument that
    three 1% events in a row are evidence against the covariance, not against the fixes.

    The fixture's prior is right-invariant-consistent, and that is not incidental: with the
    constructor's diagonal `P0` left as it is at 200 m from the origin, the same forced fix
    *rotates* the state by 80 degrees about the origin instead of translating it, because a
    diagonal RI prior claims a 50 m position uncertainty is attributable to the 14.6 deg yaw
    block. That is the failure `right_invariant_from_plain` exists to prevent."""
    f = _aided_filter()
    target = f.state.p + np.array([500.0, 0.0, 0.0])
    yaw_before = f.state.yaw
    assert f.update_gnss(target, np.eye(3) * 4.0) is False
    assert f.update_gnss(target, np.eye(3) * 4.0, gate=False) is True
    assert np.linalg.norm(f.state.p - target) < 0.05 * 500.0
    assert abs(f.state.yaw - yaw_before) < np.deg2rad(5.0)


def test_right_invariant_prior_makes_the_position_innovation_covariance_the_plain_one():
    """A diagonal `P0` in right-invariant coordinates is not a diagonal plain prior. With
    `xi_p = dp + p^ dtheta`, the GNSS innovation `z = xi_p - p^ dtheta` has covariance
    `H P H^T`; re-expressed through `right_invariant_from_plain` that is exactly the plain
    position block, and the height-to-tilt correlation that a diagonal RI prior implies at
    500 m from the origin -- `|p| sigma_tilt`, 8.7 m at 1 deg -- is gone."""
    cfg = FilterConfig()
    plain = initial_covariance(cfg, yaw_sigma_rad=np.deg2rad(9.0), level_sigma_rad=np.deg2rad(1.0))
    p = np.array([300.0, -400.0, 5.0])
    v = np.array([10.0, 5.0, 0.0])
    ri = right_invariant_from_plain(plain, p, v)

    h = np.zeros((3, ERROR_STATE_DIM))
    h[:, IDX_ATTITUDE] = -skew(p)
    h[:, IDX_POSITION] = np.eye(3)
    assert np.allclose(h @ ri @ h.T, plain[IDX_POSITION, IDX_POSITION])

    hv = np.zeros((3, ERROR_STATE_DIM))
    hv[:, IDX_ATTITUDE] = -skew(v)
    hv[:, IDX_VELOCITY] = np.eye(3)
    assert np.allclose(hv @ ri @ hv.T, plain[IDX_VELOCITY, IDX_VELOCITY])

    # Left diagonal, the same innovation covariance carries |p|^2 sigma^2 of attitude leakage.
    assert h @ plain @ h.T[:, :] is not None
    leaked = np.diag(h @ plain @ h.T) - np.diag(plain[IDX_POSITION, IDX_POSITION])
    assert leaked.max() > (500.0 * np.deg2rad(1.0)) ** 2

    assert np.allclose(ri, ri.T)
    assert np.all(np.linalg.eigvalsh(ri) > 0)
    assert np.array_equal(plain, initial_covariance(
        cfg, yaw_sigma_rad=np.deg2rad(9.0), level_sigma_rad=np.deg2rad(1.0)
    )), "the input must not be modified"


def test_right_invariant_prior_is_the_identity_map_at_the_origin_at_rest():
    plain = initial_covariance(FilterConfig())
    assert np.array_equal(right_invariant_from_plain(plain, np.zeros(3), np.zeros(3)), plain)
    with pytest.raises(ValueError):
        right_invariant_from_plain(np.eye(4), np.zeros(3), np.zeros(3))


# ------------------------------------------------------------------------------------------
# Bias hold in outages (D-115 §3)
# ------------------------------------------------------------------------------------------


def _outage_filter() -> InEKF:
    """A filter with hold_biases=True, as replay_window sets it when
    `eval.run.HOLD_BIASES_IN_OUTAGE` is on (off since D-130; the A/B is in its comment)."""
    f = _aided_filter()
    f.hold_biases = True
    return f


def test_hold_biases_freezes_bias_covariance_during_propagation():
    """With hold_biases=True, the bias blocks of Q_c are zeroed before Van Loan, so the
    diagonal uncertainty on b_g and b_a cannot grow through propagation alone."""
    f = _outage_filter()
    p_bg_before = f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS].copy()
    p_ba_before = f.P[IDX_ACCEL_BIAS, IDX_ACCEL_BIAS].copy()
    for _ in range(50):
        f.propagate(np.array([0.0, 0.0, 0.05]), np.array([0.1, 0.0, -9.80]), 0.1)
    # Bias-block diagonals must not have grown: the STM (Phi) couples attitude into biases
    # through Q_d, but with Q_c[6:12] zeroed the only contribution is Phi * P * Phi^T, which
    # cannot grow the bias diagonals above their entry values because Phi's bias-to-bias
    # sub-block is the identity (random walk model) and the cross-terms shrink it.
    for ax in range(3):
        assert f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS][ax, ax] <= p_bg_before[ax, ax] * 1.01
        assert f.P[IDX_ACCEL_BIAS, IDX_ACCEL_BIAS][ax, ax] <= p_ba_before[ax, ax] * 1.01


def test_hold_biases_zeroes_gain_rows_for_non_exempt_updates():
    """An NHC update (no allow_bias) must not move b_g or b_a when hold_biases is True."""
    f = _outage_filter()
    bg_before = f.state.b_g.copy()
    ba_before = f.state.b_a.copy()
    # Force a large innovation so any gain leak would be visible.
    f.state.v = np.array([15.0, 3.0, 0.5])  # sideways + vertical -> NHC fires
    f.update_nhc()
    assert np.array_equal(f.state.b_g, bg_before)
    assert np.array_equal(f.state.b_a, ba_before)


def test_hold_biases_keeps_bias_states_and_blocks_bit_identical_over_a_60_s_window():
    """D-115 step 3, the acceptance test as written: with the hold and NHC + ZUPT only, `b_g`,
    `b_a` and their `P` blocks are *bit-identical* to their entry values across a 60 s window
    of propagate + update_nhc + update_zupt, not merely bounded. Bit-identity holds because the
    bias rows of `Phi` and of `I - KH` are identity rows once the gain rows are zeroed."""
    f = _outage_filter()
    f.state.b_g = np.array([0.004, -0.002, 0.003])
    f.state.b_a = np.array([0.05, -0.03, 0.02])
    bg0, ba0 = f.state.b_g.copy(), f.state.b_a.copy()
    p_bg0 = f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS].copy()
    p_ba0 = f.P[IDX_ACCEL_BIAS, IDX_ACCEL_BIAS].copy()
    rng = np.random.default_rng(3)
    for k in range(600):  # 60 s at 10 Hz
        gyro = np.array([0.0, 0.0, 0.05]) + rng.normal(0.0, 1e-3, 3)
        accel = np.array([0.2, 0.0, -9.75]) + rng.normal(0.0, 1e-2, 3)
        f.propagate(gyro, accel, 0.1)
        if k % 3 == 0:
            f.update_nhc()
        if k % 50 == 0:
            f.update_zupt()
    assert np.array_equal(f.state.b_g, bg0)
    assert np.array_equal(f.state.b_a, ba0)
    assert np.array_equal(f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS], p_bg0)
    assert np.array_equal(f.P[IDX_ACCEL_BIAS, IDX_ACCEL_BIAS], p_ba0)


def test_zaru_is_exempt_from_bias_hold():
    """ZARU directly observes b_g, so it must be allowed to update b_g even when hold_biases is
    True. It must still not touch b_a (no exemption for IDX_ACCEL_BIAS)."""
    f = _outage_filter()
    # Set a small but measurable gyro-bias error. The innovation z = gyro - b_g_hat must pass
    # the chi2 gate, whose acceptance region scales with sqrt(H P H^T + R). Inflate the gyro-
    # bias covariance so the gate accepts the 0.005 rad/s innovation.
    f.state.b_g = np.array([0.005, -0.003, 0.004])
    f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS] = np.eye(3) * 0.01**2  # 0.01 rad/s sigma per axis
    ba_before = f.state.b_a.copy()
    bg_before = f.state.b_g.copy()
    # Feed near-zero gyro as if the vehicle is still.
    accepted = f.update_zaru(np.array([0.0001, -0.0001, 0.0002]))
    assert accepted, "ZARU should accept a near-zero gyro measurement with inflated P"
    # b_g must have moved toward zero (the measurement is near-zero, bias is 0.005).
    assert not np.array_equal(f.state.b_g, bg_before), "ZARU must update b_g"
    assert np.linalg.norm(f.state.b_g) < np.linalg.norm(bg_before), "b_g should shrink"
    # b_a must be untouched.
    assert np.array_equal(f.state.b_a, ba_before), "b_a must not be moved by ZARU"


def test_hold_biases_off_allows_normal_bias_updates():
    """Sanity check: with hold_biases=False, NHC *can* move biases through cross-correlations."""
    f = _aided_filter()
    assert not f.hold_biases
    assert not f.gyro_bias_direct_only, "the filter's default: every update; D-133 is the harness's"
    f.state.v = np.array([15.0, 3.0, 0.5])
    bg_before = f.state.b_g.copy()
    f.update_nhc()
    # In the aided filter with cross-correlations, the Kalman gain's bias rows are generally
    # non-zero, so at least one axis should have moved (unless the cross-correlation happens to
    # be exactly zero, which _aided_filter's 20 propagation steps should prevent). This is the
    # mechanism `gyro_bias_direct_only` switches off in the aided pass (D-133): it stays true of
    # the filter, and the harness's policy is what changes.
    moved = not np.allclose(f.state.b_g, bg_before, atol=1e-15)
    assert moved, "Without hold_biases, NHC should move b_g through cross-terms"


# ------------------------------------------------------------------------------------------
# The gyro bias moves only under its direct observation (D-133)
# ------------------------------------------------------------------------------------------


def test_gyro_bias_direct_only_leaves_b_g_to_zaru_and_q_alone():
    """D-133. With `gyro_bias_direct_only` the position, Doppler-velocity, NHC and ZUPT updates
    leave `b_g` and its covariance block exactly where they were -- their gain has no gyro-bias
    rows -- while `b_a` still moves through the cross-terms (this is not `hold_biases`), the
    block still grows through `Q` in propagation (also not `hold_biases`), and ZARU, which passes
    `allow_bias=(IDX_GYRO_BIAS,)`, still corrects it. Measured reason, TRAIN S1 against the
    truth-standstill bias: bias-block NEES 27.3 with every update allowed, 2.1 with this."""
    f = _aided_filter()
    f.gyro_bias_direct_only = True
    assert not f.hold_biases
    f.state.v = np.array([15.0, 3.0, 0.5])  # sideways + vertical -> NHC has an innovation
    bg0 = f.state.b_g.copy()
    ba0 = f.state.b_a.copy()
    p_bg0 = f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS].copy()
    p_cross0 = f.P[IDX_GYRO_BIAS, IDX_ATTITUDE].copy()

    f.update_nhc()
    assert np.array_equal(f.state.b_g, bg0), "NHC may not move b_g"
    assert np.array_equal(f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS], p_bg0), "nor its block"
    assert not np.allclose(f.state.b_a, ba0, atol=1e-15), "b_a still moves: only the gyro rows"
    assert not np.array_equal(f.P[IDX_GYRO_BIAS, IDX_ATTITUDE], p_cross0), (
        "the cross-terms are updated: the Joseph form keeps the covariance exact for this gain"
    )
    f.update_gnss_velocity(f.state.v[:2] + np.array([2.0, -1.0]), np.eye(2) * 0.25)
    assert np.array_equal(f.state.b_g, bg0), "the Doppler velocity may not move b_g"
    assert f.update_gnss(f.state.p + np.array([3.0, -2.0, 0.0]), np.eye(3) * 9.0, gate=False)
    assert np.array_equal(f.state.b_g, bg0), "the position fix may not move b_g"
    f.update_zupt()
    assert np.array_equal(f.state.b_g, bg0), "ZUPT may not move b_g"
    assert np.array_equal(f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS], p_bg0)

    for _ in range(50):
        f.propagate(np.array([0.0, 0.0, 0.05]), np.array([0.1, 0.0, -9.80]), 0.1)
    p_bg1 = f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS]
    assert np.all(np.diag(p_bg1) > np.diag(p_bg0)), (
        "Q is untouched: the block keeps growing at gyro_bias_rw between stops"
    )

    f.state.b_g = np.array([0.005, -0.003, 0.004])
    f.P[IDX_GYRO_BIAS, IDX_GYRO_BIAS] = np.eye(3) * 0.01**2
    assert f.update_zaru(np.array([0.0001, -0.0001, 0.0002]))
    assert np.linalg.norm(f.state.b_g) < np.linalg.norm([0.005, -0.003, 0.004]), (
        "ZARU observes b_g directly and is the one update that may move it"
    )

