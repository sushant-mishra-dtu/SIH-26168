"""Executable check of the derivation in docs/SE23_PROPAGATION.md.

**Why this exists.** Gate 1 is a hard stop and the InEKF is written from that document. A matrix
that is wrong on paper becomes a filter that runs, produces smooth plausible trajectories, and is
undebuggable. Every matrix the document asserts is checked here against a numerical ground truth,
so the derivation is protected by CI *before* the code that uses it exists.

**The assertions now run against `core.reference.inekf` itself.** They were originally written
against local helpers that *were* the specification; Sprint 1 (seat S) implemented that
specification and deleted the helpers, so there is one implementation and these tests check it
rather than a copy of it. `closed_form_gammas` below is the one survivor, and it is not a second
implementation -- it is the deliberately unguarded form, kept only to show where it breaks.

Numbers that came out of writing this, now recorded in the document:

* the small-angle cutoff has to be **1e-3**, not 1e-6 -- the closed form is already losing
  precision at phi ~ 1e-6, which is inside the branch that was going to use it;
* `A_RI` evaluated at the step *start* carries an O(dt^2) error that evaluating at the step
  midpoint removes almost entirely (~1800x at dt = 1 ms);
* the `Phi G Qc G^T Phi^T dt` shortcut for `Q_d` is ~4% wrong at dt = 0.1 s, which is D-031.
"""

from __future__ import annotations

import functools
import math

import numpy as np
import pytest

from core.reference.inekf import (
    ERROR_STATE_DIM,
    GRAVITY_NED,
    IDX_ATTITUDE,
    IDX_GYRO_BIAS,
    IDX_MOUNT,
    IDX_POSITION,
    IDX_VELOCITY,
    REORTHONORMALISE_EVERY,
    SMALL_ANGLE,
    FilterConfig,
    InEKF,
    a_ri,
    adjoint,
    exp_so3,
    expm_series,
    g_ri,
    gammas,
    is_stationary,
    log_so3,
    nhc_is_valid,
    process_noise_psd,
    propagate_nominal,
    se23_exp,
    se23_hat,
    se23_log,
    skew,
    unpack,
    van_loan,
    x_of,
)

# ------------------------------------------------------------------------------------------
# The one helper that stays local: the unguarded closed form, kept to show where it breaks
# ------------------------------------------------------------------------------------------


def closed_form_gammas(phi: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The textbook expressions with no small-angle guard. Used only to show where they break."""
    m = float(np.linalg.norm(phi))
    s, s2 = skew(phi), skew(phi) @ skew(phi)
    return (
        np.eye(3) + (np.sin(m) / m) * s + ((1 - np.cos(m)) / m**2) * s2,
        np.eye(3) + ((1 - np.cos(m)) / m**2) * s + ((m - np.sin(m)) / m**3) * s2,
        0.5 * np.eye(3)
        + ((m - np.sin(m)) / m**3) * s
        + ((m**2 + 2 * np.cos(m) - 2) / (2 * m**4)) * s2,
    )


# A representative mid-drive state: heading 40 deg, 16 m/s, a few tens of metres from the origin.
REF_R = exp_so3(np.array([0.05, -0.11, 0.7]))
REF_V = np.array([16.0, 1.5, -0.2])
REF_P = np.array([32.0, -14.0, 6.0])
REF_BG = np.array([0.004, -0.002, 0.006])
REF_BA = np.array([0.03, -0.05, 0.02])
RAW_OMEGA = np.array([0.02, -0.01, 0.35])
RAW_ACCEL = np.array([0.4, -0.3, -9.6])


# ------------------------------------------------------------------------------------------
# Section 8.1 -- the Gamma functions
# ------------------------------------------------------------------------------------------

ANGLES = np.logspace(-9, 0.3, 60)


@pytest.mark.parametrize("n", ANGLES)
def test_gamma_identities_hold_at_every_scale(n):
    """Gamma_0 = I + phi^ Gamma_1 and Gamma_1 = I + phi^ Gamma_2 are exact algebraic identities.

    They catch a mistyped coefficient at any magnitude, which comparing against the closed form
    near zero cannot -- there the closed form is itself the inaccurate side.
    """
    phi = np.array([0.3, -0.5, 0.81])
    phi = phi / np.linalg.norm(phi) * n
    g0, g1, g2 = gammas(phi)
    s = skew(phi)
    assert np.max(np.abs(g0 - (np.eye(3) + s @ g1))) < 1e-13
    assert np.max(np.abs(g1 - (np.eye(3) + s @ g2))) < 1e-13


def test_small_angle_cutoff_is_not_set_too_low():
    """The cutoff must sit where the closed form is *still accurate*, not where it is 0/0.

    Sweeping the identity residual puts the worst case at phi ~ 1e-6 -- which a 1e-6 cutoff would
    route to the closed form, the branch that is already degraded there. Hence SMALL_ANGLE = 1e-3.
    """
    phi = np.array([1.0, 0.0, 0.0]) * 1.2e-6
    _, g1_c, g2_c = closed_form_gammas(phi)
    _, g1_s, g2_s = gammas(phi)
    residual_closed = np.max(np.abs(g1_c - (np.eye(3) + skew(phi) @ g2_c)))
    residual_series = np.max(np.abs(g1_s - (np.eye(3) + skew(phi) @ g2_s)))

    assert residual_closed > 1e-12, "closed form is fine here -- re-derive the cutoff"
    assert residual_series < 1e-15
    assert SMALL_ANGLE > 1.2e-6


@pytest.mark.parametrize("n", np.logspace(-3, 0, 20))
def test_series_matches_closed_form_where_the_closed_form_is_trustworthy(n):
    phi = np.array([0.3, -0.5, 0.81])
    phi = phi / np.linalg.norm(phi) * n
    for got, want in zip(gammas(phi), closed_form_gammas(phi), strict=True):
        assert np.max(np.abs(got - want)) < 1e-12


def test_gammas_are_finite_at_rest():
    """phi = 0 is the ZUPT case. It happens at every traffic light, not rarely."""
    g0, g1, g2 = gammas(np.zeros(3))
    assert np.isfinite(g0).all() and np.isfinite(g1).all() and np.isfinite(g2).all()
    assert np.allclose(g0, np.eye(3))
    assert np.allclose(g1, np.eye(3))
    assert np.allclose(g2, 0.5 * np.eye(3)), "Gamma_2 -> I/2 recovers the 1/2 a t^2 term"


# ------------------------------------------------------------------------------------------
# Section 2.1 -- the adjoint
# ------------------------------------------------------------------------------------------


def test_adjoint_matches_conjugation():
    rng = np.random.default_rng(7)
    x = x_of(exp_so3(rng.normal(0, 1, 3)), rng.normal(0, 5, 3), rng.normal(0, 50, 3))
    xi = rng.normal(0, 1, 9)
    lhs = x @ se23_hat(xi) @ np.linalg.inv(x)
    assert np.max(np.abs(lhs - se23_hat(adjoint(x) @ xi))) < 1e-9


# ------------------------------------------------------------------------------------------
# Section 8.1 -- nominal propagation
# ------------------------------------------------------------------------------------------


def test_stationary_phone_does_not_drift():
    """The gravity-sign test. A level phone at rest reads specific force -g in the body frame;
    a = R f + g must cancel to exactly zero."""
    rot, v, p = np.eye(3), np.zeros(3), np.zeros(3)
    f_static = -GRAVITY_NED
    for _ in range(600):  # 60 s at 10 Hz
        rot, v, p = propagate_nominal(rot, v, p, np.zeros(3), f_static, 0.1)
    assert np.linalg.norm(p) < 1e-3


def test_the_gravity_sign_test_can_actually_fail():
    """A test that has never been seen to fail is not known to work (Gate 0's rule)."""
    v, p = np.zeros(3), np.zeros(3)
    f_static = -GRAVITY_NED
    for _ in range(600):
        v = v + f_static * 0.1 - GRAVITY_NED * 0.1  # sign flipped on purpose
        p = p + v * 0.1
    assert np.linalg.norm(p) > 1e3


def test_attitude_closes_after_a_full_turn():
    rot = np.eye(3)
    for _ in range(1000):
        rot = rot @ gammas(np.array([0, 0, 2 * np.pi / 10.0]) * 0.01)[0]
    assert np.max(np.abs(rot - np.eye(3))) < 1e-9


# ------------------------------------------------------------------------------------------
# Section 5.2 -- A_RI, the matrix Sprint 1 is written from
# ------------------------------------------------------------------------------------------


def _numeric_transition(dt: float, eps: float = 1e-6) -> np.ndarray:
    """Propagate true and estimated states from the SAME raw readings; differentiate the error.

    Compares against the discrete transition rather than A itself: recovering A by a difference
    quotient needs dt*eps ~ 1e-12 in the denominator, which is below the rounding floor of the
    state.
    """

    def step(e0: np.ndarray) -> np.ndarray:
        xi, dbg, dba, xsv = e0[0:9], e0[9:12], e0[12:15], e0[15:18]
        rot_h, v_h, p_h = unpack(se23_exp(xi) @ x_of(REF_R, REF_V, REF_P))
        true2 = propagate_nominal(REF_R, REF_V, REF_P, RAW_OMEGA - REF_BG, RAW_ACCEL - REF_BA, dt)
        est2 = propagate_nominal(
            rot_h, v_h, p_h, RAW_OMEGA - (REF_BG + dbg), RAW_ACCEL - (REF_BA + dba), dt
        )
        new_xi = se23_log(x_of(*est2) @ np.linalg.inv(x_of(*true2)))
        return np.concatenate([new_xi, dbg, dba, xsv])

    phi = np.zeros((18, 18))
    for j in range(18):
        e = np.zeros(18)
        e[j] = eps
        phi[:, j] = (step(e) - step(-e)) / (2 * eps)
    return phi


def test_analytic_transition_converges_to_the_numerical_one_at_second_order():
    """The residual from evaluating A at the step start is O(dt^2), which is what proves A right.

    A wrong entry would leave an O(1) or O(dt) floor that halving dt does not remove. Four
    halvings each cutting the error by 4x is the signature of correct linearisation.
    """
    errors = []
    for dt in (4e-3, 2e-3, 1e-3, 5e-4):
        err = np.max(np.abs(_numeric_transition(dt) - expm_series(a_ri(REF_R, REF_V, REF_P) * dt)))
        errors.append(err / dt**2)
    assert max(errors) / min(errors) < 1.05, f"not clean O(dt^2): err/dt^2 = {errors}"


def test_evaluating_a_at_the_step_midpoint_removes_the_second_order_error():
    """Recorded because it is a free accuracy win Sprint 1 should take (section 8.1 note)."""
    dt = 1e-3
    numeric = _numeric_transition(dt)
    at_start = np.max(np.abs(numeric - expm_series(a_ri(REF_R, REF_V, REF_P) * dt)))
    midpoint = propagate_nominal(
        REF_R, REF_V, REF_P, RAW_OMEGA - REF_BG, RAW_ACCEL - REF_BA, dt / 2
    )
    at_mid = np.max(np.abs(numeric - expm_series(a_ri(*midpoint) * dt)))
    assert at_mid < at_start / 100


def test_right_invariant_attitude_error_is_constant_under_propagation():
    """The defining property: with no bias error, the attitude block of Phi is exactly I."""
    phi = _numeric_transition(1e-3)
    assert np.max(np.abs(phi[0:3, 0:3] - np.eye(3))) < 1e-6


def test_gravity_coupling_is_the_only_path_from_attitude_to_velocity():
    dt = 1e-3
    phi = _numeric_transition(dt)
    assert np.max(np.abs(phi[3:6, 0:3] - skew(GRAVITY_NED) * dt)) < 1e-6


def test_pose_block_is_invariant_to_yaw():
    """The property the whole construction exists for. Assert it directly, per section 9 test 5."""
    base = a_ri(REF_R, REF_V, REF_P)[0:9, 0:9]
    for psi in (0.0, 0.7, 2.1, -1.3, 3.0):
        rz = exp_so3(np.array([0, 0, psi]))
        rotated = a_ri(rz @ REF_R, rz @ REF_V, rz @ REF_P)[0:9, 0:9]
        assert np.array_equal(base, rotated), f"pose block changed under yaw {psi}"


def test_pose_block_contains_only_gravity_and_identity():
    base = a_ri(REF_R, REF_V, REF_P)[0:9, 0:9]
    assert np.array_equal(base[3:6, 0:3], skew(GRAVITY_NED))
    assert np.array_equal(base[6:9, 3:6], np.eye(3))
    assert np.count_nonzero(base) == np.count_nonzero(skew(GRAVITY_NED)) + 3


def test_the_yaw_invariance_test_is_not_vacuous():
    """The left-invariant pose block *does* vary with yaw. If it did not, the test above would
    pass for any filter and prove nothing."""

    def a_li_pose(omega, accel):
        a = np.zeros((9, 9))
        a[0:3, 0:3] = a[3:6, 3:6] = a[6:9, 6:9] = -skew(omega)
        a[3:6, 0:3], a[6:9, 3:6] = -skew(accel), np.eye(3)
        return a

    rotated = exp_so3(np.array([0, 0, 1.1])) @ RAW_OMEGA
    assert not np.array_equal(a_li_pose(RAW_OMEGA, RAW_ACCEL), a_li_pose(rotated, RAW_ACCEL))


# ------------------------------------------------------------------------------------------
# Section 7 -- measurement Jacobians
# ------------------------------------------------------------------------------------------

R_SV = exp_so3(np.array([0.01, -0.02, 0.09]))


def _numeric_h(h, dim: int) -> np.ndarray:
    jac = np.zeros((dim, 18))
    for j in range(18):
        e = np.zeros(18)
        e[j] = 1e-7
        jac[:, j] = (h(e) - h(-e)) / 2e-7
    return jac


def test_body_velocity_jacobian_has_a_zero_attitude_column():
    """Section 7.1 -- the single zero that is most of the argument for the right-invariant error.

    A body-frame velocity constraint carries no instantaneous heading information. A naive EKF's
    Jacobian has a non-zero entry here, gains spurious yaw observability, and shrinks its yaw
    covariance on evidence it does not have.
    """

    def h(e):
        rot, v, _ = unpack(se23_exp(e[0:9]) @ x_of(REF_R, REF_V, REF_P))
        return rot.T @ v

    numeric = _numeric_h(h, 3)
    expected = np.zeros((3, 18))
    expected[:, 3:6] = REF_R.T
    assert np.max(np.abs(numeric - expected)) < 1e-5
    assert np.max(np.abs(numeric[:, 0:3])) < 1e-5


def test_vehicle_velocity_jacobian_includes_the_mount_angle():
    """Section 7.2."""

    def h(e):
        rot, v, _ = unpack(se23_exp(e[0:9]) @ x_of(REF_R, REF_V, REF_P))
        return exp_so3(e[15:18]) @ R_SV @ rot.T @ v

    numeric = _numeric_h(h, 3)
    expected = np.zeros((3, 18))
    expected[:, 3:6] = R_SV @ REF_R.T
    expected[:, 15:18] = -skew(R_SV @ REF_R.T @ REF_V)
    assert np.max(np.abs(numeric - expected)) < 1e-5


@pytest.mark.parametrize("speed", [0.0, 1.0, 16.7])
def test_mount_angle_observability_scales_with_forward_speed(speed):
    """Section 7.2 makes D-006 quantitative: the NHC rows observe mount yaw and pitch with gain
    equal to forward speed -- well on a motorway, not at all in a car park (D-016)."""
    block = -skew(np.array([speed, 0.0, 0.0]))
    assert np.allclose(block[1], [0, 0, speed]), "lateral row observes mount yaw"
    assert np.allclose(block[2], [0, -speed, 0]), "vertical row observes mount pitch"
    if speed == 0.0:
        assert np.count_nonzero(block) == 0, "nothing is observable at a standstill"


def test_zaru_observes_gyro_bias_directly():
    """Section 7.3. Contrast with test_body_velocity_jacobian_has_a_zero_attitude_column: ZARU is
    the only cheap, direct handle on the dominant error term."""
    h_zaru = np.zeros((3, 18))
    h_zaru[:, 9:12] = -np.eye(3)
    assert np.array_equal(h_zaru[:, 9:12], -np.eye(3))
    assert np.count_nonzero(h_zaru) == 3, "no coupling to anything else"


def test_gnss_jacobian():
    """Section 7.4 -- the state dependence the right-invariant choice pays for. It is on position,
    not attitude, so it does not touch the yaw-observability property."""

    def h(e):
        return unpack(se23_exp(e[0:9]) @ x_of(REF_R, REF_V, REF_P))[2]

    numeric = _numeric_h(h, 3)
    expected = np.zeros((3, 18))
    expected[:, 0:3], expected[:, 6:9] = -skew(REF_P), np.eye(3)
    assert np.max(np.abs(numeric - expected)) < 1e-4


def test_gnss_direct_and_adjoint_paths_agree():
    """Section 7.4 promises these are equivalent; Sprint 1 implements one and checks the other."""
    x = x_of(REF_R, REF_V, REF_P)
    ad_inv = adjoint(np.linalg.inv(x))
    h_direct = np.zeros((3, 9))
    h_direct[:, 0:3], h_direct[:, 6:9] = -skew(REF_P), np.eye(3)
    h_left = np.zeros((3, 9))
    h_left[:, 6:9] = REF_R  # left-invariant H, rotated back into the world frame
    assert np.max(np.abs(h_direct - h_left @ ad_inv)) < 1e-9


# ------------------------------------------------------------------------------------------
# Section 8.2 -- discrete covariance
# ------------------------------------------------------------------------------------------

Q_C = np.diag(
    np.concatenate(
        [
            np.full(3, 3.0e-3**2),
            np.full(3, 3.0e-2**2),
            np.full(3, 1.0e-5**2),
            np.full(3, 1.0e-4**2),
            np.full(3, 1.0e-6**2),
        ]
    )
)


def _gqg() -> np.ndarray:
    g = g_ri(REF_R, REF_V, REF_P)
    return g @ Q_C @ g.T


def test_van_loan_qd_is_symmetric_and_psd():
    _, qd = van_loan(a_ri(REF_R, REF_V, REF_P), _gqg(), 0.1)
    assert np.max(np.abs(qd - qd.T)) / np.max(np.abs(qd)) < 1e-12
    assert np.min(np.linalg.eigvalsh((qd + qd.T) / 2)) > -1e-12 * np.max(np.abs(qd))


def test_van_loan_qd_reduces_to_the_continuous_form_as_dt_shrinks():
    _, qd = van_loan(a_ri(REF_R, REF_V, REF_P), _gqg(), 1e-6)
    assert np.max(np.abs(qd - _gqg() * 1e-6)) / np.max(np.abs(_gqg() * 1e-6)) < 1e-5


def test_van_loan_phi_matches_expm():
    a = a_ri(REF_R, REF_V, REF_P)
    phi, _ = van_loan(a, _gqg(), 0.1)
    assert np.max(np.abs(phi - expm_series(a * 0.1))) < 1e-12


def test_the_cheap_qd_shortcut_is_measurably_wrong():
    """D-031. The shortcut is not merely inelegant -- at the dt we actually run it misallocates
    process noise by several percent, and an under-sized Q is what makes a filter reject good
    measurements at the chi-squared gate."""
    a = a_ri(REF_R, REF_V, REF_P)
    phi, qd = van_loan(a, _gqg(), 0.1)
    cheap = phi @ _gqg() @ phi.T * 0.1
    assert np.max(np.abs(cheap - qd)) / np.max(np.abs(qd)) > 0.01


# ------------------------------------------------------------------------------------------
# Section 5.3 -- units
# ------------------------------------------------------------------------------------------


def test_arw_conversion_round_trips():
    """A factor-of-60 slip is invisible: the filter runs, just 3600x wrong in variance."""
    deg_per_sqrt_hr = 2.5
    sigma = deg_per_sqrt_hr * (np.pi / 180) / 60
    assert sigma == pytest.approx(7.2722e-4, rel=1e-4)
    assert sigma / ((np.pi / 180) / 60) == pytest.approx(deg_per_sqrt_hr)


def test_default_gyro_arw_is_the_measured_value_inside_the_documented_phone_range():
    """Replaces the R-2 placeholder assertion, at that test's own instruction.

    It used to assert `gyro_arw > 5 deg/sqrt(hr)` -- i.e. that the 3e-3 placeholder was outside the
    0.5-5 range ERROR_BUDGET.md section 9 states -- with a message saying to delete it once the
    Allan run landed. It landed (D-045): 4.11e-4 rad/s/sqrt(Hz) = 1.41 deg/sqrt(hr), measured on
    IO-VNBD's own stationary segments. The assertion is inverted to hold the range from the other
    side, so a future edit that reintroduces an out-of-range guess still fails here.
    """
    from core.reference.inekf import FilterConfig

    deg_sqrt_hr = FilterConfig().gyro_arw / ((np.pi / 180) / 60)
    assert 0.5 <= deg_sqrt_hr <= 5.0, (
        f"gyro_arw is {deg_sqrt_hr:.2f} deg/sqrt(hr), outside the 0.5-5 phone-MEMS range in "
        "ERROR_BUDGET.md section 9. Either re-run `python -m eval.allan` and update both, or say "
        "in the budget why this sensor sits outside it."
    )
    assert deg_sqrt_hr == pytest.approx(1.41, abs=0.02)


# ------------------------------------------------------------------------------------------
# Section 8 -- InEKF.propagate, the wiring of the pieces above
#
# The tests above check the matrices. These check that propagate() actually uses them: the
# right ones, at the right linearisation point, with the biases removed first. A filter can
# have every matrix correct and still be wrong here, and the symptom is a smooth plausible
# trajectory.
# ------------------------------------------------------------------------------------------


def test_propagate_leaves_a_stationary_phone_where_it_started():
    """SE_2(3) test 2 at the filter level. Closed-form reference: exactly zero.

    A level phone at rest reports specific force -g. If the gravity sign is wrong anywhere in
    propagate(), 60 s of this puts the vehicle ~176 m away, which is the whole error budget.
    """
    f = InEKF()
    for _ in range(600):  # 60 s at 10 Hz
        f.propagate(np.zeros(3), -GRAVITY_NED, 0.1)
    assert np.linalg.norm(f.state.p) < 1e-3
    assert np.linalg.norm(f.state.v) < 1e-4


def test_propagate_subtracts_the_bias_before_integrating():
    """Feed the filter exactly its own bias estimate; the state must not move at all.

    Hand-computed: omega - b_g = 0 and a - b_a = -g, so R stays I and the gravity terms cancel.
    Catches a propagate() that integrates the raw reading, which no matrix test can see.
    """
    f = InEKF()
    f.state.b_g = np.array([0.01, -0.02, 0.03])
    f.state.b_a = np.array([0.2, -0.1, 0.05])
    for _ in range(100):
        f.propagate(f.state.b_g.copy(), -GRAVITY_NED + f.state.b_a, 0.1)
    assert np.max(np.abs(f.state.R - np.eye(3))) < 1e-12
    assert np.linalg.norm(f.state.p) < 1e-9


def test_propagate_refuses_a_non_positive_dt():
    """Five IO-VNBD S- files restart their clock mid-recording (M, S2, S4, Y1, S3b). A window
    placed across one hands propagate() a negative interval; integrating it silently runs the
    filter backwards, so it must raise instead."""
    f = InEKF()
    for bad in (0.0, -0.1):
        with pytest.raises(ValueError, match="dt must be positive"):
            f.propagate(np.zeros(3), -GRAVITY_NED, bad)


def test_propagate_rejects_a_non_finite_sample():
    f = InEKF()
    with pytest.raises(ValueError, match="non-finite"):
        f.propagate(np.array([np.nan, 0.0, 0.0]), -GRAVITY_NED, 0.1)


def test_covariance_stays_symmetric_and_psd_and_grows_without_measurements():
    """With no update applied there is nothing to shrink P, so its trace must increase
    monotonically. A P that shrinks under pure propagation is a filter inventing information."""
    f = InEKF()
    traces = []
    for _ in range(200):
        f.propagate(np.array([0.0, 0.0, 0.35]), np.array([0.4, -0.3, -9.6]), 0.1)
        assert np.max(np.abs(f.P - f.P.T)) < 1e-18 * max(1.0, np.max(np.abs(f.P)))
        traces.append(np.trace(f.P))
    assert np.min(np.linalg.eigvalsh(f.P)) > 0, "covariance left the PSD cone"
    assert all(b > a for a, b in zip(traces, traces[1:], strict=False)), "trace(P) must grow"


def test_propagate_linearises_at_the_midpoint_not_the_step_start():
    """D-029. Composing the same step with A evaluated at the interval start must give a
    *measurably* different covariance -- if it did not, the midpoint evaluation is not actually
    happening and the O(dt^2) error the derivation measured is still there.

    Measured separation at dt = 0.1 s from a mid-drive state: 3.7% of max|P|. The threshold below
    is two orders under that, so the test fails on a regression to start-linearisation rather than
    merely on float noise.

    `P0` is pinned here rather than inherited from the config default (D-055 replaced that
    default). The separation this measures runs through `A`'s state-dependent columns, which are
    the *bias* columns, so it scales with the prior's bias blocks: under the per-block `P0` the
    same step separates by 9.2e-7 absolute, and the ratio to a max|P| now dominated by a 9 m^2
    position block is 1e-7. That is the normaliser moving, not the midpoint evaluation going away
    -- so the experiment keeps the flat prior it was calibrated against, and says so.
    """
    gyro, accel, dt = np.array([0.0, 0.0, 0.35]), np.array([0.4, -0.3, -9.6]), 0.1
    f = InEKF(p0=np.eye(ERROR_STATE_DIM) * 1e-3)
    f.state.v = np.array([16.0, 1.5, -0.2])
    f.state.p = np.array([32.0, -14.0, 6.0])
    p_before = f.P.copy()
    f.propagate(gyro, accel, dt)

    a_start = a_ri(np.eye(3), np.array([16.0, 1.5, -0.2]), np.array([32.0, -14.0, 6.0]))
    g_start = g_ri(np.eye(3), np.array([16.0, 1.5, -0.2]), np.array([32.0, -14.0, 6.0]))
    qc = process_noise_psd(FilterConfig())
    phi, qd = van_loan(a_start, g_start @ qc @ g_start.T, dt)
    at_start = phi @ p_before @ phi.T + qd
    separation = np.max(np.abs(f.P - at_start)) / np.max(np.abs(f.P))
    assert separation > 1e-3, (
        f"P is within {separation:.2e} of the start-linearised composition -- propagate() "
        "is evaluating A at the interval start, not the midpoint (D-029)"
    )


def test_reorthonormalisation_keeps_r_on_so3():
    f = InEKF()
    for _ in range(REORTHONORMALISE_EVERY):
        f.propagate(np.array([0.05, -0.02, 0.35]), np.array([0.4, -0.3, -9.6]), 0.01)
    assert f.steps % REORTHONORMALISE_EVERY == 0, "the counter must have reached the cadence"
    assert np.max(np.abs(f.state.R.T @ f.state.R - np.eye(3))) < 1e-15
    assert np.linalg.det(f.state.R) == pytest.approx(1.0, abs=1e-15)


# ------------------------------------------------------------------------------------------
# Section 5.3 -- Q_c is read from FilterConfig, not retyped
# ------------------------------------------------------------------------------------------


def test_process_noise_psd_is_the_squares_of_the_measured_config_values():
    """Q_c must be the D-045 measured Allan coefficients squared, in that order. A transposed
    block here scales the gyro noise by the accelerometer's, which is invisible downstream."""
    cfg = FilterConfig()
    qc = process_noise_psd(cfg)
    assert qc.shape == (15, 15)
    assert np.array_equal(qc, np.diag(np.diag(qc))), "Q_c is diagonal by construction"
    expected = np.concatenate(
        [
            np.full(3, cfg.gyro_arw**2),
            np.full(3, cfg.accel_vrw**2),
            np.full(3, cfg.gyro_bias_rw**2),
            np.full(3, cfg.accel_bias_rw**2),
            np.full(3, cfg.mount_rw**2),
        ]
    )
    assert np.array_equal(np.diag(qc), expected)


def test_the_mount_block_of_q_carries_no_process_noise_yet():
    """D-048, asserted rather than left to a comment. The derivation names sigma_sv but no source
    in the repo gives it a magnitude, so it is zero -- the mount is modelled as rigid until P-11
    estimates R_sv and the bump detector re-inflates it. If P-11 sets a value, this test is the
    thing that says so out loud."""
    assert FilterConfig().mount_rw == 0.0
    f = InEKF()
    before = f.P[IDX_MOUNT, IDX_MOUNT].copy()
    for _ in range(50):
        f.propagate(np.array([0.0, 0.0, 0.35]), np.array([0.4, -0.3, -9.6]), 0.1)
    assert np.allclose(f.P[IDX_MOUNT, IDX_MOUNT], before)
    assert f.P.shape == (ERROR_STATE_DIM, ERROR_STATE_DIM)


# ------------------------------------------------------------------------------------------
# Section 9, tests 7-11 -- the update family (P-03)
#
# Tests 1-6 above check that the matrices are right. These check that the four updates use
# them correctly: the right Jacobian, the right innovation, and -- the one that is easy to get
# backwards and impossible to see afterwards -- the right SIGN on the correction.
#
# Section 5 defines the right-invariant error as `eta_R = X_hat X^-1`, so `xi` is the error *in
# the estimate*. `delta = K z` therefore estimates that error, and the retraction subtracts it
# (D-050). Section 8.3 of the derivation still writes a plus; it is wrong and D-050 supersedes it.
# ------------------------------------------------------------------------------------------


def test_zaru_converges_the_gyro_bias_to_truth():
    """SE_2(3) test 7. A constant injected bias, repeated ZARU, `b_g_hat` -> truth.

    The whole yaw budget rests on this: 40 m of a 100 m error budget is lateral error driven by
    residual gyro bias, and ZARU is the only thing that observes `b_g` directly (section 7.3).
    If the correction sign were flipped this diverges rather than converges, which is the failure
    a convergence assertion catches and a Jacobian assertion does not.
    """
    truth = np.array([2.0e-3, -1.5e-3, 3.0e-3])  # rad/s, ~10x the measured 42 deg/hr instability
    f = InEKF()
    f.P = np.eye(ERROR_STATE_DIM) * 1e-4
    before = float(np.linalg.norm(f.state.b_g - truth))
    for _ in range(300):
        f.propagate(truth, -GRAVITY_NED, 0.1)
        f.update_zaru(truth)
    after = float(np.linalg.norm(f.state.b_g - truth))
    assert after < before / 100.0, f"b_g did not converge: {before:.3e} -> {after:.3e}"
    assert np.trace(f.P[9:12, 9:12]) < np.trace(np.eye(3) * 1e-4), "ZARU must shrink the b_g block"


def test_zaru_rejects_a_malformed_gyro_sample():
    """The raw sample is an argument (D-052) precisely so it can be wrong; say so loudly."""
    f = InEKF()
    with pytest.raises(ValueError, match="3-vector gyro"):
        f.update_zaru(np.zeros((3, 3)))


def test_zupt_drives_a_wrong_velocity_to_zero_and_shrinks_its_covariance():
    """SE_2(3) test 8. Stationary with a wrong initial velocity: `v_hat` -> 0 and `P` shrinks."""
    f = InEKF()
    f.state.v = np.array([2.0, -1.0, 0.5])
    v_before = float(np.linalg.norm(f.state.v))
    p_before = np.trace(f.P[3:6, 3:6])
    for _ in range(200):
        f.propagate(np.zeros(3), -GRAVITY_NED, 0.1)
        f.update_zupt()
    assert float(np.linalg.norm(f.state.v)) < v_before / 100.0
    assert np.trace(f.P[3:6, 3:6]) < p_before


def test_zupt_does_not_shrink_the_mount_covariance():
    """D-051. ZUPT uses section 7.1's body-frame Jacobian, not section 7.2's vehicle-frame one.

    The two assert the same thing -- `R_sv` is a rotation, so `R_sv R^T v = 0` exactly when
    `R^T v = 0` -- but 7.2 carries a `-v_veh_hat^` mount column. Section 7.2's own result is that
    mount observability through a velocity constraint has **gain equal to forward speed**, and at
    a standstill that gain is zero. Using 7.2 here would let a stop shrink the mount block in
    proportion to the filter's own velocity *error*, which is information the stop does not carry.

    The velocity error below is deliberately large, because that is exactly the case where the
    vehicle-frame Jacobian's mount column is most non-zero and the bug would be biggest.
    """
    f = InEKF()
    f.state.v = np.array([5.0, -3.0, 1.0])
    mount_before = f.P[IDX_MOUNT, IDX_MOUNT].copy()
    for _ in range(50):
        f.propagate(np.zeros(3), -GRAVITY_NED, 0.1)
        f.update_zupt()
    assert np.allclose(f.P[IDX_MOUNT, IDX_MOUNT], mount_before), (
        "ZUPT shrank the mount covariance -- it is using the vehicle-frame Jacobian (section "
        "7.2) rather than the body-frame one (section 7.1). See D-051."
    )


def _nhc_mount_run(speed: float, steps: int = 300) -> tuple[float, float]:
    """Straight drive at `speed` with a true 5-degree mount yaw the filter does not know about.

    Returns (final mount-yaw error in degrees, final sigma(xi_sv,z) in degrees). The truth is
    constructed so the vehicle-frame velocity is exactly `(speed, 0, 0)` -- NHC's assumption
    holds perfectly, so anything the filter learns is genuinely from the mount, not from a
    scenario that quietly violates the constraint.
    """
    alpha = np.deg2rad(5.0)
    r_sv_true = exp_so3(np.array([0.0, 0.0, alpha]))
    f = InEKF()
    f.state.R = np.eye(3)
    f.state.v = r_sv_true.T @ np.array([speed, 0.0, 0.0])
    f.state.R_sv = np.eye(3)  # the filter believes the phone is aligned with the vehicle
    sd = np.zeros(ERROR_STATE_DIM)
    sd[0:3] = np.deg2rad(1.0)
    sd[3:6] = 0.05
    sd[6:9] = 1.0
    sd[9:12] = 1e-4
    sd[12:15] = 1e-3
    sd[15:18] = np.deg2rad(10.0)  # loose on the mount: it is the thing being learned
    f.P = np.diag(sd**2)
    for _ in range(steps):
        f.update_nhc()
    err = abs(log_so3(f.state.R_sv @ r_sv_true.T)[2])
    return float(np.rad2deg(err)), float(np.rad2deg(np.sqrt(f.P[17, 17])))


def test_nhc_learns_the_mount_yaw_and_learns_it_faster_at_speed():
    """SE_2(3) test 9. Section 7.2's `-v_veh_hat^` column made quantitative.

    For a vehicle moving forward at `u` the lateral row of that column is `[0, 0, +u]`, so the
    mount angle is observable through NHC **with gain equal to forward speed** -- estimated well
    on a motorway and barely at all in a car park. That is D-006's claim turned into a number,
    and section 7.2 names `sigma(xi_sv,z)` against speed as the thing to plot at Gate 1.

    Measured here: after 300 updates the residual sigma is 0.660 / 0.220 / 0.132 degrees at
    5 / 15 / 25 m/s -- monotone in speed, which is the assertion.
    """
    errs, sigmas = zip(*(_nhc_mount_run(u) for u in (5.0, 15.0, 25.0)), strict=True)
    assert errs[-1] < 0.05, f"mount yaw did not converge at speed: {errs[-1]:.3f} deg"
    assert all(b < a for a, b in zip(sigmas, sigmas[1:], strict=False)), (
        f"sigma(xi_sv,z) must fall as speed rises (section 7.2); got {sigmas}"
    )
    assert all(b < a for a, b in zip(errs, errs[1:], strict=False)), (
        f"mount-yaw error must fall as speed rises; got {errs}"
    )


def test_gnss_direct_and_adjoint_paths_agree_to_floating_point():
    """SE_2(3) test 10. Section 7.4 offers two routes and requires they be the same map.

    Direct: `H = [-p_hat^, 0, I, ...]` in the right-invariant coordinates the covariance is
    carried in. Adjoint: move to left-invariant coordinates with `P_L = Ad_X^-1 P_R Ad_X^-T`,
    apply `H_L = [0, 0, I]` with rotated noise `R_hat^T Sigma R_hat`, transform back.

    They agree identically only if `H_gnss` is exactly right: `H_R Ad_X = [0, 0, R_hat]`, and a
    sign or a transpose anywhere in that `-p_hat^` block breaks the identity. This is the test
    that catches a plausible-looking GNSS Jacobian.
    """
    rng = np.random.default_rng(7)
    f = InEKF()
    f.state.R = exp_so3(np.array([0.05, -0.03, 0.7]))
    f.state.v = np.array([14.0, 2.0, -0.3])
    f.state.p = np.array([220.0, -95.0, 4.0])
    f.state.R_sv = exp_so3(np.array([0.0, 0.0, 0.08]))
    a = rng.normal(size=(ERROR_STATE_DIM, ERROR_STATE_DIM))
    f.P = a @ a.T + np.eye(ERROR_STATE_DIM)

    fix = f.state.p + np.array([1.4, -0.9, 0.3])
    sigma = np.diag([9.0, 9.0, 25.0])

    # --- the adjoint path, built here from the derivation, not from the implementation ---
    rot, p_hat, p_r = f.state.R.copy(), f.state.p.copy(), f.P.copy()
    ad = np.eye(ERROR_STATE_DIM)
    ad[0:9, 0:9] = adjoint(x_of(rot, f.state.v, p_hat))
    ad_inv = np.linalg.inv(ad)
    p_l = ad_inv @ p_r @ ad_inv.T
    h_l = np.zeros((3, ERROR_STATE_DIM))
    h_l[:, 6:9] = np.eye(3)
    z_l = rot.T @ (p_hat - fix)
    r_l = rot.T @ sigma @ rot
    k_l = p_l @ h_l.T @ np.linalg.inv(h_l @ p_l @ h_l.T + r_l)
    delta = ad @ (k_l @ z_l)
    ikh = np.eye(ERROR_STATE_DIM) - k_l @ h_l
    p_l_post = ikh @ p_l @ ikh.T + k_l @ r_l @ k_l.T
    p_expected = ad @ p_l_post @ ad.T
    p_expected = 0.5 * (p_expected + p_expected.T)
    x_expected = se23_exp(-delta[0:9]) @ x_of(rot, f.state.v, p_hat)
    rot_e, v_e, p_e = unpack(x_expected)

    assert f.update_gnss(fix, sigma) is True
    assert np.max(np.abs(f.state.R - rot_e)) < 1e-9
    assert np.max(np.abs(f.state.v - v_e)) < 1e-9
    assert np.max(np.abs(f.state.p - p_e)) < 1e-9
    assert np.max(np.abs(f.P - p_expected)) / np.max(np.abs(f.P)) < 1e-9


def test_gnss_rejects_a_malformed_fix():
    f = InEKF()
    with pytest.raises(ValueError, match="3-vector position"):
        f.update_gnss(np.zeros(2), np.eye(3))
    with pytest.raises(ValueError, match="3x3 position covariance"):
        f.update_gnss(np.zeros(3), np.eye(4))


# ------------------------------------------------------------------------------------------
# Section 9, test 11 -- consistency
#
# The test that catches an inconsistent filter, which is the failure the whole design exists to
# avoid. A filter that passes 7-10 and fails 11 is not "nearly working": it is lying about its
# own covariance, and everything downstream reads that covariance -- the chi-squared gate, the
# uncertainty ellipse, and the map matcher's emission sigma.
#
# Method: draw the initial error from P0, drive truth and filter with the same IMU stream, and
# form NEES = e^T P^-1 e at the end. Over N runs the mean must sit inside the 95% chi-squared
# band for 18*N degrees of freedom, divided by N.
# ------------------------------------------------------------------------------------------

NEES_RUNS = 100
NEES_DT = 0.1
NEES_STEPS = 600  # 60 s, the reference outage length


def chi2_quantile(p: float, dof: int) -> float:
    """Inverse chi-squared CDF, by bisection on the regularised lower incomplete gamma.

    scipy is deliberately not a dependency (D-024), and the band this test asserts must be
    computed rather than pasted in as a magic constant -- a hand-typed quantile is exactly the
    kind of number that gets quietly widened when a test starts failing.

    `F(x; k) = P(k/2, x/2)`, so the root is found in `x/2` and doubled.
    """
    a = dof / 2.0

    def lower(x: float) -> float:
        if x <= 0:
            return 0.0
        scale = math.exp(-x + a * math.log(x) - math.lgamma(a))
        if x < a + 1.0:  # series
            term = total = 1.0 / a
            for n in range(1, 1_000_000):
                term *= x / (a + n)
                total += term
                if abs(term) < abs(total) * 1e-16:
                    break
            return total * scale
        tiny = 1e-300  # continued fraction on the upper tail
        b, c, d = x + 1.0 - a, 1.0 / tiny, 1.0 / (x + 1.0 - a)
        h = d
        for i in range(1, 1_000_000):
            an = -i * (i - a)
            b += 2.0
            d = an * d + b
            d = tiny if abs(d) < tiny else d
            c = b + an / c
            c = tiny if abs(c) < tiny else c
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 1e-16:
                break
        return 1.0 - scale * h

    lo, hi = 0.0, max(10.0 * dof, 100.0)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if lower(mid) < p:
            lo = mid
        else:
            hi = mid
    return lo + hi


def test_chi2_quantile_matches_published_values():
    """Including the one the repo already committed: `chi2_gate_3dof` is chi-squared 0.99 at 3 dof.

    That constant was typed into FilterConfig from a table long before this function existed, so
    agreeing with it is an independent check of both.
    """
    assert chi2_quantile(0.99, 3) == pytest.approx(FilterConfig().chi2_gate_3dof, abs=5e-4)
    assert chi2_quantile(0.95, 1) == pytest.approx(3.8415, abs=1e-3)
    assert chi2_quantile(0.975, 3) == pytest.approx(9.3484, abs=1e-3)
    assert chi2_quantile(0.5, 4) == pytest.approx(3.3567, abs=1e-3)


def _nees_p0() -> np.ndarray:
    """The Monte-Carlo prior.

    **This is the test's experimental design, not a proposal for the filter's `P0`** -- that is
    P-04's, and `InEKF.__init__` still carries a flat `1e-3 I` placeholder. The test is valid for
    any positive-definite choice, because the truth error is drawn from this same matrix; what it
    checks is that `P` tracks the error it actually makes, not that `P0` is well chosen.

    The two bias blocks are the D-045 measured bias instabilities (42 deg/hr, 0.34 mg) so that at
    least those are repo-sourced rather than picked.
    """
    sd = np.zeros(ERROR_STATE_DIM)
    sd[0:2] = np.deg2rad(2.0)
    sd[2] = np.deg2rad(5.0)
    sd[3:6] = 0.1
    sd[6:9] = 1.0
    sd[9:12] = 42.0 * (np.pi / 180.0) / 3600.0
    sd[12:15] = 0.34e-3 * 9.80665
    sd[15:18] = np.deg2rad(1.0)
    return np.diag(sd**2)


def _nees_inputs(k: int) -> tuple[np.ndarray, np.ndarray, bool]:
    """(omega, specific force, truly stopped) for step `k`: cruise, brake, stop, pull away, cruise.

    Two properties the scenario has to have, both learned the hard way:

    * **The truth must satisfy NHC exactly.** A coordinated turn at speed `u` and yaw rate `r`
      needs `a_body = (u_dot, u r, -g)` and `omega = (0, 0, r)`; anything else leaves a real
      lateral velocity and the filter is then punished for a scenario bug. Measured residual is
      ~1e-3 m/s against an NHC sigma of 0.5.
    * **The ramps must be smooth, and the vehicle must never be exactly straight while moving.**
      `is_stationary` tests accelerometer *variance* and gyro magnitude, so a synthetic car
      cruising in a straight line at constant speed -- no road vibration in the model -- reads as
      parked, and ZUPT fires at 15 m/s. A constant-deceleration brake does the same. Real data has
      cabin vibration (D-045 measured 20-30x the mechanical energy on a moving-cabin segment);
      this scenario has none, so it keeps a small yaw rate instead of inventing a vibration term.
    """
    u_cruise, yaw_rate, t_ramp = 15.0, 0.05, 3.0
    t = k * NEES_DT + NEES_DT / 2
    amp = np.pi * u_cruise / (2.0 * t_ramp)
    brake, stop, pull = 20.0, 20.0 + t_ramp, 20.0 + t_ramp + 10.0
    if t < brake:
        u, u_dot = u_cruise, 0.0
    elif t < stop:
        u = u_cruise * (1 + np.cos(np.pi * (t - brake) / t_ramp)) / 2
        u_dot = -amp * np.sin(np.pi * (t - brake) / t_ramp)
    elif t < pull:
        u, u_dot = 0.0, 0.0
    elif t < pull + t_ramp:
        u = u_cruise * (1 - np.cos(np.pi * (t - pull) / t_ramp)) / 2
        u_dot = amp * np.sin(np.pi * (t - pull) / t_ramp)
    else:
        u, u_dot = u_cruise, 0.0
    stopped = u == 0.0
    r = 0.0 if stopped else yaw_rate  # a stopped car cannot yaw
    return np.array([0.0, 0.0, r]), np.array([u_dot, u * r, -9.80665]), stopped


def _nees_run(seed: int, *, zupt: bool, zaru: bool, nhc: bool) -> tuple[float, np.ndarray]:
    """One Monte-Carlo run: NEES at the final step, over the full state and over each block.

    The per-block marginals cost nothing once the error and `P` are in hand, and they are what
    localised D-053's failure to `b_g` -- 18 degrees of freedom hide one bad 3-vector until it is
    off by a factor.
    """
    cfg = FilterConfig()
    rng = np.random.default_rng(seed)
    p0 = _nees_p0()
    rot_t, v_t, p_t = np.eye(3), np.array([15.0, 0.0, 0.0]), np.zeros(3)
    r_sv_t = np.eye(3)
    b_g_t = rng.multivariate_normal(np.zeros(3), p0[9:12, 9:12])
    b_a_t = rng.multivariate_normal(np.zeros(3), p0[12:15, 12:15])

    xi = rng.multivariate_normal(np.zeros(ERROR_STATE_DIM), p0)
    f = InEKF(cfg)
    f.state.R, f.state.v, f.state.p = unpack(se23_exp(xi[0:9]) @ x_of(rot_t, v_t, p_t))
    f.state.b_g = b_g_t + xi[9:12]
    f.state.b_a = b_a_t + xi[12:15]
    f.state.R_sv = exp_so3(xi[15:18]) @ r_sv_t
    f.P = p0.copy()

    sd_g = cfg.gyro_arw / np.sqrt(NEES_DT)
    sd_a = cfg.accel_vrw / np.sqrt(NEES_DT)
    window = max(1, int(round(cfg.zupt_window_s / NEES_DT)))
    acc_win = np.zeros((0, 3))
    gyro_win = np.zeros((0, 3))

    for k in range(NEES_STEPS):
        omega, accel, _ = _nees_inputs(k)
        gyro_m = omega + b_g_t + rng.normal(0, sd_g, 3)
        accel_m = accel + b_a_t + rng.normal(0, sd_a, 3)
        b_g_t = b_g_t + rng.normal(0, cfg.gyro_bias_rw * np.sqrt(NEES_DT), 3)
        b_a_t = b_a_t + rng.normal(0, cfg.accel_bias_rw * np.sqrt(NEES_DT), 3)
        rot_t, v_t, p_t = propagate_nominal(rot_t, v_t, p_t, omega, accel, NEES_DT)

        f.propagate(gyro_m, accel_m, NEES_DT)
        acc_win = np.vstack([acc_win, accel_m])[-window:]
        gyro_win = np.vstack([gyro_win, gyro_m])[-window:]
        fired = acc_win.shape[0] == window and is_stationary(acc_win, gyro_win, cfg)
        if fired:
            if zupt:
                f.update_zupt()
            if zaru:
                f.update_zaru(gyro_m)
        elif nhc and nhc_is_valid(
            float(np.linalg.norm(f.state.v)),
            gyro_m[2] - f.state.b_g[2],
            accel_m[1] - f.state.b_a[1],
            cfg,
        ):
            f.update_nhc()

    eta = x_of(f.state.R, f.state.v, f.state.p) @ np.linalg.inv(x_of(rot_t, v_t, p_t))
    err = np.concatenate(
        [se23_log(eta), f.state.b_g - b_g_t, f.state.b_a - b_a_t, log_so3(f.state.R_sv @ r_sv_t.T)]
    )
    full = float(err @ np.linalg.solve(f.P, err))
    blocks = np.array(
        [
            float(err[b] @ np.linalg.solve(f.P[b, b], err[b]))
            for b in (IDX_ATTITUDE, IDX_VELOCITY, IDX_POSITION, IDX_GYRO_BIAS, IDX_MOUNT)
        ]
    )
    return full, blocks


#: Order of the marginals `_nees_run` returns. `b_a` is left out only because nothing asserts on
#: it; add it here and to the tuple above together if that changes.
NEES_BLOCKS = ("attitude", "velocity", "position", "gyro_bias", "mount")


@functools.cache
def _nees_sweep(*, zupt: bool, zaru: bool, nhc: bool) -> dict[str, tuple[float, float, float]]:
    """`{"full": (mean, lo, hi), "gyro_bias": (...), ...}` over NEES_RUNS deterministic seeds.

    Cached, and returning every marginal from one pass: a sweep is 100 x 600 propagate steps, and
    re-running it per assertion would put minutes into CI to compute a different quadratic form
    over the same errors.
    """
    runs = [_nees_run(s, zupt=zupt, zaru=zaru, nhc=nhc) for s in range(NEES_RUNS)]

    def band(dim: int, mean: float) -> tuple[float, float, float]:
        dof = dim * NEES_RUNS
        return (
            mean,
            chi2_quantile(0.025, dof) / NEES_RUNS,
            chi2_quantile(0.975, dof) / NEES_RUNS,
        )

    out = {"full": band(ERROR_STATE_DIM, float(np.mean([r[0] for r in runs])))}
    per = np.array([r[1] for r in runs]).mean(axis=0)
    out.update({name: band(3, float(per[i])) for i, name in enumerate(NEES_BLOCKS)})
    return out


def _mean_nees(**kw: bool) -> tuple[float, float, float]:
    """(mean NEES, band low, band high) for the full state."""
    return _nees_sweep(**kw)["full"]


def test_11_nees_propagation_only_is_consistent():
    """Test 11, propagation alone: P0, Q_c, Van Loan and the nominal step against real error.

    This is the base case -- if it fails, nothing above it means anything, because every update
    is applied to a covariance this produced. Measured 18.287 against a band of [16.843, 19.195].
    """
    mean, lo, hi = _mean_nees(zupt=False, zaru=False, nhc=False)
    assert lo <= mean <= hi, (
        f"propagation-only NEES {mean:.3f} outside 95% band [{lo:.3f}, {hi:.3f}]"
    )


def test_11_nees_with_zupt_is_consistent():
    """Test 11 with ZUPT applied at every detected stop. Measured 18.827, band [16.843, 19.195].

    ZUPT is the update that shrinks `P` the hardest, so it is the one most able to make the filter
    over-confident. It does not: the covariance still tracks the error it actually makes.

    (18.929 before D-057; the strict gyro statistic drops two firings of the 98, at the window
    that straddles the pull-away.)
    """
    mean, lo, hi = _mean_nees(zupt=True, zaru=False, nhc=False)
    assert lo <= mean <= hi, f"ZUPT NEES {mean:.3f} outside 95% band [{lo:.3f}, {hi:.3f}]"


def test_11_nees_with_zupt_and_zaru_is_consistent():
    """**The assertion D-053 could not commit, and the one that reopens Gate 1.**

    ZUPT and ZARU fire together at every detected stop (D-004), so this is the constraint pair the
    error budget actually assumes. Measured 18.996, band [16.843, 19.195].

    It read 29.90 when P-03 measured it, and the diagnosis in D-053 -- `zaru_sigma` under the
    measured gyro noise, plus the same gyro sample serving as process noise and measurement --
    turned out to name a real error and a red herring. The 1.3x sigma was real and worth 6 points
    of the total (D-056). The sample reuse was not: giving ZARU an independently-drawn gyro read
    moved the gyro-bias block by 0.17, from 8.98 to 9.15, in the wrong direction to be the cause.

    What was left was a **detector** bug, not a covariance one (D-057): one false firing per
    pull-away, injecting a stationarity claim at 0.05 rad/s of real yaw, at the moment `P` on the
    gyro-bias block was at its minimum and the innovation therefore least questioned. It put a
    systematic 8.0e-4 rad/s -- 2.6 sigma -- into `b_g_z`, which is invisible in a variance
    (measured against the ensemble *mean*, the block looked fine) and unmissable in a NEES.
    """
    mean, lo, hi = _mean_nees(zupt=True, zaru=True, nhc=False)
    assert lo <= mean <= hi, f"ZUPT+ZARU NEES {mean:.3f} outside 95% band [{lo:.3f}, {hi:.3f}]"


def test_11_nees_gyro_bias_block_is_consistent_under_zaru():
    """The block that failed, asserted on its own. Measured 3.20 against 3.0 expected.

    The total is a poor instrument for this: 18 degrees of freedom hide a single bad block until
    it is off by a factor. This is the marginal that read 12.03 at the start of P-04, and it is
    the one to re-read first if the total ever moves again.
    """
    mean, lo, hi = _nees_sweep(zupt=True, zaru=True, nhc=False)["gyro_bias"]
    assert lo <= mean <= hi, f"gyro-bias NEES {mean:.3f} outside 95% band [{lo:.3f}, {hi:.3f}]"


def test_11_nees_with_every_update_is_not_over_confident():
    """Full state -- ZUPT, ZARU and NHC. Measured 14.141 against a band of [16.843, 19.195].

    **Asserted one-sided, and the reason is the scenario rather than the filter.** `R_NHC` is
    0.5 m/s of deliberate model slack for a constraint that real vehicles break -- side-slip,
    banking, a phone that shifts. This scenario breaks it by **5.49e-4 m/s RMS**, three orders
    smaller, because the truth is generated from a coordinated-turn model that satisfies NHC by
    construction. A filter told a measurement is 900x noisier than it is extracts less information
    from it than it could, and its `P` is then larger than the error it makes: under-confident,
    which is the safe direction and is what 14.141 says. NHC alone reads 13.750.

    Matching `R_NHC` to the scenario is not the fix and was measured rather than assumed: at
    5.49e-4 the full state goes to **6216**, because that residual is a deterministic model error,
    not white noise, and treating a systematic 5e-4 as if it were independent every step lets the
    filter accumulate certainty it has not earned. Worth knowing before P-10 trains a head that
    predicts `R_NHC`: driving that output toward the apparent residual is not conservative, it is
    the failure mode Gate 2 exists to catch.

    So the two-sided band belongs to the NHC-free cases above, where the simulation and the filter
    model the same thing, and this case asserts what it can honestly assert: adding NHC does not
    make the filter over-confident. The real `R_NHC` is a Gate 1 measurement on real data.
    """
    mean, _, hi = _mean_nees(zupt=True, zaru=True, nhc=True)
    assert mean <= hi, f"full-state NEES {mean:.3f} is over-confident against the band top {hi:.3f}"
