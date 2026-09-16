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

#: Measured angular random walk, worst white axis, from IO-VNBD's own stationary segments
#: (D-045, re-measured by D-120; docs/ERROR_BUDGET.md section 9.1). Named at module scope because
#: two `FilterConfig` fields are derived from it and a copy-paste between them is exactly the
#: drift a test cannot see. D-045 read 4.11e-4 (1.41 deg/sqrt(hr)) off segments that still held
#: the car's settle and pull-away at each end; with those excluded the same sensor reads half.
GYRO_ARW_MEASURED = 2.18e-4  # rad/s/sqrt(Hz) == 0.75 deg/sqrt(hr)

#: Measured accelerometer bias instability, worst axis, same run (D-120; D-045 read 0.34 mg). It
#: is the floor the accel-bias block converges to, not where it opens (D-115 step 2).
ACCEL_BIAS_INSTABILITY_MEASURED = 2.48e-3  # m/s^2 == 0.25 mg

#: `S-` stream rate, measured from the timestamps (D-047: median dt = 100.0 ms).
IMU_RATE_HZ = 10.0
_SQRT_IMU_RATE_HZ = float(np.sqrt(IMU_RATE_HZ))


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
    if not np.isfinite(nrm):
        raise ValueError(
            f"expm_series received a matrix with non-finite entries (max |element| = {nrm}). "
            "This usually means the filter state has diverged."
        )
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

    The four noise defaults are **measured**, from IO-VNBD's own stationary segments (D-045,
    D-120), by `eval/allan.py`. They are the worst axis across the two segments quiet enough to
    characterise a sensor on -- `S-T2[31532:36371]` (484 s) and `S-T7[47918:52176]` (426 s) --
    because an undersized Q makes the filter over-trust its own propagation and reject good
    measurements at the chi-squared gate, and that failure reads as a sensor fault rather than a
    tuning error.

    Regenerate with::

        python -m eval.allan --paths-from data/manifest/allan_segments_input.txt \
            --out-dir eval/figures

    The measured `gyro_arw` is 0.75 deg/sqrt(hr), inside the 0.5-5 deg/sqrt(hr) phone-MEMS range
    in docs/ERROR_BUDGET.md section 9. D-045 read 1.41 from the same two stops with a segment
    rule that kept the car's settle and pull-away -- ten to twenty samples at each end carrying
    10-74x the interior gyro RMS -- and every seed was about 2x pessimistic for it (D-120). Both
    replace a 3.0e-3 placeholder that was 10.3 deg/sqrt(hr), outside our own stated range (plan
    item R-2, self-flagged in SE23_PROPAGATION.md section 10).
    """

    # Allan-variance-derived, per docs/ERROR_BUDGET.md section 9. Measured on IO-VNBD, not assumed.
    gyro_arw: float = GYRO_ARW_MEASURED  # rad/s/sqrt(Hz)  == 0.75 deg/sqrt(hr)
    accel_vrw: float = 4.03e-3  # m/s^2/sqrt(Hz) == 0.24 m/s/sqrt(hr)

    # Not measured: a 484 s record cannot resolve the +1/2 rate-random-walk slope (it reaches
    # tau = 48 s). Derived instead from the two quantities that *were* measured, by modelling each
    # bias as first-order Gauss-Markov with steady-state spread B and correlation time tau_c taken
    # from the Allan minimum: q = B sqrt(2 / tau_c). A modelling choice, labelled as one, and the
    # conservative direction. See eval.allan.gauss_markov_bias_driving_noise and D-045.
    gyro_bias_rw: float = 3.10e-5  # rad/s^2/sqrt(Hz), from B = 22 deg/hr, tau_c = 23.7 s
    accel_bias_rw: float = 9.67e-4  # m/s^3/sqrt(Hz), from B = 0.25 mg, tau_c = 13.2 s

    # Mount-rotation process noise, the sigma_sv block of Q_c in SE23_PROPAGATION.md section 5.3.
    # Was zero (D-048) because nothing in the repo gave it a magnitude. It is now non-zero for a
    # reason that was measured rather than argued: with zero, NHC collapses the mount block from
    # its PCA spread (2-37 deg) to under 0.1 deg within a minute of driving, after which the
    # constraint is asserted through a rotation the filter believes it knows perfectly, and the
    # mount column of section 7.2's Jacobian -- the only thing that lets a lateral innovation be
    # blamed on the mount rather than on the velocity -- carries no weight (D-110). The value is
    # stated as the walk it implies: 1e-3 rad/sqrt(s) is 0.44 deg over a minute, the order of the
    # creep a phone in a cradle shows and well under the 5 deg knock `reinflate_mount` exists
    # for. Swept, not guessed -- see D-115 for the sweep and what it did and did not change.
    mount_rw: float = 1.0e-3  # rad/s/sqrt(Hz)

    # NHC: lateral and vertical body velocity are ~0. Loose defaults; the AI-IMU CNN replaces
    # these with a per-step prediction once seat M's adaptive head lands (D-005).
    nhc_sigma_lateral: float = 0.5  # m/s
    nhc_sigma_vertical: float = 0.5  # m/s

    zupt_sigma: float = 0.02  # m/s

    # Gyro **turn-on** bias, 1-sigma per axis: the uncertainty of a bias nothing has estimated
    # yet, which is what `P0` has to carry. It is not the bias *instability* (22 deg/hr =
    # 0.006 deg/s, D-120; D-045 read 42), which is how far an already-estimated bias wanders and
    # is the floor the block converges to, not where it starts. Measured as the mean gyro over
    # every stationary run of 5 s or longer in the TRAIN stems that have one (M, S1, S2, S4 --
    # 638 s at a standstill): worst-axis RMS 0.14 deg/s, largest single axis 0.20 deg/s (M,
    # vertical). 0.2 deg/s puts the largest measured bias at one sigma. With 42 deg/hr in the
    # block, a 0.1 deg/s reading at a standstill was a 9-sigma event and **every ZARU on every
    # held-out stem was rejected** -- 0 of 103 accepted on Vta1a -- so the one update that
    # observes the dominant error term never ran (D-115).
    gyro_bias_turn_on: float = float(np.deg2rad(0.2))  # rad/s

    # Accelerometer **turn-on** bias, 1-sigma per axis: the uncertainty of a bias nothing has
    # estimated yet, which is what `P0` has to carry. It is not the bias *instability* (0.25 mg =
    # 2.45 mm/s^2, D-120; D-045 read 0.34 mg), which is how far an already-estimated bias wanders
    # and is the floor the block converges to, not where it starts. Measured as mean(|f|) - g
    # over every stationary run of 5 s or longer in the TRAIN stems that have one (M, S1, S2, S4
    # -- the same 638 s D-115 used for the gyro): RMS across runs 6.2 mg (0.060 m/s^2), largest
    # single run 8.2 mg (0.081 m/s^2, M). That is the one accelerometer-offset component
    # independent of levelling; the horizontal components are confounded with a levelling
    # derived from the same sensor and are NOT measurable this way. 0.08 m/s^2 puts the largest
    # measured offset at one sigma.
    accel_bias_turn_on: float = 0.08  # m/s^2

    # The receiver's course over ground, `gps_orientation_deg` in the `S-` stream, is a Doppler
    # heading and is the one heading measurement a phone has before it moves far enough for a
    # fix-to-fix chord to mean anything. Its error against the paired `V-` course, pooled over
    # 5,137 moving fixes on six held-out stems, is unbiased (median -0.1 deg) with a spread that
    # falls as 1/speed exactly as a fixed cross-track velocity noise would: p90 9.9 deg at 3-5
    # m/s, 5.6 deg at 5-10 m/s, 1.6 deg above 10 m/s. `atan(0.5 m/s / speed)` reproduces those
    # to within 30% at every bin, so that is the model, with its one parameter named here.
    # Below `course_min_speed_mps` the p99 error reaches 178 deg -- a stationary receiver reports
    # its last course -- and the column is not read.
    course_cross_track_sigma_mps: float = 0.5
    course_min_speed_mps: float = 3.0

    # The receiver's Doppler *speed*, `gps_speed_mps`, against the paired `V-` track speed at
    # the fix epochs, eight held-out and TRAIN stems: unbiased (median -0.08 to +0.05 m/s), RMS
    # 0.27-0.92 m/s, p90 0.33-1.00 m/s. With the course above it is a horizontal velocity
    # measurement worth about 0.5 m/s along-track and 0.5 m/s across (D-115), and
    # `InEKF.update_gnss_velocity` applies it as one, at every open fix that is moving faster
    # than `course_min_speed_mps`. It is the update that made the filter hold on S3a: a position
    # fix every 9 s is the double integral of the tilt error and cannot tell a 3 m/s speed error
    # from a 10-degree heading error, and the filter was attributing both to the gyro bias.
    gnss_speed_sigma_mps: float = 0.5

    # ZARU's innovation is `z = w~ - b_g_hat` (SE23_PROPAGATION.md section 7.3), whose noise is
    # the gyro *white* noise per sample -- so R is not a free parameter, it is the Allan run's
    # own number at the stream's own rate: `gyro_arw / sqrt(dt) = gyro_arw * sqrt(rate)`
    # (D-056). Derived here rather than typed, so it cannot drift away from `gyro_arw`; the
    # relationship is pinned by a test. The 1.0e-3 it replaced predated the Allan run; D-045's
    # 1.2997e-3 was 1.9x this, read off segments that still held the stop's settle (D-120).
    #
    # **This is the floor, not the figure the harness tests against (D-131).** The Allan run
    # was a phone on a desk; the same phone at rest in a car carries 0.3-1.4 deg/s of idle
    # vibration per sample (TRAIN S1: innovation std [0.72, 0.38, 0.60] deg/s per axis at the
    # 3,066 samples the stop detector fired on), 10-35x this in sigma, and against R = (0.039
    # deg/s)^2 the chi-squared gate refused 1,356 of S3a's 1,372 offered ZARUs (D-130). The
    # caller reads the stop's own level from the detector window (`zaru_sigma_from_window`) and
    # passes it to `update_zaru(gyro, sigma=)`; this value is what that reading is floored at,
    # and what `update_zaru` uses when no sigma is passed (the NEES scenario, whose simulated
    # sensor *is* the Allan sensor).
    zaru_sigma: float = GYRO_ARW_MEASURED * _SQRT_IMU_RATE_HZ  # rad/s == 6.894e-4 at 10 Hz

    #: `S-` stream sample rate. Measured, not nominal: D-047 confirmed median dt = 100.0 ms from
    #: the timestamps. Named here because `zaru_sigma` is rate-dependent and the 200 Hz FOG build
    #: will need a different one.
    imu_rate_hz: float = IMU_RATE_HZ

    # Stationary detection. Thresholds are conservative on purpose: a missed ZUPT costs a little
    # accuracy, a false ZUPT while rolling injects a hard error the filter believes.
    #
    # Measured against the paired `V-` track speed (D-115, Fix 1). At 2 s / 0.02 (m/s^2)^2 on
    # accel variance and 0.01 rad/s on bias-corrected gyro window mean |mean(gyro) - b_g|,
    # rolling false-fire share is 0.0% on S1, 1.07% on S2 (0.09% rolling FPR), 0.84% on S3a
    # (0.06% FPR), and 1.13% on S3c (0.08% FPR), against 70.0% recall of S3a's stops and 82.1% of
    # S3c's. S3a's standstill gyro norm is ~1.55 deg/s of idle vibration floor that previously
    # prevented detection entirely (0% recall); subtracting gyro bias and taking the norm of the
    # window mean rather than the mean of norms recovers stop detection while keeping rolling
    # false-fires ~0%. The run-in to a stop is refuted by the harness's state veto.
    zupt_accel_var_thresh: float = 0.02  # (m/s^2)^2
    zupt_gyro_norm_thresh: float = 0.01  # rad/s
    zupt_window_s: float = 2.0

    # chi-squared gate at 3 DOF, 99% -- the only thing standing between the filter and a
    # multipath fix on tunnel exit.
    chi2_gate_3dof: float = 11.345
    #: The same 99% gate at 2 DOF -- applied to the horizontal GNSS velocity update only when
    #: `gate_gnss_velocity` is set.
    chi2_gate_2dof: float = 9.210
    #: **The Doppler velocity update is not gated**, for the reason D-057 gives for ZUPT: a
    #: rejected velocity is the first step of every runaway this harness has recorded. The
    #: filter's velocity block after 9 s of propagation is set by its tilt block, and a 2-sigma
    #: tilt excursion puts a good Doppler fix outside the gate; once refused, the next one is
    #: further out, and the lock is permanent. Measured over the whole aided pass (D-115):
    #: S3a's position error is 15.0 m median / 144 m p90 gated at 99%, 11.3 / 144 at 99.99%,
    #: and 10.6 / 58 ungated; Vta1a 15.6 / 46, 14.7 / 43, 10.2 / 16; Vw2 diverges under either
    #: gate and holds 57 / 207 without one. A Doppler velocity has no multipath mode comparable
    #: to a pseudorange position's, and the caller already refuses a course below
    #: `course_min_speed_mps`, where the receiver reports a stale one.
    gate_gnss_velocity: bool = False

    # NHC must be gated OFF during these. An ungated NHC through a slip is worse than no NHC.
    nhc_max_yaw_rate: float = 0.6  # rad/s -- hard cornering
    nhc_max_lateral_accel: float = 4.0  # m/s^2 -- approaching slip
    nhc_min_speed: float = 1.0  # m/s -- below this, direction of travel is ill-defined

    mount_disturbance_gyro_thresh: float = 3.0  # rad/s of high-frequency energy

    # ------------------------------------------------------------------------------------
    # Initial covariance P0, per block. See `initial_covariance` for the derivation of each
    # entry and docs/ERROR_BUDGET.md section 10 for the table. The flat `1e-3 * I` these replace
    # (plan item R-3) was sigma = 0.0316 in every unit at once, and wrong in both directions:
    # 95x too tight on position and 134x on velocity, 156x too *loose* on gyro bias. A P0 that
    # is too tight makes the chi-squared gate reject good measurements, and that failure reads
    # as a sensor fault rather than as tuning (D-055).
    # ------------------------------------------------------------------------------------

    #: 1-sigma horizontal GNSS position accuracy, docs/EVALUATION.md section 2 (+/- 3 m, VBOX).
    #: The harness overrides it with the `S-` stream's own per-sample `gps_accuracy_m` where it
    #: has one; this is the default for a filter constructed without a fix in hand.
    gnss_sigma_m: float = 3.0

    #: GNSS epoch used to turn a position accuracy into a velocity and a heading accuracy.
    #: 1 Hz is the protocol's nominal rate (docs/DATASETS.md section 1); the measured `S-` GPS
    #: cadence is longer, which would make both *tighter*, so 1 Hz is the conservative choice.
    gnss_epoch_s: float = 1.0


#: Reference cruise speed, docs/ERROR_BUDGET.md section 1 (60 km/h = 16.7 m/s). Used only to turn
#: a GNSS position accuracy into a course-over-ground heading accuracy for `initial_covariance`.
REFERENCE_SPEED_MPS = 16.7

#: The yaw sigma of a filter that has no heading at all: the standard deviation of an angle
#: uniform on the circle, `pi / sqrt(3)` = 103.9 deg. Used by the harness for a vehicle that has
#: not yet moved -- a stationary receiver reports no course, and a fix-to-fix chord of a car that
#: has not moved is noise -- so that the block says "unknown" rather than 14.6 deg (D-115). The
#: EKF's linearisation is meaningless at this width, and that is the point: nothing downstream
#: should be able to read it as a heading.
UNALIGNED_YAW_SIGMA_RAD = float(np.pi / np.sqrt(3.0))

#: The mount angle the disturbance detector exists for: docs/ERROR_BUDGET.md section 5 costs a
#: 5-degree knock at 87 m over a 60 s outage. It is the widest mount angle any document in this
#: repo names, and `initial_covariance` uses it as the mount prior for the reason given there.
MOUNT_KNOCK_RAD = float(np.deg2rad(5.0))


@dataclass(frozen=True)
class MountInit:
    """What the PCA initialiser found: the mount rotation, and how well it is pinned down.

    `spread_rad` is the standard error of the principal-axis angle, which is what `P0`'s mount
    block wants (D-055 uses a 5-degree fallback in its absence). `sign_resolved` is the half of the
    answer PCA cannot supply on its own.
    """

    r_sv: np.ndarray
    yaw_rad: float
    spread_rad: float
    sign_resolved: bool
    eigenvalue_ratio: float
    n_effective: float
    #: Which cue resolved the sign: "turn" (centripetal force against yaw rate), "acceleration"
    #: (forward specific force against a GNSS-derived forward acceleration), or "none".
    sign_source: str = "none"

    @property
    def yaw_deg(self) -> float:
        return float(np.degrees(self.yaw_rad))

    @property
    def spread_deg(self) -> float:
        return float(np.degrees(self.spread_rad))


#: The PCA sign cue is believed when its t-statistic clears this. 3 is the ordinary "three
#: sigma": the cue's mean product, over its effective sample size, is three standard errors from
#: zero. Below it the ambiguity is *reported* -- `sign_resolved` False -- and never guessed
#: (D-074).
SIGN_CUE_MIN_T = 3.0


def pca_mount_yaw(
    accel: np.ndarray, gravity: np.ndarray, forward_reference: np.ndarray | None = None
) -> MountInit:
    """Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific force.

    **An initialiser only** (D-006). One-shot alignment is fragile and cannot track a mount that
    shifts, so `R_sv` lives in the filter state and NHC keeps estimating it; this supplies the
    starting point and, just as importantly, the spread `P0`'s mount block should carry.

    Method. `gravity` fixes the vertical, so the phone's horizontal plane is known; within it, a
    car's specific force is dominated by braking and acceleration along its own forward axis, with
    much less side to side. The first principal component of the horizontal specific force is
    therefore the vehicle's forward axis **expressed in the phone frame**, which is exactly what
    the mount yaw is -- no navigation-frame quantity is needed and none is used.

    **PCA returns an axis, not a direction.** Forward and backward have the same principal
    component, and nothing in a covariance can tell them apart. `forward_reference` resolves it: a
    per-sample signed scalar that grows with forward acceleration -- the finite-differenced
    `gps_speed_mps` is the one the `S-` stream can supply -- and the sign is chosen so the two
    correlate positively, **when that correlation clears `SIGN_CUE_MIN_T`**. Until D-115 there
    was no such test: a reference that was *constant* over the window -- a car that had not
    moved -- left `ref - ref.mean()` as floating-point dust, `np.any` of which is True, and the
    sign was "resolved" from the correlation of noise with noise. On Vta1a that put the forward
    axis backwards with `sign_resolved` True, and the filter integrated every acceleration as a
    braking; D-110 measured the consequence and attributed it to NHC.

    Without a cue that clears the bar, `sign_resolved` is False and the yaw carries a 180-degree
    ambiguity that the caller must resolve before the result is used. It is returned rather than
    guessed because a 180-degree mount error is not a large version of a small one: it is a
    vehicle driving backwards, and it will not converge out under NHC.

    **Where PCA is the wrong tool.** Its premise is that the horizontal specific force is
    dominated by braking and acceleration along the forward axis. In a roundabout it is
    dominated by centripetal force along the *lateral* axis, and PCA returns that axis with a
    confident spread (Vw4, 60-90 s: 76.8 deg with 1.8 deg spread, 108 deg from the two windows
    before it). `mount_yaw_from_dynamics` does not have that premise and is what the harness
    aligns from when the stream carries GNSS speed; this is the fallback for streams that do not.

    `spread_rad` is the asymptotic standard error of a 2D principal-axis angle,
    `sqrt(l1 l2 / (n_eff (l1 - l2)^2))`, checked by Monte Carlo to within 7% over eigenvalue
    ratios 2-25 and n from 200 to 5000. `n_eff` is **not** the sample count: accelerometer samples
    at 10 Hz are strongly serially correlated, and using `n` would understate the spread by the
    square root of the correlation time. It is the AR(1) effective sample size
    `n (1 - rho) / (1 + rho)` from the measured lag-1 autocorrelation of the forward projection --
    derived, and labelled as derived, in the same spirit as D-045's Gauss-Markov bias noises.
    """
    accel = np.asarray(accel, dtype=float)
    gravity = np.asarray(gravity, dtype=float).ravel()
    if accel.ndim != 2 or accel.shape[1] != 3:
        raise ValueError(f"expected (n, 3) accelerometer samples, got {accel.shape}")
    if gravity.shape != (3,):
        raise ValueError(f"expected a 3-vector gravity direction, got {gravity.shape}")
    g_norm = float(np.linalg.norm(gravity))
    if g_norm < 1e-6:
        raise ValueError("gravity direction has no magnitude; the vertical cannot be established")
    if accel.shape[0] < 3:
        raise ValueError(
            f"{accel.shape[0]} samples cannot support a principal axis and its standard error"
        )

    up = gravity / g_norm
    # The phone's own x axis, projected into the horizontal plane, is the reference direction the
    # reported yaw is measured from -- so `e1` is not an arbitrary basis choice.
    x_phone = np.array([1.0, 0.0, 0.0])
    if abs(float(up @ x_phone)) > 0.999:  # phone stood on its nose: x is the vertical
        x_phone = np.array([0.0, 1.0, 0.0])
    e1 = x_phone - float(up @ x_phone) * up
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(up, e1)

    horizontal = np.column_stack([accel @ e1, accel @ e2])
    horizontal = horizontal - horizontal.mean(axis=0)
    cov = np.cov(horizontal, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    l2, l1 = float(eigvals[0]), float(eigvals[1])
    axis = eigvecs[:, 1]

    projection = horizontal @ axis
    n = projection.shape[0]
    sign_resolved = False
    sign_source = "none"

    if forward_reference is not None:
        ref = np.asarray(forward_reference, dtype=float).ravel()
        if ref.shape[0] != n:
            raise ValueError(
                f"forward_reference has {ref.shape[0]} samples against {n} accelerometer "
                "samples; they must be the same stream"
            )
        centred = ref - ref.mean()
        if np.ptp(centred) > 0:
            t_stat, positive = _cue_statistic(projection * centred)
            if t_stat >= SIGN_CUE_MIN_T:
                if not positive:
                    axis, projection = -axis, -projection
                sign_resolved, sign_source = True, "acceleration"

    # AR(1) effective sample size: 10 Hz accelerometer samples are not independent draws.
    n_eff = _effective_samples(projection)

    gap = l1 - l2
    spread = float(np.sqrt(l1 * l2 / (n_eff * gap**2))) if gap > 0 else float(np.pi / 2)

    forward = axis[0] * e1 + axis[1] * e2
    down = -up
    right = np.cross(down, forward)
    r_sv = orthonormalise(np.vstack([forward, right, down]))
    return MountInit(
        r_sv=r_sv,
        yaw_rad=float(np.arctan2(axis[1], axis[0])),
        spread_rad=min(spread, float(np.pi / 2)),
        sign_resolved=sign_resolved,
        eigenvalue_ratio=float(l1 / l2) if l2 > 0 else float("inf"),
        n_effective=float(n_eff),
        sign_source=sign_source,
    )


def _effective_samples(x: np.ndarray) -> float:
    """AR(1) effective sample size of a serially correlated series, never below 2."""
    n = x.shape[0]
    if n < 3:
        return 2.0
    a, b = x[:-1] - x.mean(), x[1:] - x.mean()
    denom = float(np.sqrt((a @ a) * (b @ b)))
    rho = float(np.clip((a @ b) / denom, -0.999, 0.999)) if denom > 0 else 0.0
    return max(2.0, n * (1.0 - rho) / (1.0 + rho))


#: `mount_yaw_from_dynamics` accepts a fit only above this correlation between the phone's
#: horizontal specific force and the reference. Measured per 60 s window on the held-out stems:
#: windows that clear 0.5 agree with each other to a median 9-13 deg on S3a and Vta1a, windows
#: below it scatter over the circle (D-115). The threshold is where the estimator becomes
#: repeatable, which is the only property a 180-degree-free estimate can be checked for without
#: truth.
DYNAMICS_FIT_MIN_CORRELATION = 0.5

#: Minimum effective samples for a dynamics fit. With both sides low-passed over
#: `smooth_samples` and the reference's forward component held over 9 s fix intervals, the
#: residual is far too autocorrelated for an AR(1) count to mean anything -- it returns 2-12 on
#: windows whose correlation is 0.55-0.87 -- so the count is the number of smoothing windows the
#: data spans, and 15 of them is 27 s at the default smoothing: enough driving to have held an
#: acceleration and a turn, not enough to have driven a long straight road and called it aligned.
DYNAMICS_FIT_MIN_EFFECTIVE = 15.0


def mount_yaw_from_dynamics(
    accel: np.ndarray,
    gravity: np.ndarray,
    forward_ref: np.ndarray,
    right_ref: np.ndarray,
    *,
    smooth_samples: int = 9,
) -> MountInit:
    """Mount yaw by least squares between the phone's horizontal specific force and the
    vehicle's own acceleration -- signed, so there is no 180-degree ambiguity to resolve.

    `forward_ref` is the vehicle's longitudinal acceleration per sample and `right_ref` its
    lateral (centripetal) acceleration, both in the vehicle frame, both m/s^2. The harness builds
    them from what the phone has: the finite-differenced GNSS speed for the first, and
    `speed * omega_down` from the gyro for the second (D-115). Anything that is not a rotation
    of the phone's horizontal specific force onto that reference is residual.

    The frame algebra, written out because it is where a sign is easy to lose: the vehicle frame
    is (forward, right, **down**) and the phone's horizontal basis `(e1, e2)` has `e2 = up x e1`,
    so the two horizontal frames have *opposite* handedness. A vehicle-frame vector `(a_f, a_r)`
    has phone-plane components `(a_f - i a_r) e^{i phi}` in complex form, where `phi` is the
    forward axis's angle from `e1`. The fit is therefore `phi = arg(sum(conj(a_f - i a_r) h))`.
    Treating the lateral component as `+i a_r` -- rotating forward by +90 degrees to get "right"
    -- returns the left axis instead, and the estimate comes out 180 degrees wrong on every turn.

    Both sides are low-passed over `smooth_samples` (0.9 s at 10 Hz) before the fit: the phone's
    horizontal channels carry 3-4x the vehicle's acceleration in aliased vibration at this rate,
    and the vehicle's rigid-body dynamics live below 1 Hz.

    `spread_rad` is the angle's standard error from the residual: residual variance per
    component over the reference's mean squared magnitude, over the effective sample count,
    which is the number of smoothing windows the data spans (`n / (2 * smooth_samples)` -- the
    reference's own bandwidth, since an AR(1) count of a residual that holds a 9 s step function
    is meaningless). `sign_resolved` is True whenever the fit is accepted -- a signed reference
    has no ambiguity -- and False, with the axis still reported, when the correlation falls below
    `DYNAMICS_FIT_MIN_CORRELATION` or the effective sample count below
    `DYNAMICS_FIT_MIN_EFFECTIVE`: a fit nothing should be aligned from.
    """
    accel = np.asarray(accel, dtype=float)
    gravity = np.asarray(gravity, dtype=float).ravel()
    forward_ref = np.asarray(forward_ref, dtype=float).ravel()
    right_ref = np.asarray(right_ref, dtype=float).ravel()
    if accel.ndim != 2 or accel.shape[1] != 3:
        raise ValueError(f"expected (n, 3) accelerometer samples, got {accel.shape}")
    n = accel.shape[0]
    if forward_ref.shape[0] != n or right_ref.shape[0] != n:
        raise ValueError(
            f"references have {forward_ref.shape[0]} and {right_ref.shape[0]} samples against "
            f"{n} accelerometer samples; they must be the same stream"
        )
    g_norm = float(np.linalg.norm(gravity))
    if gravity.shape != (3,) or g_norm < 1e-6:
        raise ValueError("gravity direction has no magnitude; the vertical cannot be established")

    up = gravity / g_norm
    x_phone = np.array([1.0, 0.0, 0.0])
    if abs(float(up @ x_phone)) > 0.999:
        x_phone = np.array([0.0, 1.0, 0.0])
    e1 = x_phone - float(up @ x_phone) * up
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(up, e1)

    h = (accel @ e1) + 1j * (accel @ e2)
    w = forward_ref - 1j * right_ref
    ok = np.isfinite(h) & np.isfinite(w)
    h = _moving_average(np.where(ok, h, 0.0), smooth_samples)[ok]
    w = _moving_average(np.where(ok, w, 0.0), smooth_samples)[ok]
    h = h - h.mean()
    w = w - w.mean()

    energy_h, energy_w = float(np.sum(np.abs(h) ** 2)), float(np.sum(np.abs(w) ** 2))
    if h.size < 3 or energy_h <= 0 or energy_w <= 0:
        return MountInit(
            r_sv=np.eye(3), yaw_rad=0.0, spread_rad=float(np.pi / 2), sign_resolved=False,
            eigenvalue_ratio=float("nan"), n_effective=0.0, sign_source="none",
        )
    z = complex(np.sum(np.conj(w) * h))
    phi = float(np.angle(z))
    correlation = float(abs(z) / np.sqrt(energy_h * energy_w))

    residual = h - w * np.exp(1j * phi)
    n_eff = max(2.0, h.size / (2.0 * max(smooth_samples, 1)))
    spread = float(
        np.sqrt((np.mean(np.abs(residual) ** 2) / 2.0) / np.mean(np.abs(w) ** 2) / n_eff)
    )
    accepted = correlation >= DYNAMICS_FIT_MIN_CORRELATION and n_eff >= DYNAMICS_FIT_MIN_EFFECTIVE

    forward = np.cos(phi) * e1 + np.sin(phi) * e2
    down = -up
    right = np.cross(down, forward)
    return MountInit(
        r_sv=orthonormalise(np.vstack([forward, right, down])),
        yaw_rad=phi,
        spread_rad=min(spread, float(np.pi / 2)),
        sign_resolved=bool(accepted),
        eigenvalue_ratio=correlation,  # for this estimator: the fit correlation, not a ratio
        n_effective=float(n_eff),
        sign_source="dynamics" if accepted else "none",
    )


def _moving_average(x: np.ndarray, k: int) -> np.ndarray:
    """Centred moving average over `k` samples, shrinking at the edges rather than padding."""
    if k <= 1:
        return np.asarray(x)
    kernel = np.ones(k)
    count = np.convolve(np.ones(x.shape[0]), kernel, mode="same")
    if np.iscomplexobj(x):
        real = np.convolve(x.real, kernel, mode="same")
        imag = np.convolve(x.imag, kernel, mode="same")
        return (real + 1j * imag) / count
    return np.convolve(x, kernel, mode="same") / count


def _cue_statistic(products: np.ndarray) -> tuple[float, bool]:
    """`(t, positive)` for a sign cue: how many standard errors the mean product sits from
    zero, over the cue's own effective sample size, and which side."""
    products = np.asarray(products, dtype=float)
    if products.size < 3:
        return 0.0, True
    mean = float(products.mean())
    sd = float(products.std(ddof=1))
    if sd <= 0:
        return 0.0, mean > 0
    t = abs(mean) / (sd / np.sqrt(_effective_samples(products)))
    return float(t), mean > 0


def initial_covariance(
    cfg: FilterConfig | None = None,
    *,
    mount_sigma_rad: float | None = None,
    yaw_sigma_rad: float | None = None,
    level_sigma_rad: float | None = None,
    velocity_sigma_mps: float | None = None,
) -> np.ndarray:
    """`P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDGET.md.

    Replaces the flat `1e-3 * I` of plan item R-3 (D-055). One number, sigma = 0.0316, carried
    in six different units -- so it was wrong in every block and wrong in both directions:

        block          flat sigma      P0 sigma        flat was
        position       3.2 cm          3 m             95x too tight
        velocity       3.2 cm/s        4.24 m/s        134x too tight
        yaw            1.81 deg        14.56 deg       8x too tight
        roll, pitch    1.81 deg        0.83 deg        2.2x too loose
        gyro bias      1810 deg/hr     720 deg/hr      2.5x too loose
        accel bias     3.2 cm/s^2      8 cm/s^2        2.5x too tight
        mount          1.81 deg        5 deg           2.8x too tight

    (The gyro-bias row read 42 deg/hr and the roll/pitch row 1.31 deg until D-115; the accel-bias
    row read 2.5 mm/s^2 until D-115 step 2; see `FilterConfig.gyro_bias_turn_on` and
    `FilterConfig.accel_bias_turn_on` for why a bias instability is the wrong quantity to start an
    unestimated bias from, and the `zupt_*` thresholds for the tighter stop detector.)

    A `P0` that is too tight makes the chi-squared gate reject good measurements, and that failure
    presents as a sensor problem rather than as a tuning one, which is how it survives a debugging
    session. (The plan's R-3 row calls the position block "too loose"; it is too *tight*, by 95x
    in sigma. Flagged rather than silently corrected -- phases.md section 0.1.)

    The initialisation model, stated because two blocks below depend on which epoch it is:

    * **Roll and pitch** come from the gravity vector at a **detected stop**, so the levelling
      error is bounded by the largest specific-force disturbance the stop detector still admits:
      `sqrt(zupt_accel_var_thresh) / g` = 0.83 deg. The sensor *floor* is far tighter -- the
      measured 0.25 mg accel bias instability is 0.015 deg -- but the floor is not what bounds a
      real alignment, the detector's own admission threshold is.
    * **Yaw** comes from GNSS course over ground, which needs motion, so it is not observable at
      that same stationary epoch and the prior stands until the vehicle moves: differencing two
      fixes gives `sqrt(2) * sigma_p / dt_gnss` of cross-track velocity error, and dividing by the
      reference speed gives 14.6 deg. That is the *fallback*. The harness passes `yaw_sigma_rad`
      when it has a real heading source -- the receiver's own course at a known speed
      (`FilterConfig.course_cross_track_sigma_mps`) -- or when it has none at all, in which case
      the honest value is `UNALIGNED_YAW_SIGMA_RAD`, and 14.6 deg would be a claim to know a
      heading nobody has measured (D-115).
    * **Position** is the fix itself; **velocity** is that same differenced pair.
    * **The gyro bias block** is the measured turn-on bias (D-115); **the accel bias block** is
      the measured turn-on bias (`FilterConfig.accel_bias_turn_on`, 0.08 m/s^2, D-115 step 2).
    * **The mount block** takes `mount_sigma_rad` when the PCA initialiser (`pca_mount_yaw`)
      has run and measured a spread; without one it falls back to a stated 5 degrees. See below.

    Returns a diagonal matrix: `P0` is a *prior*, and the correlations between blocks are exactly
    what the filter has not learned yet.
    """
    cfg = cfg or FilterConfig()
    g = float(GRAVITY_NED[2])

    # Levelling at a detected stop. The detector admits accelerometer variance up to
    # `zupt_accel_var_thresh`, so that is the residual specific force the alignment must tolerate.
    # The harness passes its own figure when it levelled on a moving window (D-115).
    if level_sigma_rad is None:
        sigma_level = float(np.sqrt(cfg.zupt_accel_var_thresh)) / g
    elif level_sigma_rad <= 0:
        raise ValueError(f"level_sigma_rad must be positive, got {level_sigma_rad}")
    else:
        sigma_level = float(level_sigma_rad)

    # Two GNSS fixes, differenced. Position noise sqrt(2)*sigma_p over one epoch -- unless the
    # caller set the velocity from the receiver's Doppler speed and course, which is worth
    # `course_cross_track_sigma_mps` and not a position chord (D-115).
    if velocity_sigma_mps is None:
        sigma_v = float(np.sqrt(2.0) * cfg.gnss_sigma_m / cfg.gnss_epoch_s)
    elif velocity_sigma_mps <= 0:
        raise ValueError(f"velocity_sigma_mps must be positive, got {velocity_sigma_mps}")
    else:
        sigma_v = float(velocity_sigma_mps)

    # Course over ground: cross-track velocity error over forward speed -- unless the caller has
    # a measured heading accuracy, or knows it has no heading at all.
    if yaw_sigma_rad is None:
        sigma_yaw = sigma_v / REFERENCE_SPEED_MPS
    elif yaw_sigma_rad <= 0:
        raise ValueError(f"yaw_sigma_rad must be positive, got {yaw_sigma_rad}")
    else:
        sigma_yaw = float(yaw_sigma_rad)

    # Gyro and accel: the measured turn-on biases (`FilterConfig.gyro_bias_turn_on`,
    # `FilterConfig.accel_bias_turn_on`), because the blocks start from biases nothing has
    # estimated yet. The Allan run's bias instabilities (22 deg/hr, 0.25 mg since D-120; D-045 read
    # 42 and 0.34) are how far an already-estimated bias wanders -- the floor the blocks converge
    # to, not where they start. The vertical accelerometer offset is measured as mean(|f|) - g
    # over standstill runs (the one component independent of levelling); 0.08 m/s^2 puts the
    # largest measured offset at one sigma.
    sigma_bg = cfg.gyro_bias_turn_on
    sigma_ba = cfg.accel_bias_turn_on

    # The mount block. Without a PCA spread the block starts from no measurement, and the prior
    # therefore must not assert knowledge we do not have. The ~1.15 deg figure in
    # docs/ERROR_BUDGET.md section 5 is a *requirement*, and using a requirement as a prior would
    # have the filter begin by asserting that the budget is already met. The 5 deg knock in the
    # same section is the widest mount angle the repo names and the magnitude the disturbance
    # detector exists for, so it is used instead: wide enough that the NHC updates which would
    # correct a real misalignment are not rejected at the gate. Same reasoning as D-048, opposite
    # direction, because here zero is not available. P-11 replaces this with the initialiser's
    # measured spread.
    sigma_mount = MOUNT_KNOCK_RAD if mount_sigma_rad is None else float(mount_sigma_rad)
    if sigma_mount <= 0:
        raise ValueError(f"mount_sigma_rad must be positive, got {mount_sigma_rad}")

    sd = np.empty(ERROR_STATE_DIM)
    sd[0:2] = sigma_level  # roll, pitch
    sd[2] = sigma_yaw
    sd[IDX_VELOCITY] = sigma_v
    sd[IDX_POSITION] = cfg.gnss_sigma_m
    sd[IDX_GYRO_BIAS] = sigma_bg
    sd[IDX_ACCEL_BIAS] = sigma_ba
    sd[IDX_MOUNT] = sigma_mount
    return np.diag(sd**2)


def right_invariant_from_plain(
    p_plain: np.ndarray, position_ned: np.ndarray, velocity_ned: np.ndarray
) -> np.ndarray:
    """Re-express a covariance built on *plain* errors in the filter's right-invariant ones.

    Every sigma `initial_covariance` is built from is a plain error: the position is known to
    the fix accuracy, the velocity to the Doppler accuracy, the yaw to the course accuracy --
    each about the vehicle, where it stands. The filter's error is not that. Section 5 defines
    `eta = X_hat X^-1`, and expanding `Exp(xi) X` gives `p_hat = p + dtheta x p + xi_p` and
    `v_hat = v + dtheta x v + xi_v`: the invariant position error `xi_p` is the plain error
    *minus* the displacement a world-frame attitude error produces about the origin, and a
    diagonal `P` in these coordinates is a claim that the two are uncorrelated. They are not.
    Writing `xi_p = dp + p^ dtheta` and `xi_v = dv + v^ dtheta`, a diagonal plain covariance
    maps to one with `cov(xi_p, dtheta) = p^ P_theta` and `P_xi_p = P_p + p^ P_theta p^T`.

    Left diagonal, the filter is *under*-confident in plain terms by `|p| sigma_yaw` -- 16 m at
    100 m from the origin with a 9-degree yaw -- and, less harmlessly, it holds a correlation
    between height and roll/pitch of `|p| sigma_tilt` that nothing measured: at 500 m and 1 deg
    that is 8.7 m, comparable to the altitude fix, and each altitude innovation then moves the
    tilt (D-115). This is the same `-p^` that `update_gnss` carries in its Jacobian, applied
    once to the prior so the prior and the measurement model agree on what `xi_p` means.

    `p_plain` is returned re-expressed; the input is not modified.
    """
    p_plain = np.asarray(p_plain, dtype=float)
    if p_plain.shape != (ERROR_STATE_DIM, ERROR_STATE_DIM):
        raise ValueError(
            f"expected a {ERROR_STATE_DIM}x{ERROR_STATE_DIM} covariance, got {p_plain.shape}"
        )
    j = np.eye(ERROR_STATE_DIM)
    j[IDX_VELOCITY, IDX_ATTITUDE] = skew(np.asarray(velocity_ned, dtype=float).ravel())
    j[IDX_POSITION, IDX_ATTITUDE] = skew(np.asarray(position_ned, dtype=float).ravel())
    out = j @ p_plain @ j.T
    return 0.5 * (out + out.T)


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


def is_stationary(
    accel_window: np.ndarray,
    gyro_window: np.ndarray,
    cfg: FilterConfig,
    *,
    gyro_bias: np.ndarray | None = None,
) -> bool:
    """Detect a stopped vehicle for ZUPT/ZARU.

    Both conditions must hold: low accelerometer variance *and* low bias-corrected gyro magnitude.
    Variance rather than magnitude on the accelerometer because gravity dominates its magnitude at
    all times; a stationary phone still reads ~9.8 m/s^2.

    The gyro condition checks `|mean(gyro_window) - gyro_bias| < zupt_gyro_norm_thresh`, where
    `gyro_bias` defaults to zero if omitted. Evaluating the norm of the window mean rather than the
    mean of per-sample norms prevents high-frequency sensor noise and idle cabin vibration (such as
    S3a's ~1.55 deg/s standstill gyro norm) from masking a true stop and locking out ZARU.
    """
    accel_window = np.asarray(accel_window, dtype=float)
    gyro_window = np.asarray(gyro_window, dtype=float)
    if accel_window.ndim != 2 or accel_window.shape[1] != 3:
        raise ValueError(f"expected (n, 3) accel window, got {accel_window.shape}")
    if gyro_window.ndim != 2 or gyro_window.shape[1] != 3:
        raise ValueError(f"expected (n, 3) gyro window, got {gyro_window.shape}")

    accel_var = float(np.mean(np.var(accel_window, axis=0)))
    bias = np.zeros(3) if gyro_bias is None else np.asarray(gyro_bias, dtype=float).ravel()
    if bias.shape != (3,):
        raise ValueError(f"expected 3-vector gyro_bias, got {bias.shape}")
    gyro_mean = np.mean(gyro_window, axis=0) - bias
    gyro_norm = float(np.linalg.norm(gyro_mean))
    return accel_var < cfg.zupt_accel_var_thresh and gyro_norm < cfg.zupt_gyro_norm_thresh


def zaru_sigma_from_window(gyro_window: np.ndarray, cfg: FilterConfig) -> np.ndarray:
    """Per-axis ZARU measurement sigma, read from the stop detector's own window (D-131).

    At a standstill the window is bias plus white noise, so its per-axis sample standard
    deviation (ddof = 1) is the noise ZARU's innovation `z = w~ - b_g_hat` carries -- the stop's
    own figure, read causally from the same 2 s `is_stationary` fired on, never a constant.
    Floored at `cfg.zaru_sigma`, the Allan run's desk figure: a stream cannot be quieter than
    its sensor, and a quantised gyro that repeats a value at rest would otherwise report zero.

    Why not a constant, measured on TRAIN against the paired `V-` truth (D-131): the level a
    phone shows at rest in a car is 0.3-1.4 deg/s per axis and it is not one number. Over
    every >= 5 s truth stop the worst-axis white level reads 0.77 deg/s on S1, 5.1 on S4, 5.6
    on M and 30 on S2 -- on M and S2 the phone is not still at its truth stops at all and the
    detector fires on 0 % of them -- while at the samples the detector *does* fire on it reads
    0.70 on S1 and 0.70 on S4. A window of 20 samples estimates its own sigma to about 16 %:
    on S1 the window figure is [0.70, 0.35, 0.59] deg/s per axis against an innovation std of
    [0.72, 0.38, 0.60] at the same 3,066 samples, and the gate then accepts 99.4 % of them
    (0.5 % under the desk figure). Why not the in-motion level `in_motion_config` reads on the
    warm-up: it is 1.52 deg/s on S1 and 2.04 on S4, 2-3x the standstill level -- a different
    physical quantity, and R four to nine times too wide in variance.
    """
    w = np.asarray(gyro_window, dtype=float)
    if w.ndim != 2 or w.shape[1] != 3 or w.shape[0] < 2:
        raise ValueError(f"expected an (n >= 2, 3) gyro window, got {w.shape}")
    return np.maximum(np.std(w, axis=0, ddof=1), float(cfg.zaru_sigma))


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
# Filter -- Sprint 1
# --------------------------------------------------------------------------------------------


class InEKF:
    """Error-state Invariant EKF on SE_2(3).

    Sprint 1 (seat S) implements propagate() and the update family. The interface was fixed before
    the implementation so that seat D could wire the harness against it and seat A could agree the
    FFI surface without waiting.

    **Gating is the caller's job, not this class's.** `is_stationary` and `nhc_is_valid` read the
    raw IMU stream -- accelerometer variance, bias-corrected gyro magnitude (the caller passes
    `gyro_bias=state.b_g`), yaw rate, lateral acceleration -- and none of those is an intrinsic
    property of the state, so the filter cannot check them for itself. The harness calls the
    detector, then the update. ZUPT and ZARU fire **together** at every detected stop: a stop where
    only one runs is a bug, not a tuning choice.
    """

    def __init__(self, cfg: FilterConfig | None = None) -> None:
        self.cfg = cfg or FilterConfig()
        self.state = NavState()
        self.P = initial_covariance(self.cfg)
        #: Steps since the last re-projection of R onto SO(3). See REORTHONORMALISE_EVERY.
        self.steps = 0
        #: When True, hold gyro and accel biases during an outage: propagate zeroes Q_c on the
        #: b_g and b_a blocks before Van Loan, and _apply_update zeroes Kalman gain rows for
        #: IDX_GYRO_BIAS and IDX_ACCEL_BIAS unless explicitly exempted in allow_bias.
        #: ZARU is exempt because it directly observes b_g; constraints that cannot observe
        #: biases (ZUPT, NHC) cannot perturb them. The P bias blocks therefore stay at their
        #: entry value.
        self.hold_biases: bool = False
        #: When True, `b_g` moves only under an update that observes it directly -- ZARU, which
        #: passes `allow_bias=(IDX_GYRO_BIAS,)` -- and every other update's Kalman gain has its
        #: gyro-bias rows zeroed (D-133). Unlike `hold_biases` nothing is done to `Q`: the block's
        #: uncertainty keeps growing at `gyro_bias_rw` between stops, its cross-terms keep
        #: updating, and the next ZARU is weighed against an honest covariance. Why: at a 9 s fix
        #: cadence the Doppler velocity, NHC and position updates cannot separate tilt, heading
        #: and gyro bias, and through the cross-correlations they moved `b_g` 2-3x faster than
        #: the bias walks while the block claimed 0.03 deg/s -- measured on TRAIN S1 against the
        #: truth-standstill bias, a bias-block NEES of 27.3 against 3.0 expected, and 2.1 with
        #: this set. The harness sets it from `eval.run.GYRO_BIAS_DIRECT_ONLY`; it is not a
        #: `FilterConfig` field because it is a policy about which updates are believed, not a
        #: sensor parameter.
        self.gyro_bias_direct_only: bool = False

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
        qc = process_noise_psd(self.cfg)
        if self.hold_biases:
            qc = qc.copy()
            qc[6:12, :] = 0.0
            qc[:, 6:12] = 0.0
        gqg = g @ qc @ g.T

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

    def _apply_update(
        self,
        z: np.ndarray,
        h: np.ndarray,
        r: np.ndarray,
        *,
        allow_bias: tuple[slice, ...] = (),
    ) -> None:
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
        if self.hold_biases:
            if IDX_GYRO_BIAS not in allow_bias:
                gain[IDX_GYRO_BIAS, :] = 0.0
            if IDX_ACCEL_BIAS not in allow_bias:
                gain[IDX_ACCEL_BIAS, :] = 0.0
        if self.gyro_bias_direct_only and IDX_GYRO_BIAS not in allow_bias:
            # A zeroed gain row is a legitimate (sub-optimal) linear estimator, and the Joseph
            # form below gives its exact covariance: the b_g block is left where propagation put
            # it while its cross-terms with the corrected states are updated (D-133).
            gain[IDX_GYRO_BIAS, :] = 0.0
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

    def update_gnss(self, position_ned: np.ndarray, cov: np.ndarray, *, gate: bool = True) -> bool:
        """chi-squared-gated GNSS position update. Returns whether the fix was accepted.

        `gate=False` applies the fix regardless. The caller decides when the gate itself is the
        thing that is wrong -- see `eval.run.GNSS_REJECTIONS_BEFORE_REANCHOR` for the one case
        this repo uses it, and why a run of rejections is evidence against the filter rather
        than against the fixes.

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

        if gate and not chi2_gate(z, h @ self.P @ h.T + cov, self.cfg.chi2_gate_3dof):
            return False
        self._apply_update(z, h, cov)
        return True

    def update_gnss_velocity(self, velocity_ne: np.ndarray, cov: np.ndarray) -> bool:
        """Horizontal GNSS velocity update. Returns whether it was applied.

        The receiver's Doppler course and speed, as one world-frame velocity: `z = v_hat[:2] -
        v_gnss`, `H = [-v_hat^, I, 0, 0, 0, 0]` restricted to the north and east rows -- the
        velocity twin of `update_gnss`, and derived the same way: `v_hat = v + dtheta x v +
        xi_v` under the section 5 error, so the invariant velocity error is observed together
        with the attitude error's action on the velocity. Like the position update, it is never
        called inside an outage; unlike it, one fix of it observes the speed and heading
        *directly*, where nine seconds of position observe their double integral (D-115).

        The vertical row is left out: a phone receiver reports no vertical speed, and the
        vehicle's is asserted zero by NHC in the frame where that is true.

        Gated only when `FilterConfig.gate_gnss_velocity` is set, which by default it is not;
        the reason is with that field. Returns False only for a gated rejection.
        """
        velocity_ne = np.asarray(velocity_ne, dtype=float).ravel()
        cov = np.asarray(cov, dtype=float)
        if velocity_ne.shape != (2,):
            raise ValueError(f"expected a 2-vector horizontal velocity, got {velocity_ne.shape}")
        if cov.shape != (2, 2):
            raise ValueError(f"expected a 2x2 velocity covariance, got {cov.shape}")

        z = self.state.v[:2] - velocity_ne
        h = np.zeros((2, ERROR_STATE_DIM))
        h[:, IDX_ATTITUDE] = -skew(self.state.v)[:2]
        h[:, IDX_VELOCITY] = np.eye(3)[:2]

        if self.cfg.gate_gnss_velocity and not chi2_gate(
            z, h @ self.P @ h.T + cov, self.cfg.chi2_gate_2dof
        ):
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

    def update_zaru(
        self, gyro: np.ndarray, sigma: np.ndarray | float | None = None
    ) -> bool:
        """Zero-angular-rate update, chi-squared gated. Returns whether it was applied.

        Observes gyro bias -- the dominant error term. Offered at *every* detected stop; the
        error budget assumes it is running (docs/ERROR_BUDGET.md section 3.2).

        `gyro` is the **raw** sample for this step, not a bias-corrected one (D-052). Section 7.3
        asserts the true rate is zero, so the raw reading *is* the bias: `z = w~ - b_g_hat`, which
        expands to `-db_g` and gives `H_zaru = [0, 0, 0, -I, 0, 0]`. A **direct** observation of
        `b_g` -- no coupling, no integration, no waiting. Compare section 7.1, where yaw is only
        reachable through a second-order path; this is why ZARU matters more for yaw than NHC.

        **`sigma` is the gyro white noise at *this* stop, per axis** (D-131): the caller reads it
        from the detector's own window with `zaru_sigma_from_window` and passes it here, so
        `R = diag(sigma^2)`. It is floored at `cfg.zaru_sigma`, the Allan run's desk figure,
        which is also what runs when nothing is passed -- the NEES scenario, whose simulated
        sensor is that sensor. Why the desk figure alone was wrong, measured on the real
        stream: at rest in a car the same phone carries 0.3-1.4 deg/s of idle vibration per
        sample (S3a's aided pass: per-axis std [0.33, 1.31, 1.39] deg/s at its truth stops),
        so against R = (0.039 deg/s)^2 the innovation's chi-squared distance sat in the
        hundreds and the gate refused **1,356 of the 1,372 stops the detector found on S3a**
        (241 of 1,524 on S3c, 2 of 739 on Vw2 -- D-130); the bias the whole budget rests on was
        detected and still not observed. With the window's own figure the gate accepts 99.4 % of
        the 3,066 detector-positive standstill samples on TRAIN S1 (0.5 % before), and the
        pull-away samples it now admits -- the trailing window's lag after the truth says
        moving, 0.2-2.7 deg/s, 61 samples over 23 stops -- shift the admitted mean by
        <= 0.008 deg/s against the standstill bias, inside ERROR_BUDGET section 3.2's operating
        row. D-057's synthetic 2.9 deg/s pull-away sample is still refused at S1's level (0.7
        deg/s: chi-squared 15.5) and is admitted at S3a's (1.4 deg/s: 4.1); on the real stems no
        run-out sample reached 2.9 deg/s.

        **The gate is the fix for D-053** (superseded by D-057), and it is not defensive
        programming -- it was measured. `is_stationary` averages over a 0.5 s window, so at the
        step where the vehicle pulls away the window still holds four stopped samples and one
        moving one and the detector still says "stopped". ZARU then fires against a true yaw rate
        of 0.05 rad/s and injects ~7.5e-4 rad/s of pure error into a bias estimate whose sigma is
        1.6e-4 -- and that single sample is the whole of the filter's over-confidence. Measured
        gyro-bias-block NEES over the 60 s reference scenario, 100 runs, 3.0 expected:

            ungated, sigma 1.0e-3   13.14        <- D-053's number
            ungated, sigma measured  9.32
            gated,   sigma measured  3.05        <- in band

        The rejected sample carried a chi-squared distance of **1456** against the repo's own
        3-dof 99% threshold of 11.345, so nothing subtle is being discriminated here. Measured
        rejection rate is 2.0% of offered updates, which is the one transition sample per stop
        plus the ~1% tail the threshold is defined to reject.

        **ZUPT is deliberately *not* gated** (D-057). The same experiment says gating it makes it
        worse, not better: ZUPT-only NEES goes 18.93 -> 44.74, because `zupt_sigma` = 0.02 m/s
        collapses the velocity block until legitimate innovations fall outside the gate and are
        locked out permanently. The asymmetry is physical, not incidental: at the first moving
        sample the vehicle's *speed* is necessarily near zero, so a false ZUPT is nearly harmless,
        whereas its *yaw rate* can be anything a driver turning the wheel while pulling away
        chooses, so a false ZARU is not bounded at all.
        """
        gyro = np.asarray(gyro, dtype=float).ravel()
        if gyro.shape != (3,):
            raise ValueError(f"expected a 3-vector gyro sample, got {gyro.shape}")
        floor = float(self.cfg.zaru_sigma)
        if sigma is None:
            sig = np.full(3, floor)
        else:
            sig = np.asarray(sigma, dtype=float).ravel()
            if sig.shape == (1,):
                sig = np.full(3, sig[0])
            if sig.shape != (3,) or not np.isfinite(sig).all():
                raise ValueError(f"expected a finite scalar or 3-vector ZARU sigma, got {sigma!r}")
            sig = np.maximum(sig, floor)
        h = np.zeros((3, ERROR_STATE_DIM))
        h[:, IDX_GYRO_BIAS] = -np.eye(3)
        z = gyro - self.state.b_g
        r = np.diag(sig**2)
        if not chi2_gate(z, h @ self.P @ h.T + r, self.cfg.chi2_gate_3dof):
            return False
        self._apply_update(z, h, r, allow_bias=(IDX_GYRO_BIAS,))
        return True

    def reinflate_mount(self, sigma_rad: float = MOUNT_KNOCK_RAD) -> None:
        """Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated.

        Call this when `detect_mount_disturbance` fires. Without it the filter carries a stale
        rotation with a covariance that says the rotation is known -- and because `mount_rw` is
        zero (D-048) nothing else will ever widen it again. A 5-degree knock costs ~87 m over a
        60 s outage (docs/ERROR_BUDGET.md section 5) and **nothing else in the system reports it**:
        the phone is still level, the IMU still reads plausibly, the trajectory still looks like a
        drive, and only the mount angle is wrong.

        Variances add: the block's existing uncertainty is kept and the knock's is added on top,
        rather than the block being reset to a fixed value. A reset would *shrink* the covariance
        of a filter that had already lost track, which is the direction that cannot recover.

        The default is section 5's 5 degrees -- the same figure `initial_covariance` uses and the
        magnitude `mount_disturbance_gyro_thresh` is there to catch. It is a stated number, not a
        measured one; a bump's actual angle is not observable from the gyro energy that detected
        it, which is exactly why the covariance is widened rather than the rotation corrected.

        The state is untouched. A knock is news about *uncertainty*, not a measurement of a new
        angle: NHC re-estimates `R_sv` from the widened prior, with gain equal to forward speed
        (section 7.2), so the re-estimation happens on a motorway and barely at all in a car park.
        """
        if sigma_rad <= 0:
            raise ValueError(f"re-inflation sigma must be positive, got {sigma_rad}")
        idx = np.arange(ERROR_STATE_DIM)[IDX_MOUNT]
        self.P[idx, idx] += float(sigma_rad) ** 2

    def update_speed(self, speed_mps: float, variance: float) -> None:
        """Learned forward-speed pseudo-measurement with its predicted variance.

        The variance is not decoration: a confidently wrong covariance corrupts the filter worse
        than a noisy mean, which is what Gate 2 tests.
        """
        raise NotImplementedError("Sprint 2, seat S + M: speed pseudo-measurement")
