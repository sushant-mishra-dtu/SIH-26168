"""The two Gate 1 baselines: naive strapdown INS, and GNSS-available.

Gate 1 is a *ratio* -- physics-only InEKF within 3-5x of the GNSS-available baseline over 60 s
outages -- so both denominators have to exist, and be trustworthy, before the gate is measured.
Neither needs the filter; both are harness work.

**Neither baseline computes a metric.** Both return a `BaselineTrajectory`, and every number comes
out of `eval.metrics.core.evaluate_outage`. A baseline that computed its own drift-% would be a
second definition of the graded quantity, which is the failure the frozen protocol exists to stop.

Protocol: docs/EVALUATION.md sections 3-4. Metrics: eval/metrics/core.py.

--------------------------------------------------------------------------------------------
H-2: **this module contains the one place in the repo where acceleration is double-integrated.**

`naive_strapdown` exists precisely to measure what that costs -- it is the fourth line in every
mandatory 4-trajectory figure and it is what turns docs/ERROR_BUDGET.md section 2's arithmetic
("10 mg of accelerometer bias is 176 m in 60 s") into a measurement. Every name, docstring and
caption here says "naive strapdown" for that reason. It is a **baseline**, never the method, and
nothing in `core/` may import it.
--------------------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.reference.inekf import exp_so3, propagate_nominal
from eval.metrics.core import OutageMetrics, evaluate_outage
from eval.outages.inject import PREDICTION_CADENCE_S, SAMPLE_RATE_HZ, Outage

#: A displacement shorter than this over one epoch carries no usable direction of travel, so the
#: previous heading is held rather than a heading being read out of rounding noise. 1 cm over a 1 s
#: epoch is 0.01 m/s, two orders below `FilterConfig.nhc_min_speed`, which is the repo's existing
#: statement of the speed below which "direction of travel" stops meaning anything.
MIN_HEADING_DISPLACEMENT_M = 0.01


@dataclass(frozen=True)
class BaselineTrajectory:
    """One baseline's answer over one outage window, at the protocol's 1 s prediction cadence.

    `displacements_ned` is `(n_epochs, 2)` -- per-epoch NED displacement, the form
    `eval.metrics.core.per_epoch_errors` consumes, so that a constant offset between two
    trajectories cannot masquerade as a per-epoch error.

    `yaw_rad` is `(n_epochs,)`: the course made good over each epoch. Truth carries no heading
    channel -- `eval.loaders.truth.TRUTH_COLUMNS` is lat, lon and time of day and nothing else, by
    design -- so course over ground from consecutive positions is the *only* heading either side of
    the comparison can have, and both sides are computed the same way by `course_over_ground`.
    """

    displacements_ned: np.ndarray
    yaw_rad: np.ndarray

    def __post_init__(self) -> None:
        d = np.asarray(self.displacements_ned, dtype=float)
        y = np.asarray(self.yaw_rad, dtype=float)
        if d.ndim != 2 or d.shape[1] != 2:
            raise ValueError(f"expected (n, 2) NED displacements, got {d.shape}")
        if y.shape != (d.shape[0],):
            raise ValueError(
                f"yaw must carry one heading per epoch: got {y.shape} for {d.shape[0]} epochs"
            )
        if not np.isfinite(d).all() or not np.isfinite(y).all():
            raise ValueError(
                "non-finite value in a baseline trajectory -- fix the baseline, do not drop them"
            )

    @property
    def n_epochs(self) -> int:
        return int(self.displacements_ned.shape[0])


def course_over_ground(
    displacements_ned: np.ndarray, *, initial_yaw_rad: float = 0.0
) -> np.ndarray:
    """Heading made good over each epoch, radians, from NED displacements.

    Used for **both** sides of every yaw comparison in the harness, which is the point: ground
    truth is a `V-` position track with no heading channel, so a course computed from positions is
    the only heading it can offer. Computing the estimate's heading the same way keeps H-6's yaw
    error a comparison of like with like rather than of a filter's attitude against a derived
    course.

    Where the vehicle did not move far enough for a direction to mean anything the previous
    heading is held, starting from `initial_yaw_rad`. Reading `atan2` off a sub-centimetre
    displacement returns a uniformly-distributed angle, and feeding that into a yaw RMSE produces
    a large error at exactly the moments -- stops -- where heading is least at risk.
    """
    d = np.asarray(displacements_ned, dtype=float)
    if d.ndim != 2 or d.shape[1] != 2:
        raise ValueError(f"expected (n, 2) NED displacements, got {d.shape}")
    moved = np.linalg.norm(d, axis=1) >= MIN_HEADING_DISPLACEMENT_M
    raw = np.arctan2(d[:, 1], d[:, 0])
    out = np.empty(d.shape[0], dtype=float)
    held = float(initial_yaw_rad)
    for i in range(d.shape[0]):
        if moved[i]:
            held = float(raw[i])
        out[i] = held
    return out


def yaw_only_rotation(yaw_rad: float) -> np.ndarray:
    """Navigation-from-body rotation for a level vehicle on a given heading."""
    return exp_so3(np.array([0.0, 0.0, float(yaw_rad)]))


# --------------------------------------------------------------------------------------------
# Baseline 1 -- naive strapdown INS. The one exception to H-2, and it is labelled everywhere.
# --------------------------------------------------------------------------------------------


def naive_strapdown(
    gyro: np.ndarray,
    accel: np.ndarray,
    dt: float,
    *,
    initial_rotation: np.ndarray,
    initial_velocity_ned: np.ndarray,
    epoch_stride: int,
) -> BaselineTrajectory:
    """**Naive strapdown baseline.** Mechanise the raw IMU with no constraints, no learning and no
    aiding, and report where it thinks it went.

    This is the honest "naive dead reckoning" trajectory, and it is the one place in this
    repository where acceleration is double-integrated (H-2's stated exception). Nothing here
    corrects a bias, applies NHC, ZUPT, ZARU or a learned speed, or takes a GNSS fix: `gyro` and
    `accel` go in raw and the errors compound as physics says they must.

    The nominal step is `core.reference.inekf.propagate_nominal` -- the same exact
    `Gamma_0/Gamma_1/Gamma_2` mechanisation the filter propagates with (D-029), already checked
    against the derivation in CI. Reusing it is deliberate: a baseline mechanised differently from
    the method would make every comparison partly a comparison of two integrators, and the
    difference we are trying to show is the *aiding*, not the arithmetic.

    `initial_rotation` and `initial_velocity_ned` are supplied by the caller, and
    `initial_state_from_truth` supplies them from ground truth. That hands this baseline a
    perfect initial heading and speed, which is deliberately generous: it means the drift measured
    here is a **floor** on what no-aiding costs, so nothing in the comparison rests on the
    baseline having been set up to fail.

    `epoch_stride` is IMU samples per 1 s prediction epoch (10 at the `S-` stream's measured rate).
    """
    gyro = np.asarray(gyro, dtype=float)
    accel = np.asarray(accel, dtype=float)
    if gyro.shape != accel.shape or gyro.ndim != 2 or gyro.shape[1] != 3:
        raise ValueError(f"expected matching (n, 3) IMU arrays, got {gyro.shape} and {accel.shape}")
    if epoch_stride < 1:
        raise ValueError(f"epoch_stride must be at least 1 sample, got {epoch_stride}")
    n = gyro.shape[0]
    if n % epoch_stride:
        raise ValueError(
            f"{n} IMU samples is not a whole number of {epoch_stride}-sample epochs. The outage "
            "sweep tiles whole epochs; a partial one means the window was built wrongly."
        )

    rot = np.asarray(initial_rotation, dtype=float).copy()
    v = np.asarray(initial_velocity_ned, dtype=float).ravel().copy()
    p = np.zeros(3)
    positions = [p[:2].copy()]
    for k in range(n):
        rot, v, p = propagate_nominal(rot, v, p, gyro[k], accel[k], dt)
        if (k + 1) % epoch_stride == 0:
            positions.append(p[:2].copy())

    disp = np.diff(np.asarray(positions), axis=0)
    yaw0 = float(np.arctan2(initial_rotation[1, 0], initial_rotation[0, 0]))
    return BaselineTrajectory(disp, course_over_ground(disp, initial_yaw_rad=yaw0))


# --------------------------------------------------------------------------------------------
# Baseline 2 -- GNSS available throughout. The denominator of the Gate 1 ratio.
# --------------------------------------------------------------------------------------------


def gnss_available(
    fix_times_s: np.ndarray,
    fix_ned: np.ndarray,
    epoch_times_s: np.ndarray,
    *,
    initial_yaw_rad: float = 0.0,
) -> BaselineTrajectory:
    """**GNSS-available baseline.** What the system reports when the signal is never denied.

    The estimate at an epoch boundary is the most recent fix at or before it -- a zero-order hold,
    never an interpolation. That is not a simplification, it is the measurement: a receiver that
    has not updated has not moved its answer, and interpolating between two fixes would
    manufacture positions the instrument never reported. `eval.loaders.truth.TruthTrack.index_at`
    refuses interpolation for the same reason and says so at length.

    **Read the cadence before reading the number.** The `S-` smartphone GPS updates at a measured
    median of 9.0 s, not the 1 Hz the protocol was drafted against
    (`eval.loaders.io_vnbd.GNSS_MEDIAN_INTERVAL_S`), so across a 60 s window this baseline holds
    its answer for eight epochs out of nine and then steps. Its per-epoch CTE and CRSE are
    therefore dominated by that staircase and are **not** a statement about GPS accuracy; its
    drift-%, which is measured at the window boundary against the paired `V-` truth, is. This is
    what a phone-only system actually has available, which is what makes it the right denominator
    for Gate 1 -- but quoting its CRSE beside the filter's without this paragraph would be
    comparing a staircase to a curve.

    `fix_ned` is `(n_fixes, 2)` in the same local frame as `epoch_times_s`' expected output, and
    both time arrays are on one clock. Raises if the window opens before the first fix: there is
    nothing to hold, and holding a *later* fix backwards would leak future information into an
    epoch that did not have it.
    """
    t_fix = np.asarray(fix_times_s, dtype=float).ravel()
    ned = np.asarray(fix_ned, dtype=float)
    t_epoch = np.asarray(epoch_times_s, dtype=float).ravel()
    if ned.ndim != 2 or ned.shape[1] != 2 or ned.shape[0] != t_fix.size:
        raise ValueError(f"expected ({t_fix.size}, 2) fix positions, got {ned.shape}")
    if t_fix.size == 0:
        raise ValueError("no GNSS fixes: the GNSS-available baseline has nothing to report")
    if not np.all(np.diff(t_fix) > 0):
        raise ValueError("fix times must be strictly increasing; sort or reject the file")
    if t_epoch.size < 2:
        raise ValueError("need at least two epoch boundaries to form one displacement")
    if t_epoch[0] < t_fix[0]:
        raise ValueError(
            f"window opens at t = {t_epoch[0]:.3f} s, before the first fix at {t_fix[0]:.3f} s. "
            "There is no fix to hold, and holding a later one backwards would give this epoch "
            "information it did not have."
        )

    held = np.searchsorted(t_fix, t_epoch, side="right") - 1
    disp = np.diff(ned[held], axis=0)
    return BaselineTrajectory(disp, course_over_ground(disp, initial_yaw_rad=initial_yaw_rad))


# --------------------------------------------------------------------------------------------
# Window runners -- assemble a baseline against the frozen protocol and hand it to the metrics
# --------------------------------------------------------------------------------------------


def epoch_times(
    t_start_s: float, length_s: int, *, cadence_s: int = PREDICTION_CADENCE_S
) -> np.ndarray:
    """Epoch boundary times for one outage window: `length_s // cadence_s + 1` of them.

    Boundaries, not epochs: `n + 1` positions give the `n` displacements the metrics consume.
    """
    n = length_s // cadence_s
    return t_start_s + np.arange(n + 1, dtype=float) * cadence_s


def initial_state_from_truth(truth, t_start_s: float) -> tuple[np.ndarray, np.ndarray]:
    """`(R0, v0)` for the naive strapdown baseline, taken from ground truth at the outage start.

    Deliberately generous to the baseline, as `naive_strapdown` explains. Heading is the truth
    course over the first epoch and the vehicle is assumed level -- there is no roll or pitch
    channel in the truth track to do better, and a level assumption is the standard coarse
    alignment. Velocity is the truth displacement over that same epoch.
    """
    ned = truth.ned_at(np.array([t_start_s, t_start_s + PREDICTION_CADENCE_S]))
    step = ned[1] - ned[0]
    moved = float(np.linalg.norm(step)) >= MIN_HEADING_DISPLACEMENT_M
    yaw = float(np.arctan2(step[1], step[0])) if moved else 0.0
    v0 = np.array([step[0], step[1], 0.0]) / PREDICTION_CADENCE_S
    return yaw_only_rotation(yaw), v0


def score(trajectory: BaselineTrajectory, truth, outage: Outage) -> OutageMetrics:
    """Score any baseline against the paired `V-` truth over one window.

    Every number comes from `eval.metrics.core.evaluate_outage`; nothing is recomputed here. The
    truth heading is `course_over_ground` on the truth's own displacements -- the same function the
    baseline used -- because the truth track carries lat, lon and time of day and no heading.
    """
    t0 = outage.start_idx / SAMPLE_RATE_HZ
    times = epoch_times(t0, outage.length_s)
    true_disp = truth.displacements_ned(times)
    return evaluate_outage(
        est_disp=trajectory.displacements_ned,
        true_disp=true_disp,
        est_yaw=trajectory.yaw_rad,
        true_yaw=course_over_ground(true_disp),
        distance_m=truth.distance_m(times[0], times[-1]),
        duration_s=float(outage.length_s),
    )
