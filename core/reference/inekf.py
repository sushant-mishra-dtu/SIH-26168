"""Reference InEKF on SE_2(3) -- state layout, gating, and interfaces.

**This is the screening prototype.** The C++/Rust core (DECISION_LOG D-011) mirrors this file
exactly and reuses its tests; the Python version exists so Gate 1 can be hit inside the compressed
schedule, not to replace the compiled core.

Propagation (P-02) and the update family (P-03) are implemented; the learned speed
pseudo-measurement is Sprint 2 and is still a placeholder that raises. The parts that were settled
before any of it was written -- the state layout, the constraint gating conditions, and the rule
that GNSS is never a mode switch -- are unchanged, because they are what is easy to get quietly
wrong later.

Background: docs/GLOSSARY.md (InEKF, NHC, ZUPT, ZARU), docs/ERROR_BUDGET.md (why yaw dominates).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------------------------
# State layout
#
# The nominal state lives on SE_2(3) x R^6 x SO(3):
#     R    attitude          (3x3 rotation, navigation <- body)
#     v    velocity          (3,)  NED
#     p    position          (3,)  NED
#     b_g  gyro bias         (3,)
#     b_a  accel bias        (3,)
#     R_sv phone -> vehicle  (3x3 rotation)
#
# The *error* state is the 18-vector indexed below. Error-state, not total-state: the small
# quantity is the one being linearised, which is what keeps the filter numerically sane.
# --------------------------------------------------------------------------------------------

IDX_ATTITUDE = slice(0, 3)
IDX_VELOCITY = slice(3, 6)
IDX_POSITION = slice(6, 9)
IDX_GYRO_BIAS = slice(9, 12)
IDX_ACCEL_BIAS = slice(12, 15)
IDX_MOUNT = slice(15, 18)  # small-angle error on R_sv
ERROR_STATE_DIM = 18

GRAVITY_NED = np.array([0.0, 0.0, 9.80665])

#: Below this angle the Gamma functions use their Taylor series rather than the closed form.
#: **1e-3, not 1e-6** (D-032): the guard has to sit where the closed form is still accurate, not
#: where it finally divides by zero. Sweeping the exact identities `Gamma_0 = I + phi^ Gamma_1`
#: and `Gamma_1 = I + phi^ Gamma_2` puts the worst residual at phi ~ 1.2e-6, which a 1e-6 cutoff
#: would route to the closed form -- the branch that is already degraded there.
SMALL_ANGLE = 1e-3

#: Re-project R onto SO(3) this often (docs/SE23_PROPAGATION.md section 8.1). Float drift off the
#: group is slow but not zero, and a non-orthonormal R makes R.T stop being R^-1 in every Jacobian.
REORTHONORMALISE_EVERY = 1000


# --------------------------------------------------------------------------------------------
# SE_2(3) group operations
#
# Transcribed from docs/SE23_PROPAGATION.md, which is checked against numerical ground truth in
# tests/test_se23_derivation.py. These lived in that test file as "the specification" until the
# filter existed; the tests now assert against these, so there is one implementation, not two.
# --------------------------------------------------------------------------------------------


def skew(a: np.ndarray) -> np.ndarray:
    """The hat map: `skew(a) @ b == np.cross(a, b)`."""
    a = np.asarray(a, dtype=float)
    return np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])


def gammas(phi: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gamma_0, Gamma_1, Gamma_2 of docs/SE23_PROPAGATION.md section 8.1.

    The series branch is not an optimisation. The closed forms carry 1/phi^3 and 1/phi^4
    coefficients that are 0/0 at rest -- which is the ZUPT case, and therefore constant.
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


def exp_so3(phi: np.ndarray) -> np.ndarray:
    """Rodrigues. Gamma_0 *is* the SO(3) exponential."""
    return gammas(phi)[0]


def log_so3(rot: np.ndarray) -> np.ndarray:
    theta = float(np.arccos(np.clip((np.trace(rot) - 1) / 2, -1.0, 1.0)))
    w = np.array([rot[2, 1] - rot[1, 2], rot[0, 2] - rot[2, 0], rot[1, 0] - rot[0, 1]])
    return w / 2 if theta < 1e-8 else theta / (2 * np.sin(theta)) * w


def expm_series(m: np.ndarray, terms: int = 30) -> np.ndarray:
    """Scaling-and-squaring Taylor matrix exponential.

    scipy is deliberately not a dependency (D-024): the harness is the critical path and must not
    block on an install. This is the one linear-algebra primitive numpy does not ship.
    """
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


def orthonormalise(rot: np.ndarray) -> np.ndarray:
    """Nearest rotation matrix in the Frobenius sense, with the reflection branch excluded."""
    u, _, vt = np.linalg.svd(rot)
    if np.linalg.det(u @ vt) < 0:
        u = u.copy()
        u[:, -1] *= -1
    return u @ vt


def x_of(rot: np.ndarray, v: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Pack (R, v, p) into the 5x5 SE_2(3) matrix of section 2."""
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
    """Section 2.1. Used by the GNSS update to move a left-invariant observation into the
    right-invariant convention the covariance is carried in (D-028)."""
    rot, v, p = unpack(x)
    a = np.zeros((9, 9))
    a[0:3, 0:3] = rot
    a[3:6, 0:3], a[3:6, 3:6] = skew(v) @ rot, rot
    a[6:9, 0:3], a[6:9, 6:9] = skew(p) @ rot, rot
    return a


def propagate_nominal(
    rot: np.ndarray, v: np.ndarray, p: np.ndarray, omega: np.ndarray, accel: np.ndarray, dt: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Section 8.1. Exact under a constant-input assumption over dt, **not** an Euler step (D-029).

    `omega` and `accel` are already bias-corrected. `accel` is specific force in the body frame;
    gravity is added in the navigation frame, so a level phone at rest reading `-GRAVITY_NED`
    cancels to exactly zero -- which is what makes SE_2(3) test 2 a gravity-sign check.

    At 10 Hz and 0.6 rad/s the Gamma_1 correction is ~3% of the velocity increment, and it is
    rotation-direction-dependent, so it does not average out over the 1800 steps of a 180 s
    outage. It is systematic heading-correlated drift, which the error budget has no room for.
    """
    g0, g1, g2 = gammas(omega * dt)
    return (
        rot @ g0,
        v + rot @ g1 @ accel * dt + GRAVITY_NED * dt,
        p + v * dt + rot @ g2 @ accel * dt**2 + 0.5 * GRAVITY_NED * dt**2,
    )


@dataclass
class FilterConfig:
    """Tuning. Process noise is seeded from a measured Allan-variance run, never guessed.

    The four noise defaults are **measured**, from IO-VNBD's own stationary segments (D-045), by
    `eval/allan.py`. They are the worst axis across the two segments quiet enough to characterise
    a sensor on -- `S-T2[31422:36490]` (507 s) and `S-T7[47809:52285]` (448 s) -- because an
    undersized Q makes the filter over-trust its own propagation and reject good measurements at
    the chi-squared gate, and that failure reads as a sensor fault rather than a tuning error.

    Regenerate with::

        python -m eval.allan --paths-from <list of S- csv paths> --out-dir eval/figures

    The measured `gyro_arw` is 1.41 deg/sqrt(hr), inside the 0.5-5 deg/sqrt(hr) phone-MEMS range
    in docs/ERROR_BUDGET.md section 9. It replaces a 3.0e-3 placeholder that was 10.3 deg/sqrt(hr)
    -- 7x pessimistic and outside our own stated range (plan item R-2, self-flagged in
    SE23_PROPAGATION.md section 10).
    """

    # Allan-variance-derived, per docs/ERROR_BUDGET.md section 9. Measured on IO-VNBD, not assumed.
    gyro_arw: float = 4.11e-4  # rad/s/sqrt(Hz)  == 1.41 deg/sqrt(hr)
    accel_vrw: float = 7.46e-3  # m/s^2/sqrt(Hz) == 0.45 m/s/sqrt(hr)

    # Not measured: a 507 s record cannot resolve the +1/2 rate-random-walk slope (it reaches
    # tau = 51 s). Derived instead from the two quantities that *were* measured, by modelling each
    # bias as first-order Gauss-Markov with steady-state spread B and correlation time tau_c taken
    # from the Allan minimum: q = B sqrt(2 / tau_c). A modelling choice, labelled as one, and the
    # conservative direction. See eval.allan.gauss_markov_bias_driving_noise and D-045.
    gyro_bias_rw: float = 5.48e-5  # rad/s^2/sqrt(Hz), from B = 42 deg/hr, tau_c = 27.7 s
    accel_bias_rw: float = 1.04e-3  # m/s^3/sqrt(Hz), from B = 0.34 mg, tau_c = 20.3 s

    # Mount-rotation process noise, the sigma_sv block of Q_c in SE23_PROPAGATION.md section 5.3.
    # **Zero, and deliberately so** (D-048): the derivation names the term but no source in the
    # repo gives it a magnitude, and inventing one would be a guessed number inside the covariance
    # every downstream chi-squared gate reads. Zero states the model actually in force here -- the
    # mount is rigid -- rather than dressing a guess up as a measurement. P-11 owns both the value
    # and the bump-detector re-inflation that makes a non-zero one meaningful.
    mount_rw: float = 0.0  # rad/s/sqrt(Hz)

    # NHC: lateral and vertical body velocity are ~0. Loose defaults; the AI-IMU CNN replaces
    # these with a per-step prediction once seat M's adaptive head lands (D-005).
    nhc_sigma_lateral: float = 0.5  # m/s
    nhc_sigma_vertical: float = 0.5  # m/s

    zupt_sigma: float = 0.02  # m/s

    #: Nominal IMU sample rate. Measured, not nominal-by-assumption: the `S-` stream's median
    #: sample interval is 100.0 ms (docs/ERROR_BUDGET.md section 9.1, the same timestamps the Allan
    #: run was computed on). The 200 Hz FOG edge build sets this and every rate-dependent quantity
    #: below follows -- which is the reason they are derived here rather than typed in.
    imu_rate_hz: float = 10.0

    # ---- P0, per block. Every entry names its source; see initial_covariance() and D-055. ----

    #: Horizontal and vertical position sigma at initialisation, metres. The protocol's stated
    #: GNSS accuracy (docs/EVALUATION.md section 2, +-3 m). **That figure is the VBOX reference
    #: receiver's, and the `S-` phone fix the filter actually initialises on is worse** -- which is
    #: the over-tight direction R-3 warns about. The fix carries its own `gps_accuracy_m`, which is
    #: on the loader's allowlist, so pass it: `initial_covariance(cfg, gnss_sigma_m=...)`. This
    #: default is the value in force when nobody does, and it is an assumption, not a measurement.
    init_position_sigma: float = 3.0  # m

    #: Initial heading sigma. **Not measured anywhere in this repo** (D-055): no code here
    #: initialises yaw, so there is no initialiser spread to quote. 5 degrees is the magnitude
    #: docs/ERROR_BUDGET.md section 5 sizes as a plausible-but-costly heading error (87 m over the
    #: 60 s reference outage), and an initial NED-yaw error costs exactly what a mount error of the
    #: same size costs -- section 5's `e_lat = v t delta` is the same equation. A judgement call,
    #: logged as one, and deliberately on the loose side: too tight here rejects the GNSS fixes
    #: that would have corrected it.
    init_yaw_sigma: float = np.deg2rad(5.0)  # rad

    #: Initial mount-angle sigma, all three axes. Same source and same 5 degrees
    #: (docs/ERROR_BUDGET.md section 5, the knock the mount-disturbance detector exists to catch).
    #: R_sv starts *unknown* -- D-006 makes the PCA fit an initialiser, not a calibration, and its
    #: spread has never been measured -- so this block must start loose enough for NHC to do the
    #: work. SE_2(3) test 9 measures that it can: 0.660 / 0.220 / 0.132 degrees residual after
    #: 300 NHC updates at 5 / 15 / 25 m/s. P-11 replaces this with the initialiser's own spread.
    init_mount_sigma: float = np.deg2rad(5.0)  # rad

    #: Bias instabilities, measured on IO-VNBD (D-045, docs/ERROR_BUDGET.md section 9.1). Used for
    #: the two bias blocks of P0: at a cold start the bias is unknown to its own stability.
    gyro_bias_instability: float = 2.04e-4  # rad/s   == 42 deg/hr, gyro_yaw, S-T7
    accel_bias_instability: float = 3.32e-3  # m/s^2  == 0.34 mg,   accel_x, S-T7

    # Stationary detection. Thresholds are conservative on purpose: a missed ZUPT costs a little
    # accuracy, a false ZUPT while rolling injects a hard error the filter believes.
    zupt_accel_var_thresh: float = 0.05  # (m/s^2)^2
    zupt_gyro_norm_thresh: float = 0.02  # rad/s
    zupt_window_s: float = 0.5

    # chi-squared gate at 3 DOF, 99% -- the only thing standing between the filter and a
    # multipath fix on tunnel exit.
    chi2_gate_3dof: float = 11.345

    # NHC must be gated OFF during these. An ungated NHC through a slip is worse than no NHC.
    nhc_max_yaw_rate: float = 0.6  # rad/s -- hard cornering
    nhc_max_lateral_accel: float = 4.0  # m/s^2 -- approaching slip
    nhc_min_speed: float = 1.0  # m/s -- below this, direction of travel is ill-defined

    mount_disturbance_gyro_thresh: float = 3.0  # rad/s of high-frequency energy

    # ---- Derived, not free. Each one below is a measured quantity re-expressed, and none of
    # them is a knob: changing a value here means changing `gyro_arw`, `accel_vrw` or
    # `imu_rate_hz`, which are what the Allan run and the timestamps measured. That is deliberate.
    # D-053's failure mode was an `R` that had been typed in and then read as if it were measured.

    @property
    def gyro_noise_sigma(self) -> float:
        """White noise on **one** gyro sample, rad/s. `ARW / sqrt(dt)` at the nominal rate."""
        return self.gyro_arw * np.sqrt(self.imu_rate_hz)

    @property
    def accel_noise_sigma(self) -> float:
        """White noise on one accelerometer sample, m/s^2."""
        return self.accel_vrw * np.sqrt(self.imu_rate_hz)

    @property
    def zaru_sigma(self) -> float:
        """ZARU measurement noise, rad/s. **Exactly the gyro white noise, and not a free choice.**

        Section 7.3's innovation is `z = w~ - b_g_hat`: at a true standstill the raw sample *is*
        the bias plus one sample of white noise, so this `R` is that noise and nothing else.
        1.30e-3 rad/s at 10 Hz. It replaces a hand-set 1.0e-3 that predated the Allan run and was
        1.3x under it in sigma, 1.7x in variance -- over-confident, the unsafe direction (D-056).
        """
        return self.gyro_noise_sigma

    @property
    def init_tilt_sigma(self) -> float:
        """Initial roll/pitch sigma, rad. Derived: one-sample gravity levelling, `sigma_a / g`.

        2.41e-3 rad (0.138 deg) at 10 Hz. Levelling is only valid at a standstill, which is where
        the filter aligns; it is also the case where the accelerometer reads gravity and nothing
        else. Conservative in that it uses a single sample rather than the ZUPT window's average.
        """
        return self.accel_noise_sigma / float(GRAVITY_NED[2])


@dataclass
class NavState:
    """Nominal state. Covariance is carried separately as an 18x18 on the error state."""

    R: np.ndarray = field(default_factory=lambda: np.eye(3))
    v: np.ndarray = field(default_factory=lambda: np.zeros(3))
    p: np.ndarray = field(default_factory=lambda: np.zeros(3))
    b_g: np.ndarray = field(default_factory=lambda: np.zeros(3))
    b_a: np.ndarray = field(default_factory=lambda: np.zeros(3))
    R_sv: np.ndarray = field(default_factory=lambda: np.eye(3))

    @property
    def yaw(self) -> float:
        """Heading in radians. The quantity the whole error budget turns on."""
        return float(np.arctan2(self.R[1, 0], self.R[0, 0]))


# --------------------------------------------------------------------------------------------
# Linearised error dynamics and discrete covariance
# --------------------------------------------------------------------------------------------


def a_ri(rot: np.ndarray, v: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Right-invariant error-state matrix, section 5.2. Ordering matches the IDX_* slices above.

    Read the top-left 9x9: `skew(g)` and `I`, and nothing else. No R, no v, no omega, no a. That
    block is the same matrix on a straight motorway and mid-roundabout, at any heading, however
    wrong the current attitude estimate is -- which is the entire reason for carrying the
    right-invariant error (D-002, D-028). Every state dependence sits in the bias columns.
    """
    a = np.zeros((ERROR_STATE_DIM, ERROR_STATE_DIM))
    a[IDX_VELOCITY, IDX_ATTITUDE] = skew(GRAVITY_NED)
    a[IDX_POSITION, IDX_VELOCITY] = np.eye(3)
    a[IDX_ATTITUDE, IDX_GYRO_BIAS] = -rot
    a[IDX_VELOCITY, IDX_GYRO_BIAS] = -skew(v) @ rot
    a[IDX_POSITION, IDX_GYRO_BIAS] = -skew(p) @ rot
    a[IDX_VELOCITY, IDX_ACCEL_BIAS] = -rot
    return a


def g_ri(rot: np.ndarray, v: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Noise mapping, section 5.3. Columns are `[w_g, w_a, w_bg, w_ba, w_sv]`, 15 wide.

    Process noise enters exactly where the bias errors do -- same algebra, `w_g` in place of
    `delta b_g`.
    """
    g = np.zeros((ERROR_STATE_DIM, 15))
    g[IDX_ATTITUDE, 0:3] = -rot
    g[IDX_VELOCITY, 0:3] = -skew(v) @ rot
    g[IDX_POSITION, 0:3] = -skew(p) @ rot
    g[IDX_VELOCITY, 3:6] = -rot
    g[IDX_GYRO_BIAS, 6:9] = np.eye(3)
    g[IDX_ACCEL_BIAS, 9:12] = np.eye(3)
    g[IDX_MOUNT, 12:15] = np.eye(3)
    return g


def process_noise_psd(cfg: FilterConfig) -> np.ndarray:
    """Continuous-time `Q_c`, section 5.3: `diag(sigma_g^2, sigma_a^2, sigma_bg^2, sigma_ba^2,
    sigma_sv^2)`, each repeated three times.

    Every value is read from `FilterConfig`, which carries the D-045 measured Allan coefficients.
    Nothing here is retyped from a document: `gyro_arw` and `accel_vrw` trace to
    `eval/figures/allan_coefficients.csv` (worst axis, `gyro_pitch` on S-T2 and `accel_z` on S-T7)
    and the two bias driving noises are the *derived* Gauss-Markov quantities, labelled as derived
    in ERROR_BUDGET.md section 9.1 and everywhere they appear.

    Units are PSD amplitudes squared. A factor-of-60 slip between deg/sqrt(hr) and rad/s/sqrt(Hz)
    is invisible -- the filter still runs, with a confidence wrong by 3600x in variance -- so the
    conversion happens once, at the config boundary, and never here.
    """
    return np.diag(
        np.concatenate(
            [
                np.full(3, cfg.gyro_arw**2),
                np.full(3, cfg.accel_vrw**2),
                np.full(3, cfg.gyro_bias_rw**2),
                np.full(3, cfg.accel_bias_rw**2),
                np.full(3, cfg.mount_rw**2),
            ]
        )
    )


def van_loan(a: np.ndarray, gqg: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Discrete transition and process noise by Van Loan's method, section 8.2 (D-031).

    Returns `(Phi, Q_d)`. The `Phi G Q_c G^T Phi^T dt` shortcut is ~4.2% wrong at dt = 0.1 s at
    our own noise values, and it is wrong by *misallocating* noise between the position and
    velocity blocks. An under-sized Q makes the filter reject good measurements at the chi-squared
    gate, and that failure reads as a sensor problem rather than as a tuning one.

    One 36x36 `expm` per step, which is the identified hotspot for the October C++ port (D-022).
    """
    n = a.shape[0]
    m = np.zeros((2 * n, 2 * n))
    m[:n, :n], m[:n, n:], m[n:, n:] = -a, gqg, a.T
    e = expm_series(m * dt)
    phi = e[n:, n:].T
    return phi, phi @ e[:n, n:]


# --------------------------------------------------------------------------------------------
# Detectors -- implemented, because they are simple and everything else depends on them
# --------------------------------------------------------------------------------------------


def is_stationary(accel_window: np.ndarray, gyro_window: np.ndarray, cfg: FilterConfig) -> bool:
    """Detect a stopped vehicle for ZUPT/ZARU.

    Both conditions must hold: low accelerometer variance *and* low gyro magnitude. Variance
    rather than magnitude on the accelerometer because gravity dominates its magnitude at all
    times; a stationary phone still reads ~9.8 m/s^2.

    The gyro condition is the window's **maximum** sample magnitude, not its mean (D-057). A mean
    lets one sample of real rotation be diluted by the rest of the window: at 10 Hz with the 0.5 s
    window, a car pulling away at 0.05 rad/s reads as `(4 x 0.0015 + 0.05) / 5 = 0.011` rad/s,
    under the 0.02 threshold, and fires ZUPT *and* ZARU while the vehicle is turning. Measured, in
    the reference scenario: exactly one such firing per pull-away, and because it lands where the
    stop has just driven `P` on the gyro-bias block to its minimum, it puts a **systematic
    8.0e-4 rad/s** into `b_g_z` -- 2.6 sigma of the block's own spread, and the whole of the
    29.90 NEES that blocked Gate 1 (D-053, D-057). The accelerometer half does not catch it: a
    smooth pull-away has no acceleration step to see.

    The asymmetry this file already states is the reason to prefer the strict statistic: a missed
    stop costs a little accuracy, a false one injects a confident wrong measurement that the
    filter believes. Both D-045 segments sit an order of magnitude inside these thresholds
    (docs/ERROR_BUDGET.md section 9.2), so the margin is there to spend.
    """
    accel_window = np.asarray(accel_window, dtype=float)
    gyro_window = np.asarray(gyro_window, dtype=float)
    if accel_window.ndim != 2 or accel_window.shape[1] != 3:
        raise ValueError(f"expected (n, 3) accel window, got {accel_window.shape}")

    accel_var = float(np.mean(np.var(accel_window, axis=0)))
    gyro_norm = float(np.max(np.linalg.norm(gyro_window, axis=1)))
    return accel_var < cfg.zupt_accel_var_thresh and gyro_norm < cfg.zupt_gyro_norm_thresh


def nhc_is_valid(
    speed_mps: float, yaw_rate: float, lateral_accel: float, cfg: FilterConfig
) -> bool:
    """Whether the non-holonomic constraint may be applied this step.

    NHC says the vehicle cannot move sideways. That is true of a car tracking its tyres and false
    of one sliding, drifting, or reversing -- and it is meaningless at a standstill, where there is
    no direction of travel to be lateral to. Applying it anyway injects a confident wrong
    measurement, which is strictly worse than applying nothing.
    """
    if speed_mps < cfg.nhc_min_speed:
        return False
    if abs(yaw_rate) > cfg.nhc_max_yaw_rate:
        return False
    if abs(lateral_accel) > cfg.nhc_max_lateral_accel:
        return False
    return True


def chi2_gate(innovation: np.ndarray, innovation_cov: np.ndarray, threshold: float) -> bool:
    """Mahalanobis gate. True means *accept* the measurement.

    This single function is what makes GNSS optional rather than a mode. Inside a tunnel nothing
    passes, so nothing is applied, and there is no branch to switch -- which is precisely why the
    "seamless transition within milliseconds" requirement is met by construction (D-001).
    """
    innovation = np.asarray(innovation, dtype=float).ravel()
    try:
        d2 = float(innovation @ np.linalg.solve(innovation_cov, innovation))
    except np.linalg.LinAlgError:
        return False  # singular covariance: reject rather than trust
    return d2 <= threshold


def detect_mount_disturbance(gyro_window: np.ndarray, cfg: FilterConfig) -> bool:
    """Detect the phone being knocked, so R_sv covariance can be re-inflated.

    A 5-degree mount shift costs ~87 m over a 60 s outage (docs/ERROR_BUDGET.md section 5), and it
    is silent -- nothing else in the system notices.
    """
    gyro_window = np.asarray(gyro_window, dtype=float)
    if gyro_window.shape[0] < 2:
        return False
    high_freq = np.diff(gyro_window, axis=0)
    return bool(np.max(np.linalg.norm(high_freq, axis=1)) > cfg.mount_disturbance_gyro_thresh)


# --------------------------------------------------------------------------------------------
# Initial covariance
# --------------------------------------------------------------------------------------------


def initial_covariance(cfg: FilterConfig, *, gnss_sigma_m: float | None = None) -> np.ndarray:
    """`P0`, per block, with every entry traceable to a source (R-3, D-055).

    The flat `1e-3 I` this replaces was wrong in all six blocks and wrong in *both* directions at
    once -- 3.2 cm on position, 1.8 deg/s on gyro bias (155x looser than the 42 deg/hr the Allan
    run measured), 1.8 deg on a mount angle that starts unknown. A wrong `P0` is not a cosmetic
    problem: it is read by the chi-squared gate, so a too-tight one makes the filter reject good
    fixes, and that failure presents as a sensor fault rather than as a tuning error.

    ==============  ==========================  =============================================
    Block           sigma                       Source
    ==============  ==========================  =============================================
    attitude r/p    `cfg.init_tilt_sigma`       derived: one-sample levelling, `sigma_a / g`
    attitude yaw    `cfg.init_yaw_sigma`        ERROR_BUDGET section 5 -- judgement call, D-055
    velocity        `cfg.zupt_sigma`            the filter aligns at a detected standstill, and
                                                that is exactly what ZUPT asserts there
    position        `gnss_sigma_m` or the       EVALUATION.md section 2 -- assumption, D-055
                    `cfg.init_position_sigma`
    gyro bias       `cfg.gyro_bias_instability` D-045, measured: 42 deg/hr
    accel bias      `cfg.accel_bias_instability` D-045, measured: 0.34 mg
    mount           `cfg.init_mount_sigma`      ERROR_BUDGET section 5 -- judgement call, D-055
    ==============  ==========================  =============================================

    `gnss_sigma_m` is the initialising fix's own reported accuracy (`gps_accuracy_m`, on the
    loader's allowlist). **Pass it.** The config default is the protocol's GNSS figure, which is
    the VBOX reference receiver's rather than the phone's, and is therefore optimistic.

    Two entries above are judgement calls rather than measurements, and both are on the loose
    side by choice: nothing in this repo initialises heading, and D-006 makes the PCA fit an
    initialiser whose spread nobody has measured. Loose costs convergence time, which NHC and
    GNSS buy back; tight costs rejected measurements, which nothing buys back.
    """
    sd = np.zeros(ERROR_STATE_DIM)
    sd[0:2] = cfg.init_tilt_sigma  # roll, pitch -- observable from gravity at a standstill
    sd[2] = cfg.init_yaw_sigma  # yaw -- not observable from the IMU at all
    sd[IDX_VELOCITY] = cfg.zupt_sigma
    sd[IDX_POSITION] = cfg.init_position_sigma if gnss_sigma_m is None else float(gnss_sigma_m)
    sd[IDX_GYRO_BIAS] = cfg.gyro_bias_instability
    sd[IDX_ACCEL_BIAS] = cfg.accel_bias_instability
    sd[IDX_MOUNT] = cfg.init_mount_sigma
    if (sd <= 0).any():
        raise ValueError("every P0 sigma must be positive; a zero block cannot be corrected")
    return np.diag(sd**2)


# --------------------------------------------------------------------------------------------
# Filter -- Sprint 1
# --------------------------------------------------------------------------------------------


class InEKF:
    """Error-state Invariant EKF on SE_2(3).

    Sprint 1 (seat S) implements propagate() and the update family. The interface was fixed before
    the implementation so that seat D could wire the harness against it and seat A could agree the
    FFI surface without waiting.

    **Gating is the caller's job, not this class's.** `is_stationary` and `nhc_is_valid` read the
    raw IMU stream -- accelerometer variance, gyro magnitude, yaw rate, lateral acceleration --
    and none of those is a property of the state, so the filter cannot check them for itself. The
    harness calls the detector, then the update. ZUPT and ZARU fire **together** at every detected
    stop: a stop where only one runs is a bug, not a tuning choice.
    """

    def __init__(self, cfg: FilterConfig | None = None, p0: np.ndarray | None = None) -> None:
        self.cfg = cfg or FilterConfig()
        self.state = NavState()
        #: `P0` per block (D-055). `p0` overrides it for a caller that knows better -- the harness
        #: initialising on a fix whose reported accuracy it has, or a Monte-Carlo drawing its own
        #: prior. See `initial_covariance`.
        self.P = initial_covariance(self.cfg) if p0 is None else np.asarray(p0, dtype=float)
        if self.P.shape != (ERROR_STATE_DIM, ERROR_STATE_DIM):
            raise ValueError(f"P0 must be {ERROR_STATE_DIM}x{ERROR_STATE_DIM}, got {self.P.shape}")
        #: Steps since the last re-projection of R onto SO(3). See REORTHONORMALISE_EVERY.
        self.steps = 0

    def propagate(self, gyro: np.ndarray, accel: np.ndarray, dt: float) -> None:
        """IMU propagation. Always runs, GNSS or not -- this is the spine.

        `dt` comes from real timestamps. Never a nominal value: sensor timestamps jitter and
        batch, and assuming 1/100 s silently integrates the wrong interval (D-013).

        Section 8.1 for the nominal step, 8.2 for the covariance. Three things the derivation
        insists on, each with a decision behind it:

        * the exact Gamma_0/Gamma_1/Gamma_2 closed form, not an Euler step (D-029);
        * `A_RI` evaluated at the step **midpoint**, not at the interval start (D-029) -- the
          bias-coupling columns carry `skew(v) @ R` and `skew(p) @ R`, both of which move during
          the step, so evaluating at the start leaves an O(dt^2) error that the midpoint removes
          almost entirely (~1800x at dt = 1 ms);
        * `Q_d` by Van Loan, not the `Phi G Q_c G^T Phi^T dt` shortcut (D-031).
        """
        gyro = np.asarray(gyro, dtype=float).ravel()
        accel = np.asarray(accel, dtype=float).ravel()
        if gyro.shape != (3,) or accel.shape != (3,):
            raise ValueError(f"expected 3-vectors, got gyro {gyro.shape}, accel {accel.shape}")
        if not np.isfinite(gyro).all() or not np.isfinite(accel).all():
            raise ValueError("non-finite IMU sample -- fix the loader, do not propagate through it")
        if dt <= 0:
            raise ValueError(
                f"dt must be positive, got {dt}. A non-positive interval means the timestamps "
                "went backwards; five IO-VNBD S- files restart their clock mid-recording, and "
                "propagating through one integrates the wrong interval silently."
            )

        s = self.state
        omega = gyro - s.b_g
        specific_force = accel - s.b_a

        # Linearise at the midpoint (D-029). A and G share the linearisation point: Van Loan's
        # block matrix mixes them, so evaluating them at different states would be inconsistent.
        mid_rot, mid_v, mid_p = propagate_nominal(s.R, s.v, s.p, omega, specific_force, dt / 2)
        a = a_ri(mid_rot, mid_v, mid_p)
        g = g_ri(mid_rot, mid_v, mid_p)
        gqg = g @ process_noise_psd(self.cfg) @ g.T

        phi, q_d = van_loan(a, gqg, dt)

        s.R, s.v, s.p = propagate_nominal(s.R, s.v, s.p, omega, specific_force, dt)
        # Biases are unchanged in the nominal propagation; their uncertainty grows through Q_d.

        p_new = phi @ self.P @ phi.T + q_d
        self.P = 0.5 * (p_new + p_new.T)  # cheap insurance against a drift out of symmetry

        self.steps += 1
        if self.steps % REORTHONORMALISE_EVERY == 0:
            s.R = orthonormalise(s.R)
            s.R_sv = orthonormalise(s.R_sv)

    # ----------------------------------------------------------------------------------------
    # The one update step. Every measurement below reduces to (z, H, R) and calls this.
    # ----------------------------------------------------------------------------------------

    def _apply_update(self, z: np.ndarray, h: np.ndarray, r: np.ndarray) -> None:
        """Error-state Kalman update, with the correction **subtracted** (D-050).

        The sign is not a convention we are free to pick. Section 5 defines the right-invariant
        error as `eta_R = X_hat X^-1`, so `X_hat = Exp(xi) X` and `xi` is the error *in the
        estimate*: estimate-minus-truth, and likewise `db_g = b_g_hat - b_g`. Every Jacobian in
        section 7 is the Jacobian of that subsection's innovation with respect to that same `xi`
        -- GNSS `z = p_hat - p_gnss` giving `+I` on the position block, ZARU `z = w~ - b_g_hat =
        -db_g` giving `-I` on the gyro-bias block. So `delta = K z` is an estimate of the error,
        and removing an error means subtracting it.

        Note this is independent of which way round the innovation is written: flipping `z` to
        measurement-minus-prediction flips `H` with it, `K` picks up the second sign, and `delta`
        is unchanged. Only the section 5 error definition sets the sign, which is why section
        8.3's `X_hat+ = Exp(delta) X_hat` is wrong rather than merely a different convention.

        Joseph form for the covariance: it stays symmetric and PSD under the round-off that the
        short `(I - KH)P` form does not survive across the ~1800 updates of a 180 s outage.
        """
        z = np.asarray(z, dtype=float).ravel()
        s = h @ self.P @ h.T + r
        gain = self.P @ h.T @ np.linalg.inv(s)
        delta = gain @ z

        st = self.state
        # Pose: left-multiply by the *inverse* increment -- right-invariant retraction, minus.
        x_corrected = se23_exp(-delta[0:9]) @ x_of(st.R, st.v, st.p)
        st.R, st.v, st.p = unpack(x_corrected)
        st.b_g = st.b_g - delta[IDX_GYRO_BIAS]
        st.b_a = st.b_a - delta[IDX_ACCEL_BIAS]
        st.R_sv = exp_so3(-delta[IDX_MOUNT]) @ st.R_sv

        ikh = np.eye(ERROR_STATE_DIM) - gain @ h
        p_new = ikh @ self.P @ ikh.T + gain @ r @ gain.T
        self.P = 0.5 * (p_new + p_new.T)

    def _h_body_velocity(self) -> np.ndarray:
        """Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is exactly zero.

        A body-frame velocity constraint carries no instantaneous heading information, and the
        right-invariant filter says so. A naive EKF has a non-zero entry there, gains spurious yaw
        observability, and then trusts a heading it has no right to trust.
        """
        h = np.zeros((3, ERROR_STATE_DIM))
        h[:, IDX_VELOCITY] = self.state.R.T
        return h

    def _h_vehicle_velocity(self) -> tuple[np.ndarray, np.ndarray]:
        """Section 7.2. Returns `(v_veh_hat, H_veh)` with the mount column carried.

        `H_veh = [0, R_sv R_hat^T, 0, 0, 0, -v_veh_hat^]`. The mount column is what makes the
        mount angle observable through NHC **with gain equal to forward speed** -- estimated well
        on a motorway and barely at all in a car park.
        """
        st = self.state
        v_veh = st.R_sv @ st.R.T @ st.v
        h = np.zeros((3, ERROR_STATE_DIM))
        h[:, IDX_VELOCITY] = st.R_sv @ st.R.T
        h[:, IDX_MOUNT] = -skew(v_veh)
        return v_veh, h

    def update_gnss(self, position_ned: np.ndarray, cov: np.ndarray) -> bool:
        """chi-squared-gated GNSS position update. Returns whether the fix was accepted.

        Not called at all during an injected outage -- see eval/outages/inject.mask_gnss.

        Section 7.4: `z = p_hat - p_gnss`, `H_gnss = [-p_hat^, 0, I, 0, 0, 0]`. The `-p_hat^` is
        the price of section 6 -- a state dependence on *position*, which is benign because it is
        not an attitude dependence and so does not touch the yaw-observability property.

        **A rejected fix applies nothing.** Not a smaller correction, not a re-initialisation, not
        a mode flag -- the method returns False and neither `state` nor `P` is touched. That
        absence is the architectural claim: there is no branch to switch on tunnel entry, so there
        is nothing that could produce a jump, and "seamless transition within milliseconds" is
        satisfied by construction rather than by handling (D-001).
        """
        position_ned = np.asarray(position_ned, dtype=float).ravel()
        cov = np.asarray(cov, dtype=float)
        if position_ned.shape != (3,):
            raise ValueError(f"expected a 3-vector position, got {position_ned.shape}")
        if cov.shape != (3, 3):
            raise ValueError(f"expected a 3x3 position covariance, got {cov.shape}")

        z = self.state.p - position_ned
        h = np.zeros((3, ERROR_STATE_DIM))
        h[:, IDX_ATTITUDE] = -skew(self.state.p)
        h[:, IDX_POSITION] = np.eye(3)

        if not chi2_gate(z, h @ self.P @ h.T + cov, self.cfg.chi2_gate_3dof):
            return False
        self._apply_update(z, h, cov)
        return True

    def update_nhc(self, r_nhc: np.ndarray | None = None) -> None:
        """Non-holonomic pseudo-measurement. Caller checks nhc_is_valid() first.

        `r_nhc` is the per-step covariance from the AI-IMU adaptive head once it exists; None
        falls back to the fixed config values.

        Rows 1 and 2 of section 7.2 -- lateral and vertical vehicle-frame velocity are asserted
        zero. Row 0 (forward) is left alone: that is the learned speed head's row, in P-09.

        The gating is the caller's job and cannot be moved in here. `nhc_is_valid` needs yaw rate
        and lateral acceleration, which are properties of the IMU stream and not of the state --
        the filter does not have them.
        """
        v_veh, h_full = self._h_vehicle_velocity()
        rows = [1, 2]
        h = h_full[rows, :]
        z = v_veh[rows]
        if r_nhc is None:
            r = np.diag([self.cfg.nhc_sigma_lateral**2, self.cfg.nhc_sigma_vertical**2])
        else:
            r = np.asarray(r_nhc, dtype=float)
            if r.shape != (2, 2):
                raise ValueError(f"expected a 2x2 NHC covariance, got {r.shape}")
        self._apply_update(z, h, r)

    def update_zupt(self) -> None:
        """Zero-velocity update. Observes accelerometer bias.

        Uses section **7.1**'s body-frame Jacobian, not section 7.2's vehicle-frame one (D-051).
        The two assert the same thing -- `R_sv` is a rotation, so `R_sv R^T v = 0` exactly when
        `R^T v = 0` -- but 7.2 carries a `-v_veh_hat^` mount column, and at a standstill there is
        no direction of travel for the mount angle to be measured against. Section 7.2's own
        result says so: mount observability through a velocity constraint has **gain equal to
        forward speed**, which is zero here. Keeping that column would let a stop shrink the mount
        covariance in proportion to the filter's own *velocity error* -- the very quantity ZUPT
        exists to remove -- which is information the stop does not contain.
        """
        self._apply_update(
            self.state.R.T @ self.state.v,
            self._h_body_velocity(),
            np.eye(3) * self.cfg.zupt_sigma**2,
        )

    def update_zaru(self, gyro: np.ndarray) -> None:
        """Zero-angular-rate update. Observes gyro bias -- the dominant error term.

        Apply at *every* detected stop. This is the cheapest yaw-drift mitigation available and
        the error budget assumes it is running (docs/ERROR_BUDGET.md section 3.2).

        `gyro` is the **raw** sample for this step, not a bias-corrected one (D-052). Section 7.3
        asserts the true rate is zero, so the raw reading *is* the bias: `z = w~ - b_g_hat`, which
        expands to `-db_g` and gives `H_zaru = [0, 0, 0, -I, 0, 0]`. A **direct** observation of
        `b_g` -- no coupling, no integration, no waiting. Compare section 7.1, where yaw is only
        reachable through a second-order path; this is why ZARU matters more for yaw than NHC.
        """
        gyro = np.asarray(gyro, dtype=float).ravel()
        if gyro.shape != (3,):
            raise ValueError(f"expected a 3-vector gyro sample, got {gyro.shape}")
        h = np.zeros((3, ERROR_STATE_DIM))
        h[:, IDX_GYRO_BIAS] = -np.eye(3)
        self._apply_update(gyro - self.state.b_g, h, np.eye(3) * self.cfg.zaru_sigma**2)

    def update_speed(self, speed_mps: float, variance: float) -> None:
        """Learned forward-speed pseudo-measurement with its predicted variance.

        The variance is not decoration: a confidently wrong covariance corrupts the filter worse
        than a noisy mean, which is what Gate 2 tests.
        """
        raise NotImplementedError("Sprint 2, seat S + M: speed pseudo-measurement")
