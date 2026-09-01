"""`R_sv` -- the PCA initialiser, in-filter estimation, and the bump detector (P-11).

The mount angle owns 20 m of the 100 m budget and the requirement is ~1 degree
(docs/ERROR_BUDGET.md section 5). A 5-degree knock costs ~87 m over a 60 s outage and is
**silent**: nothing else in the system reports it. These tests are the report.

Every scenario is synthetic and self-consistent, so the answers are known independently of the
code -- the IO-VNBD files are Git-LFS objects this container cannot fetch (D-059).
"""

from __future__ import annotations

import numpy as np
import pytest

from core.reference.inekf import (
    IDX_MOUNT,
    FilterConfig,
    InEKF,
    detect_mount_disturbance,
    exp_so3,
    initial_covariance,
    is_stationary,
    log_so3,
    nhc_is_valid,
    pca_mount_yaw,
    propagate_nominal,
)

G = 9.80665
DT = 0.1
CFG = FilterConfig()


def _driving_specific_force(n: int, rng, *, mount_yaw_rad: float, gravity_up=(0.0, 0.0, 1.0)):
    """Specific force a phone reads, in the phone frame, on a car braking and accelerating.

    The vehicle's own specific force is `(a_fwd, a_lat, -g)` in vehicle axes with `a_fwd`
    dominating -- braking and acceleration are what a car does most of. The phone sees it rotated
    by the mount yaw, which is precisely what the initialiser has to recover.
    """
    a_fwd = rng.normal(0.0, 1.2, n)
    a_lat = rng.normal(0.0, 0.3, n)
    up = np.asarray(gravity_up, dtype=float)
    up = up / np.linalg.norm(up)
    e1 = np.array([1.0, 0.0, 0.0]) - float(up @ np.array([1.0, 0.0, 0.0])) * up
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    forward = np.cos(mount_yaw_rad) * e1 + np.sin(mount_yaw_rad) * e2
    right = np.cross(-up, forward)
    return np.outer(a_fwd, forward) + np.outer(a_lat, right) + np.outer(np.full(n, G), up), a_fwd


# ------------------------------------------------------------------------------------------
# The PCA initialiser
# ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("yaw_deg", [0.0, 17.0, 45.0, -63.0, 120.0])
def test_pca_recovers_the_mount_yaw_it_was_given(yaw_deg):
    rng = np.random.default_rng(1)
    yaw = np.deg2rad(yaw_deg)
    accel, a_fwd = _driving_specific_force(4000, rng, mount_yaw_rad=yaw)
    init = pca_mount_yaw(accel, np.array([0.0, 0.0, G]), forward_reference=a_fwd)
    assert init.sign_resolved
    assert init.yaw_deg == pytest.approx(yaw_deg, abs=1.5)


def test_pca_recovers_the_full_rotation_not_just_the_yaw():
    """`R_sv` maps a phone-frame vector into vehicle axes, so the forward direction it found must
    come back as (1, 0, 0)."""
    rng = np.random.default_rng(2)
    yaw = np.deg2rad(35.0)
    accel, a_fwd = _driving_specific_force(4000, rng, mount_yaw_rad=yaw)
    init = pca_mount_yaw(accel, np.array([0.0, 0.0, G]), forward_reference=a_fwd)
    forward_phone = np.array([np.cos(yaw), np.sin(yaw), 0.0])
    assert init.r_sv @ forward_phone == pytest.approx([1.0, 0.0, 0.0], abs=0.03)
    assert np.linalg.det(init.r_sv) == pytest.approx(1.0)


def test_pca_works_with_the_phone_tilted_in_its_cradle():
    """A phone in a windscreen cradle is not level, so the horizontal plane has to come from
    gravity rather than from the phone's own z axis."""
    rng = np.random.default_rng(3)
    up = np.array([0.3, 0.0, 0.95])
    up = up / np.linalg.norm(up)
    accel, a_fwd = _driving_specific_force(
        4000, rng, mount_yaw_rad=np.deg2rad(25.0), gravity_up=up
    )
    init = pca_mount_yaw(accel, up * G, forward_reference=a_fwd)
    assert init.yaw_deg == pytest.approx(25.0, abs=2.0)
    assert init.r_sv[2] == pytest.approx(-up, abs=1e-9), "vehicle down is opposite gravity"


def test_without_a_forward_reference_the_180_degree_ambiguity_is_reported_not_guessed():
    """PCA returns an axis, and forward and backward have the same principal component. A
    180-degree mount error is not a large version of a small one -- it is a vehicle driving
    backwards, and it will not converge out under NHC -- so it must not be guessed."""
    rng = np.random.default_rng(4)
    accel, _ = _driving_specific_force(4000, rng, mount_yaw_rad=np.deg2rad(30.0))
    init = pca_mount_yaw(accel, np.array([0.0, 0.0, G]))
    assert init.sign_resolved is False
    ambiguous = np.rad2deg(np.arctan2(np.sin(init.yaw_rad), np.cos(init.yaw_rad)))
    assert min(abs(ambiguous - 30.0), abs(abs(ambiguous - 30.0) - 180.0)) < 2.0


def test_the_forward_reference_flips_the_axis_when_the_car_is_the_other_way_round():
    rng = np.random.default_rng(5)
    accel, a_fwd = _driving_specific_force(4000, rng, mount_yaw_rad=np.deg2rad(30.0))
    forward = pca_mount_yaw(accel, np.array([0.0, 0.0, G]), forward_reference=a_fwd)
    backward = pca_mount_yaw(accel, np.array([0.0, 0.0, G]), forward_reference=-a_fwd)
    delta = np.rad2deg(abs(forward.yaw_rad - backward.yaw_rad))
    assert delta == pytest.approx(180.0, abs=1.0)


def test_the_spread_narrows_with_more_data_and_with_a_stronger_forward_axis():
    """`spread_rad` is the standard error of the principal-axis angle, so it must fall as
    `1/sqrt(n_eff)` and as the eigenvalue gap widens. `P0`'s mount block reads it."""
    rng = np.random.default_rng(6)
    short, a_short = _driving_specific_force(400, rng, mount_yaw_rad=0.4)
    long, a_long = _driving_specific_force(8000, rng, mount_yaw_rad=0.4)
    s = pca_mount_yaw(short, np.array([0.0, 0.0, G]), forward_reference=a_short)
    long_init = pca_mount_yaw(long, np.array([0.0, 0.0, G]), forward_reference=a_long)
    assert long_init.spread_rad < s.spread_rad
    assert long_init.spread_rad * 3 < s.spread_rad, "should fall roughly as 1/sqrt(n)"
    assert long_init.eigenvalue_ratio > 4.0


def test_the_effective_sample_count_is_below_the_sample_count_on_correlated_data():
    """Accelerometer samples at 10 Hz are not independent draws, and using `n` would understate
    the spread by the square root of the correlation time. Derived from the measured lag-1
    autocorrelation, and labelled as derived."""
    rng = np.random.default_rng(7)
    n = 4000
    accel, a_fwd = _driving_specific_force(n, rng, mount_yaw_rad=0.2)
    # Smooth the forward channel so it is visibly correlated, as real cabin data is.
    kernel = np.ones(20) / 20.0
    smooth = np.convolve(a_fwd, kernel, mode="same")
    accel_smooth, _ = _driving_specific_force(n, rng, mount_yaw_rad=0.2)
    accel_smooth[:, 0] = np.convolve(accel_smooth[:, 0], kernel, mode="same")
    accel_smooth[:, 1] = np.convolve(accel_smooth[:, 1], kernel, mode="same")

    correlated = pca_mount_yaw(accel_smooth, np.array([0.0, 0.0, G]), forward_reference=smooth)
    assert correlated.n_effective < n


def test_pca_refuses_inputs_it_cannot_answer_from():
    with pytest.raises(ValueError, match="no magnitude"):
        pca_mount_yaw(np.zeros((10, 3)), np.zeros(3))
    with pytest.raises(ValueError, match="cannot support a principal axis"):
        pca_mount_yaw(np.zeros((2, 3)), np.array([0.0, 0.0, G]))
    with pytest.raises(ValueError, match="same stream"):
        pca_mount_yaw(np.zeros((10, 3)), np.array([0.0, 0.0, G]), forward_reference=np.zeros(5))


def test_p0s_mount_block_takes_the_initialisers_measured_spread():
    """The loop D-055 left open: with an initialiser run, the mount prior is a measurement rather
    than the stated 5-degree fallback."""
    rng = np.random.default_rng(8)
    accel, a_fwd = _driving_specific_force(8000, rng, mount_yaw_rad=0.3)
    init = pca_mount_yaw(accel, np.array([0.0, 0.0, G]), forward_reference=a_fwd)

    measured = np.sqrt(np.diag(initial_covariance(mount_sigma_rad=init.spread_rad)))[IDX_MOUNT]
    fallback = np.sqrt(np.diag(initial_covariance()))[IDX_MOUNT]
    assert measured == pytest.approx(np.full(3, init.spread_rad))
    assert fallback == pytest.approx(np.full(3, np.deg2rad(5.0)))
    with pytest.raises(ValueError, match="must be positive"):
        initial_covariance(mount_sigma_rad=0.0)


# ------------------------------------------------------------------------------------------
# The bump detector, wired
# ------------------------------------------------------------------------------------------


def test_re_inflation_widens_the_mount_block_and_touches_nothing_else():
    f = InEKF()
    before = np.diag(f.P).copy()
    r_before = f.state.R_sv.copy()

    f.reinflate_mount(np.deg2rad(5.0))

    after = np.diag(f.P)
    assert np.array_equal(f.state.R_sv, r_before), "a knock is news about uncertainty, not an angle"
    assert after[IDX_MOUNT] == pytest.approx(before[IDX_MOUNT] + np.deg2rad(5.0) ** 2)
    assert after[:15] == pytest.approx(before[:15]), "no other block may move"


def test_re_inflation_adds_variance_rather_than_resetting_it():
    """A reset would *shrink* the covariance of a filter that had already lost track, which is the
    direction that cannot recover."""
    f = InEKF()
    f.P[15:18, 15:18] = np.eye(3) * np.deg2rad(20.0) ** 2
    f.reinflate_mount(np.deg2rad(5.0))
    assert np.sqrt(np.diag(f.P)[15]) > np.deg2rad(20.0)


def test_re_inflation_refuses_a_non_positive_sigma():
    with pytest.raises(ValueError, match="must be positive"):
        InEKF().reinflate_mount(0.0)


# ------------------------------------------------------------------------------------------
# The whole loop: a 5-degree knock, detected and re-estimated
# ------------------------------------------------------------------------------------------


def _drive_with_a_knock(*, knock_rad: float, reinflate: bool, seed: int = 0):
    """Cruise at 15 m/s with a gentle yaw rate; knock the phone at t = 30 s; run to t = 90 s.

    The truth model is kept physically consistent, which matters more here than it looks:

        R_sv = R_veh<-phone, so a vehicle-frame quantity reads `R_sv.T @ v` in the phone frame
        R    = R_nav<-phone = R_nv @ R_sv
        at the knock `R_sv` jumps R_sv0 -> R_sv1, so the phone physically rotates by
        `R_sv0.T @ R_sv1` and the gyro over that sample integrates to exactly that

    A knock is not a change to `R_sv` alone: the phone really does rotate, the gyro really does
    see it, and the filter's attitude really does follow. Only `R_sv` is left wrong. Simulating
    the mount change without the matching gyro rotation makes the filter's attitude wrong too, and
    then the test measures the scenario rather than the mechanism.

    NHC is the only thing that observes the mount, and section 7.2's result is that it does so with
    **gain equal to forward speed** -- so this cruises rather than parks.

    Returns `(detector_firings, |mount yaw error|, mount sigma, peak sample-to-sample gyro step)`.
    """
    rng = np.random.default_rng(seed)
    cfg = FilterConfig()
    u, r = 15.0, 0.05
    n, knock_at = 900, 300

    r_sv = np.eye(3)
    rot_nv = np.eye(3)
    f = InEKF(cfg)
    f.state.R = rot_nv @ r_sv
    f.state.v = np.array([u, 0.0, 0.0])
    f.P = initial_covariance(cfg, mount_sigma_rad=np.deg2rad(1.0))

    sd_g = cfg.gyro_arw / np.sqrt(DT)
    sd_a = cfg.accel_vrw / np.sqrt(DT)
    window = max(1, int(round(cfg.zupt_window_s / DT)))
    acc_win = np.zeros((0, 3))
    gyro_win = np.zeros((0, 3))
    detected = 0
    peak_step = 0.0

    for k in range(n):
        omega_veh = np.array([0.0, 0.0, r])
        f_veh = np.array([0.0, u * r, -G])

        if k == knock_at:
            r_sv_next = exp_so3(np.array([0.0, 0.0, knock_rad])) @ r_sv
            omega_phone = r_sv.T @ omega_veh + log_so3(r_sv.T @ r_sv_next) / DT
        else:
            r_sv_next = r_sv
            omega_phone = r_sv.T @ omega_veh

        gyro_m = omega_phone + rng.normal(0, sd_g, 3)
        accel_m = r_sv.T @ f_veh + rng.normal(0, sd_a, 3)
        rot_nv, _, _ = propagate_nominal(rot_nv, np.zeros(3), np.zeros(3), omega_veh, f_veh, DT)
        r_sv = r_sv_next

        f.propagate(gyro_m, accel_m, DT)
        acc_win = np.vstack([acc_win, accel_m])[-window:]
        gyro_win = np.vstack([gyro_win, gyro_m])[-window:]

        if gyro_win.shape[0] >= 2:
            step = float(np.max(np.linalg.norm(np.diff(gyro_win, axis=0), axis=1)))
            peak_step = max(peak_step, step)
        if gyro_win.shape[0] >= 2 and detect_mount_disturbance(gyro_win, cfg):
            detected += 1
        # The re-inflation is driven by the knock itself rather than by the detector, because the
        # detector cannot see a knock this small -- see the blind-spot test below. This isolates
        # the mechanism P-11 owns from the threshold it depends on, which is a separate gap.
        if reinflate and k == knock_at:
            f.reinflate_mount(np.deg2rad(5.0))

        if acc_win.shape[0] == window and is_stationary(acc_win, gyro_win, cfg):
            f.update_zupt()
            f.update_zaru(gyro_m)
        elif nhc_is_valid(
            float(np.linalg.norm(f.state.v)),
            float(gyro_m[2] - f.state.b_g[2]),
            float(accel_m[1] - f.state.b_a[1]),
            cfg,
        ):
            f.update_nhc()

    error_rad = float(log_so3(f.state.R_sv @ r_sv.T)[2])
    return detected, abs(error_rad), float(np.sqrt(np.diag(f.P)[17])), peak_step


def test_re_inflating_after_the_knock_re_estimates_the_mount_and_not_re_inflating_does_not():
    """**The phase's exit criterion**, as a comparison rather than a bare threshold.

    Both runs see the identical knock and the identical NHC updates; the only difference is
    whether the mount block is widened afterwards. Measured over 60 s of cruising after a 5-degree
    knock:

        re-inflated   0.43 deg of residual mount-yaw error
        not           8.56 deg

    Not re-inflating is worse than the knock itself, because the filter carries a stale rotation
    behind a covariance that says the rotation is known -- `mount_rw` is zero (D-048), so nothing
    will ever widen it again -- and the wrong mount then drags the rest of the state with it. At
    16.7 m/s over 60 s, 8.56 deg of mount yaw is roughly 150 m of lateral error against a 100 m
    budget, and no other instrument in the system reports it.
    """
    knock = np.deg2rad(5.0)
    _, err_reinflated, sd_reinflated, _ = _drive_with_a_knock(knock_rad=knock, reinflate=True)
    _, err_stale, _, _ = _drive_with_a_knock(knock_rad=knock, reinflate=False)

    assert err_stale > knock, "a stale mount should be at least as wrong as the knock"
    assert err_reinflated < 0.2 * err_stale, "re-inflation must recover most of the knock"
    assert err_reinflated < 0.2 * knock, (
        f"mount yaw error {np.rad2deg(err_reinflated):.2f} deg after re-inflation -- NHC did not "
        "re-estimate it"
    )
    assert np.rad2deg(sd_reinflated) < 2.0, "and the covariance must come back down with it"


def test_an_undisturbed_run_does_not_drift_the_mount():
    """The control. If the mount wanders without a knock, the comparison above measures noise."""
    _, err, _, _ = _drive_with_a_knock(knock_rad=0.0, reinflate=False)
    assert np.rad2deg(err) < 1.0


def test_the_detector_cannot_see_a_five_degree_knock_at_10_hz():
    """**A gap, asserted rather than tuned away.**

    `detect_mount_disturbance` thresholds the sample-to-sample gyro step at
    `mount_disturbance_gyro_thresh` = 3.0 rad/s. A knock of angle `theta` delivered inside one
    sample cannot present more than `theta / dt` of *measured* rate however violent it was --
    the stream is 10 Hz and the transient is averaged away below Nyquist. So the threshold
    corresponds to a knock of

        3.0 rad/s * 0.1 s = 0.3 rad = **17.2 degrees**

    and the 5-degree knock docs/ERROR_BUDGET.md section 5 says costs 87 m presents 0.87 rad/s --
    a factor of 3.4 under. Measured here at 0.875 rad/s, and the detector does not fire.

    The threshold is not lowered to make this test pass. It has no source in the repo, and sizing
    it against a synthetic knock would be fitting a detector to a scenario -- what it needs is a
    recording of a real phone being knocked in a cradle, which is ten minutes of seat A's time and
    is logged as an open item (D-075). Until then the mechanism is exercised by signalling the
    knock directly, and the detector guards only a violent one (`test_bump_is_detected` in
    tests/test_filter.py, at 8 rad/s).
    """
    detected, _, _, peak_step = _drive_with_a_knock(knock_rad=np.deg2rad(5.0), reinflate=False)

    assert peak_step == pytest.approx(np.deg2rad(5.0) / DT, rel=0.05)
    assert peak_step < CFG.mount_disturbance_gyro_thresh
    assert detected == 0, "if this starts firing, D-075 has been resolved -- update it"
    assert np.rad2deg(CFG.mount_disturbance_gyro_thresh * DT) == pytest.approx(17.19, abs=0.01)


def test_the_mount_yaw_error_is_readable_in_degrees_without_a_change_of_basis():
    """D-030's convention exists for this: `xi_sv,z` is mount-yaw error **in the vehicle frame**,
    so it compares directly against section 5's ~1 degree requirement. Do not "simplify" the
    convention -- a right-multiplied one would need a rotation applied every time the budget is
    checked, which is a step someone eventually skips."""
    f = InEKF()
    knock = np.deg2rad(5.0)
    f.state.R_sv = exp_so3(np.array([0.0, 0.0, knock])) @ np.eye(3)
    assert np.rad2deg(log_so3(f.state.R_sv)[2]) == pytest.approx(5.0)
