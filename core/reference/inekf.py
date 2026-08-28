"""Reference InEKF on SE_2(3) -- state layout, gating, and interfaces.

**This is the screening prototype.** The C++/Rust core (DECISION_LOG D-011) mirrors this file
exactly and reuses its tests; the Python version exists so Gate 1 can be hit inside the compressed
schedule, not to replace the compiled core.

Propagation and the update step are deliberately left unimplemented -- that is Sprint 1 work and
writing it speculatively here would produce a filter nobody has reasoned through. What *is* settled
and encoded below is the part that is easy to get quietly wrong later: the state layout, the
constraint gating conditions, and the rule that GNSS is never a mode switch.

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

    # NHC: lateral and vertical body velocity are ~0. Loose defaults; the AI-IMU CNN replaces
    # these with a per-step prediction once seat M's adaptive head lands (D-005).
    nhc_sigma_lateral: float = 0.5  # m/s
    nhc_sigma_vertical: float = 0.5  # m/s

    zupt_sigma: float = 0.02  # m/s
    zaru_sigma: float = 1.0e-3  # rad/s

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
# Detectors -- implemented, because they are simple and everything else depends on them
# --------------------------------------------------------------------------------------------


def is_stationary(accel_window: np.ndarray, gyro_window: np.ndarray, cfg: FilterConfig) -> bool:
    """Detect a stopped vehicle for ZUPT/ZARU.

    Both conditions must hold: low accelerometer variance *and* low gyro magnitude. Variance
    rather than magnitude on the accelerometer because gravity dominates its magnitude at all
    times; a stationary phone still reads ~9.8 m/s^2.
    """
    accel_window = np.asarray(accel_window, dtype=float)
    gyro_window = np.asarray(gyro_window, dtype=float)
    if accel_window.ndim != 2 or accel_window.shape[1] != 3:
        raise ValueError(f"expected (n, 3) accel window, got {accel_window.shape}")

    accel_var = float(np.mean(np.var(accel_window, axis=0)))
    gyro_norm = float(np.mean(np.linalg.norm(gyro_window, axis=1)))
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
# Filter -- Sprint 1
# --------------------------------------------------------------------------------------------


class InEKF:
    """Error-state Invariant EKF on SE_2(3).

    Sprint 1 (seat S) implements propagate() and the update family. The interface is fixed here so
    that seat D can wire the harness against it now and seat A can agree the FFI surface, both
    without waiting on the implementation.
    """

    def __init__(self, cfg: FilterConfig | None = None) -> None:
        self.cfg = cfg or FilterConfig()
        self.state = NavState()
        self.P = np.eye(ERROR_STATE_DIM) * 1e-3

    def propagate(self, gyro: np.ndarray, accel: np.ndarray, dt: float) -> None:
        """IMU propagation. Always runs, GNSS or not -- this is the spine.

        `dt` comes from real timestamps. Never a nominal value: sensor timestamps jitter and
        batch, and assuming 1/100 s silently integrates the wrong interval (D-013).
        """
        raise NotImplementedError("Sprint 1, seat S: SE_2(3) propagation with bias states")

    def update_gnss(self, position_ned: np.ndarray, cov: np.ndarray) -> bool:
        """chi-squared-gated GNSS position update. Returns whether the fix was accepted.

        Not called at all during an injected outage -- see eval/outages/inject.mask_gnss.
        """
        raise NotImplementedError("Sprint 1, seat S: gated position update")

    def update_nhc(self, r_nhc: np.ndarray | None = None) -> None:
        """Non-holonomic pseudo-measurement. Caller checks nhc_is_valid() first.

        `r_nhc` is the per-step covariance from the AI-IMU adaptive head once it exists; None
        falls back to the fixed config values.
        """
        raise NotImplementedError("Sprint 1, seat S: NHC pseudo-measurement")

    def update_zupt(self) -> None:
        """Zero-velocity update. Observes accelerometer bias."""
        raise NotImplementedError("Sprint 1, seat S: ZUPT")

    def update_zaru(self) -> None:
        """Zero-angular-rate update. Observes gyro bias -- the dominant error term.

        Apply at *every* detected stop. This is the cheapest yaw-drift mitigation available and
        the error budget assumes it is running (docs/ERROR_BUDGET.md section 3.2).
        """
        raise NotImplementedError("Sprint 1, seat S: ZARU")

    def update_speed(self, speed_mps: float, variance: float) -> None:
        """Learned forward-speed pseudo-measurement with its predicted variance.

        The variance is not decoration: a confidently wrong covariance corrupts the filter worse
        than a noisy mean, which is what Gate 2 tests.
        """
        raise NotImplementedError("Sprint 2, seat S + M: speed pseudo-measurement")
