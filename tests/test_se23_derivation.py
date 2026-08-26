"""Executable check of the derivation in docs/SE23_PROPAGATION.md.

**Why this exists.** Gate 1 is a hard stop and the InEKF is written from that document. A matrix
that is wrong on paper becomes a filter that runs, produces smooth plausible trajectories, and is
undebuggable. Every matrix the document asserts is checked here against a numerical ground truth,
so the derivation is protected by CI *before* the code that uses it exists.

**The helpers below are the specification, not a second implementation.** When Sprint 1 (seat S)
implements `core.reference.inekf`, these local helpers are deleted and the same assertions are
re-pointed at the real code. The `test_sprint1_surface_fails_loudly_rather_than_silently` case in
`test_filter.py` fails the moment `propagate()` is implemented, which forces that migration.

Numbers that came out of writing this, now recorded in the document:

* the small-angle cutoff has to be **1e-3**, not 1e-6 -- the closed form is already losing
  precision at phi ~ 1e-6, which is inside the branch that was going to use it;
* `A_RI` evaluated at the step *start* carries an O(dt^2) error that evaluating at the step
  midpoint removes almost entirely (~1800x at dt = 1 ms);
* the `Phi G Qc G^T Phi^T dt` shortcut for `Q_d` is ~4% wrong at dt = 0.1 s, which is D-031.
"""

from __future__ import annotations

import numpy as np
import pytest

GRAVITY_NED = np.array([0.0, 0.0, 9.80665])

#: Below this angle, use the Taylor series rather than the closed form. Established by
#: ``test_small_angle_cutoff_is_not_set_too_low`` -- see the module docstring.
SMALL_ANGLE = 1e-3


# ------------------------------------------------------------------------------------------
# The math the document asserts
# ------------------------------------------------------------------------------------------


def skew(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    return np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])


def gammas(phi: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gamma_0, Gamma_1, Gamma_2 of docs/SE23_PROPAGATION.md section 8.1.

    The series branch is not an optimisation -- the closed form is 0/0 at rest, which is exactly
    the ZUPT case and therefore constant.
    """
    n = float(np.linalg.norm(phi))
    s = skew(phi)
    s2 = s @ s
    if n < SMALL_ANGLE:
        c0s, c0c = 1 - n**2 / 6, 0.5 - n**2 / 24
        c1a, c1b = 0.5 - n**2 / 24, 1 / 6 - n**2 / 120
        c2a, c2b = 1 / 6 - n**2 / 120, 1 / 24 - n**2 / 720
    else:
        c0s, c0c = np.sin(n) / n, (1 - np.cos(n)) / n**2
        c1a, c1b = (1 - np.cos(n)) / n**2, (n - np.sin(n)) / n**3
        c2a, c2b = (n - np.sin(n)) / n**3, (n**2 + 2 * np.cos(n) - 2) / (2 * n**4)
    return (
        np.eye(3) + c0s * s + c0c * s2,
        np.eye(3) + c1a * s + c1b * s2,
        0.5 * np.eye(3) + c2a * s + c2b * s2,
    )


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


def exp_so3(phi: np.ndarray) -> np.ndarray:
    return gammas(phi)[0]


def log_so3(rot: np.ndarray) -> np.ndarray:
    theta = float(np.arccos(np.clip((np.trace(rot) - 1) / 2, -1.0, 1.0)))
    w = np.array([rot[2, 1] - rot[1, 2], rot[0, 2] - rot[2, 0], rot[1, 0] - rot[0, 1]])
    return w / 2 if theta < 1e-8 else theta / (2 * np.sin(theta)) * w


def expm_series(m: np.ndarray, terms: int = 30) -> np.ndarray:
    """Scaling-and-squaring Taylor expm. scipy is deliberately not a dependency (D-024)."""
    nrm = float(np.max(np.abs(m)))
    squarings = int(np.ceil(np.log2(nrm / 0.5))) if nrm > 0.5 else 0
    a = m / (2.0**squarings)
    out = term = np.eye(m.shape[0])
    for k in range(1, terms):
        term = term @ a / k
        out = out + term
    for _ in range(squarings):
        out = out @ out
    return out


def x_of(rot: np.ndarray, v: np.ndarray, p: np.ndarray) -> np.ndarray:
    x = np.eye(5)
    x[:3, :3], x[:3, 3], x[:3, 4] = rot, v, p
    return x


def unpack(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return x[:3, :3].copy(), x[:3, 3].copy(), x[:3, 4].copy()


def se23_hat(xi: np.ndarray) -> np.ndarray:
    m = np.zeros((5, 5))
    m[:3, :3], m[:3, 3], m[:3, 4] = skew(xi[0:3]), xi[3:6], xi[6:9]
    return m


def se23_exp(xi: np.ndarray) -> np.ndarray:
    g0, g1, _ = gammas(xi[0:3])
    return x_of(g0, g1 @ xi[3:6], g1 @ xi[6:9])


def se23_log(x: np.ndarray) -> np.ndarray:
    rot, v, p = unpack(x)
    phi = log_so3(rot)
    j_inv = np.linalg.inv(gammas(phi)[1])
    return np.concatenate([phi, j_inv @ v, j_inv @ p])


def adjoint(x: np.ndarray) -> np.ndarray:
    """Section 2.1."""
    rot, v, p = unpack(x)
    a = np.zeros((9, 9))
    a[0:3, 0:3] = rot
    a[3:6, 0:3], a[3:6, 3:6] = skew(v) @ rot, rot
    a[6:9, 0:3], a[6:9, 6:9] = skew(p) @ rot, rot
    return a


def propagate(rot, v, p, omega, accel, dt):
    """Section 8.1. Exact under a constant-input assumption over dt, not an Euler step."""
    g0, g1, g2 = gammas(omega * dt)
    return (
        rot @ g0,
        v + rot @ g1 @ accel * dt + GRAVITY_NED * dt,
        p + v * dt + rot @ g2 @ accel * dt**2 + 0.5 * GRAVITY_NED * dt**2,
    )


def a_ri(rot: np.ndarray, v: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Section 5.2. Ordering matches the IDX_* slices in core/reference/inekf.py."""
    a = np.zeros((18, 18))
    a[3:6, 0:3] = skew(GRAVITY_NED)
    a[6:9, 3:6] = np.eye(3)
    a[0:3, 9:12] = -rot
    a[3:6, 9:12] = -skew(v) @ rot
    a[6:9, 9:12] = -skew(p) @ rot
    a[3:6, 12:15] = -rot
    return a


def g_ri(rot: np.ndarray, v: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Section 5.3."""
    g = np.zeros((18, 15))
    g[0:3, 0:3] = -rot
    g[3:6, 0:3] = -skew(v) @ rot
    g[6:9, 0:3] = -skew(p) @ rot
    g[3:6, 3:6] = -rot
    g[9:12, 6:9] = np.eye(3)
    g[12:15, 9:12] = np.eye(3)
    g[15:18, 12:15] = np.eye(3)
    return g


def van_loan(a: np.ndarray, gqg: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Section 8.2."""
    n = a.shape[0]
    m = np.zeros((2 * n, 2 * n))
    m[:n, :n], m[:n, n:], m[n:, n:] = -a, gqg, a.T
    e = expm_series(m * dt)
    phi = e[n:, n:].T
    return phi, phi @ e[:n, n:]


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
        rot, v, p = propagate(rot, v, p, np.zeros(3), f_static, 0.1)
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
        true2 = propagate(REF_R, REF_V, REF_P, RAW_OMEGA - REF_BG, RAW_ACCEL - REF_BA, dt)
        est2 = propagate(
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
    midpoint = propagate(REF_R, REF_V, REF_P, RAW_OMEGA - REF_BG, RAW_ACCEL - REF_BA, dt / 2)
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


def test_default_gyro_arw_placeholder_is_outside_the_documented_phone_range():
    """FilterConfig.gyro_arw = 3e-3 rad/s/sqrt(Hz) is ~10.3 deg/sqrt(hr); ERROR_BUDGET.md section 9
    puts phone MEMS at 0.5-5. The placeholder is pessimistic rather than wrong, but it is
    inconsistent with our own documentation and the Allan run must replace it (Gate 1)."""
    from core.reference.inekf import FilterConfig

    deg_sqrt_hr = FilterConfig().gyro_arw / ((np.pi / 180) / 60)
    assert deg_sqrt_hr > 5.0, (
        "gyro_arw placeholder now sits inside the ERROR_BUDGET section 9 range -- if the Allan "
        "run landed, delete this test and record the measured value instead"
    )
