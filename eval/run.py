"""Harness entry point. One command regenerates every number.

    idr-eval --data data/IO-VNBD --seed 0 --out eval/figures

If regenerating the results needs manual steps, the figures will silently drift from the numbers
in the text. That is the failure this file exists to prevent.

Three trajectories are produced per outage window and scored through the same metrics path:

    filter           the physics-only InEKF -- IMU propagation, NHC, ZUPT, ZARU, gated GNSS
    strapdown        the naive strapdown baseline (eval/baselines.py)
    gnss_available   the zero-order-hold GNSS baseline, the Gate 1 denominator

**Gate 1 is the ratio of the first to the third, on median drift-%, at 60 s. The gate is 3-5x.**
It is reported here as a measured number and it is not this file's job to decide whether it passed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from core.reference.inekf import (
    FilterConfig,
    InEKF,
    initial_covariance,
    is_stationary,
    nhc_is_valid,
    pca_mount_yaw,
)
from eval.baselines import (
    MIN_HEADING_DISPLACEMENT_M,
    BaselineTrajectory,
    course_over_ground,
    gnss_available,
    initial_state_from_truth,
    naive_strapdown,
    score,
    yaw_only_rotation,
)
from eval.loaders.io_vnbd import SAMPLE_RATE_HZ, Sequence, load_split
from eval.loaders.truth import (
    TruthPairingError,
    align_to_sequence,
    load_truth,
    paired_truth_path,
)
from eval.metrics.core import (
    CRSE_CONVENTION,
    OutageMetrics,
    ZeroDistanceOutage,
    summarise,
)
from eval.outages.inject import (
    OUTAGE_LENGTHS_S,
    PREDICTION_CADENCE_S,
    Outage,
    assert_non_overlapping,
    generate_sweep,
    mask_gnss,
)
from eval.splits import (
    LONG_OUTAGE,
    MANDATORY_PLOT_SEQUENCES,
    assert_split_disjoint,
    assert_split_is_loadable,
    test_sequences,
)
from idr.geo import geodetic_to_ned, wrap_to_pi
from idr.stamp import Stamp, seed_everything

DEFAULT_SEED = 0

#: IMU samples per 1 s prediction epoch, at the `S-` stream's measured 10 Hz.
EPOCH_STRIDE = SAMPLE_RATE_HZ * PREDICTION_CADENCE_S

#: The three methods, in the order every figure and table lists them.
METHODS = ("filter", "strapdown", "gnss_available")

#: Gate 1: physics-only within this many times the GNSS-available baseline over 60 s outages.
GATE1_RATIO_RANGE = (3.0, 5.0)
GATE1_LENGTH_S = 60

#: How far the per-sample interval may stray from nominal before the sequence is refused rather
#: than integrated. The loader measures a median of exactly 100.0 ms; a file that wanders outside
#: this is not the 10 Hz stream the outage sweep tiles in sample indices, and integrating it would
#: put every epoch boundary somewhere other than where the truth lookup expects it.
MAX_DT_DEVIATION_S = 0.05


class SequenceUnusable(RuntimeError):
    """This stem cannot be graded, and the run says so rather than reporting a number anyway."""


# --------------------------------------------------------------------------------------------
# Reading a loaded Sequence into the arrays the filter and the baselines consume
# --------------------------------------------------------------------------------------------


def imu_stream(seq: Sequence) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`(gyro, accel, t_rel_s)` for one sequence: `(n, 3)`, `(n, 3)`, `(n,)`.

    Axis mapping is the one D-047 established: the shipped `GYROSCOPE Yaw/Pitch/Roll` columns are
    AndroSensor's labels for device x/y/z and are byte-identical to the `GYROSCOPE X/Y/Z` spelling
    in the other folder, so `gyro_yaw` is device **x**, not the vertical axis. Getting this wrong
    is silent: the filter still runs and the trajectory still looks like a drive.

    `t_rel_s` comes from the stream's own `time_since_start_ms`. Never a nominal 1/10 s: sensor
    timestamps jitter and batch, and five `S-` stems restart their clock mid-recording (D-013).
    """
    imu = seq.imu
    needed = ["gyro_yaw", "gyro_pitch", "gyro_roll", "accel_x", "accel_y", "accel_z"]
    missing = [c for c in needed if c not in imu.columns]
    if missing:
        raise SequenceUnusable(f"{seq.name}: inertial channel(s) {missing} absent after loading")
    if "time_since_start_ms" not in imu.columns:
        raise SequenceUnusable(
            f"{seq.name}: no 'time_since_start_ms' column, so dt cannot come from real "
            "timestamps. Propagating on a nominal interval integrates the wrong dt silently."
        )

    gyro = imu[["gyro_yaw", "gyro_pitch", "gyro_roll"]].to_numpy(dtype=float)
    accel = imu[["accel_x", "accel_y", "accel_z"]].to_numpy(dtype=float)
    t_rel_s = imu["time_since_start_ms"].to_numpy(dtype=float) / 1000.0
    if not np.isfinite(gyro).all() or not np.isfinite(accel).all():
        raise SequenceUnusable(
            f"{seq.name}: non-finite inertial samples. Fix the loader; do not propagate over them."
        )
    return gyro, accel, t_rel_s


def assert_uniform_grid(seq_name: str, t_rel_s: np.ndarray) -> np.ndarray:
    """Per-sample `dt`, refusing a stream that is not the 10 Hz grid the sweep assumes.

    `eval/outages/inject.py` tiles outages in **sample indices** and `epoch_times` converts them to
    seconds by dividing by 10, so a stream whose samples are not 0.1 s apart puts every epoch
    boundary somewhere other than where the truth lookup goes to find it. A clock that runs
    backwards is the same failure, louder.
    """
    dt = np.diff(t_rel_s)
    if dt.size == 0:
        raise SequenceUnusable(f"{seq_name}: fewer than two samples")
    if np.any(dt <= 0):
        first = int(np.argmax(dt <= 0))
        raise SequenceUnusable(
            f"{seq_name}: timestamps go backwards at sample {first + 1} "
            f"(dt = {dt[first]:.4f} s). Five `S-` stems restart their clock mid-recording; this "
            "one cannot be integrated as a single sequence."
        )
    nominal = 1.0 / SAMPLE_RATE_HZ
    worst = float(np.max(np.abs(dt - nominal)))
    if worst > MAX_DT_DEVIATION_S:
        raise SequenceUnusable(
            f"{seq_name}: sample interval strays {worst:.3f} s from the nominal {nominal:.3f} s. "
            "The outage sweep tiles in sample indices and converts to seconds at 10 Hz, so this "
            "stream's epoch boundaries would not land where the truth lookup expects them."
        )
    return dt


def truth_clock_offset_s(seq: Sequence) -> float:
    """Seconds to add to a sequence-relative time to put it on the truth track's clock.

    The two streams carry different clocks -- `S-` counts milliseconds from the start of the
    recording, `V-` counts seconds since midnight -- and `eval/loaders/truth.py` anchors the
    difference deliberately so neither can be mistaken for the other. The fixes carry both, so the
    offset is theirs to supply. The **median** over all fixes rather than the first one: a single
    anchor makes the whole sequence's alignment depend on one row's timestamp.
    """
    from eval.loaders.truth import seconds_of_day_utc

    gnss = seq.gnss
    if "date" not in gnss.columns or "time_since_start_ms" not in gnss.columns:
        raise SequenceUnusable(
            f"{seq.name}: fixes carry no 'date'/'time_since_start_ms' pair, so the `S-` clock "
            "cannot be placed against the `V-` truth clock."
        )
    tod = seconds_of_day_utc(gnss["date"].tolist())
    rel = gnss["time_since_start_ms"].to_numpy(dtype=float) / 1000.0
    finite = np.isfinite(tod) & np.isfinite(rel)
    if not finite.any():
        raise SequenceUnusable(f"{seq.name}: no fix carries both a date and a relative timestamp")
    return float(np.median(tod[finite] - rel[finite]))


def fix_arrays(
    seq: Sequence, lat0: float, lon0: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`(sample_idx, ned (n, 3), sigma_m (n,))` for the distinct `S-` GPS fixes.

    These are the **gated filter update**, not truth. `eval/loaders/io_vnbd.py` already reduces
    them to one row per position change; forward-filling them into a per-sample column is what the
    loader refuses to do and this must not undo.

    `sigma_m` is the receiver's own reported `gps_accuracy_m` where the file carries it, so the
    covariance the gate reads is the phone's own statement about the fix rather than a constant.
    Where it is absent the config default stands.
    """
    gnss = seq.gnss
    idx = gnss["sample_idx"].to_numpy(dtype=int)
    ned2 = geodetic_to_ned(
        gnss["gps_lat"].to_numpy(dtype=float), gnss["gps_lon"].to_numpy(dtype=float), lat0, lon0
    )
    if "gps_altitude_m" in gnss.columns:
        alt = gnss["gps_altitude_m"].to_numpy(dtype=float)
        down = -(alt - alt[0])
        down = np.where(np.isfinite(down), down, 0.0)
    else:
        down = np.zeros(idx.size)
    ned = np.column_stack([ned2, down])

    default = FilterConfig().gnss_sigma_m
    if "gps_accuracy_m" in gnss.columns:
        sigma = gnss["gps_accuracy_m"].to_numpy(dtype=float)
        sigma = np.where(np.isfinite(sigma) & (sigma > 0), sigma, default)
    else:
        sigma = np.full(idx.size, default)
    return idx, ned, sigma


# --------------------------------------------------------------------------------------------
# The filter run -- one pass per sequence per outage length
# --------------------------------------------------------------------------------------------


@dataclass
class FilterRun:
    """Everything one pass of the filter produced, at every sample."""

    position_ned: np.ndarray  # (n, 2)
    yaw_rad: np.ndarray  # (n,) the filter's own attitude yaw, for H-6 diagnostics
    position_var: np.ndarray  # (n, 2) diagonal of the position covariance block
    n_gnss_applied: int
    n_gnss_rejected: int
    n_zupt: int
    n_zaru_applied: int
    n_zaru_rejected: int
    n_nhc: int
    #: How the filter was started (D-094), or None when `run_filter` was called without a
    #: `Sequence` -- which only the unit tests do, on fixtures where `R_sv = I` is correct.
    init: FilterInit | None = None


def run_filter(
    gyro: np.ndarray,
    accel: np.ndarray,
    dt: np.ndarray,
    fix_idx: np.ndarray,
    fix_ned: np.ndarray,
    fix_sigma: np.ndarray,
    gnss_open: np.ndarray,
    *,
    cfg: FilterConfig | None = None,
    seq: Sequence | None = None,
) -> FilterRun:
    """Drive the InEKF across one whole sequence, applying GNSS only where `gnss_open` is True.

    **There is no outage branch here, and that absence is the architectural claim.** During an
    injected outage the GNSS update is simply not called, exactly as `mask_gnss` describes; nothing
    switches mode, nothing re-initialises, and re-acquisition is an ordinary gated update. A
    rejected fix (multipath on tunnel exit) takes the same path as a masked one -- see D-001 and
    `InEKF.update_gnss`.

    Gating is the caller's job, per the filter's own contract: `is_stationary` and `nhc_is_valid`
    read the raw IMU stream, which is not a property of the state. ZUPT and ZARU are **offered
    together** at every detected stop (D-004); ZARU may decline at its own χ² gate (D-057), which
    is counted separately so a run can be read for how often that happens.
    """
    cfg = cfg or FilterConfig()
    f = InEKF(cfg)
    n = gyro.shape[0]

    # **Before the first propagate, not after it.** See `initialise_filter`: starting from
    # R = R_sv = I integrates gravity into the horizontal axes and the run diverges (D-094).
    init = None if seq is None else initialise_filter(f, seq, accel, fix_idx, fix_ned)

    fix_at = {int(i): k for k, i in enumerate(fix_idx)}
    window = max(1, int(round(cfg.zupt_window_s * SAMPLE_RATE_HZ)))

    pos = np.zeros((n, 2))
    yaw = np.zeros(n)
    pvar = np.zeros((n, 2))
    counts = dict(gnss_ok=0, gnss_no=0, zupt=0, zaru_ok=0, zaru_no=0, nhc=0)

    for k in range(n):
        if k > 0:
            f.propagate(gyro[k], accel[k], float(dt[k - 1]))

        lo = max(0, k - window + 1)
        if k + 1 >= window and is_stationary(accel[lo : k + 1], gyro[lo : k + 1], cfg):
            f.update_zupt()
            counts["zupt"] += 1
            if f.update_zaru(gyro[k]):
                counts["zaru_ok"] += 1
            else:
                counts["zaru_no"] += 1
        elif nhc_is_valid(
            float(np.linalg.norm(f.state.v)),
            float(gyro[k][2] - f.state.b_g[2]),
            float(accel[k][1] - f.state.b_a[1]),
            cfg,
        ):
            f.update_nhc()
            counts["nhc"] += 1

        j = fix_at.get(k)
        if j is not None and gnss_open[k]:
            cov = np.eye(3) * float(fix_sigma[j]) ** 2
            if f.update_gnss(fix_ned[j], cov):
                counts["gnss_ok"] += 1
            else:
                counts["gnss_no"] += 1

        pos[k] = f.state.p[:2]
        yaw[k] = f.state.yaw
        pvar[k] = np.diag(f.P)[6:8]

    return FilterRun(
        init=init,
        position_ned=pos,
        yaw_rad=yaw,
        position_var=pvar,
        n_gnss_applied=counts["gnss_ok"],
        n_gnss_rejected=counts["gnss_no"],
        n_zupt=counts["zupt"],
        n_zaru_applied=counts["zaru_ok"],
        n_zaru_rejected=counts["zaru_no"],
        n_nhc=counts["nhc"],
    )


#: The GNSS-available run-up `generate_outages` leaves before the first window. The initialiser
#: may read this and nothing after it: every outage starts later, so using a sample from beyond it
#: would be initialising a window with its own future.
WARMUP_S = 30


@dataclass(frozen=True)
class FilterInit:
    """What the filter was started from, so a run can be read for whether it was started well."""

    yaw_rad: float
    speed_mps: float
    mount_yaw_rad: float
    mount_spread_rad: float
    mount_sign_resolved: bool
    n_warmup_fixes: int


def _forward_reference(seq: Sequence, n: int) -> np.ndarray | None:
    """A per-sample signed scalar that grows with forward acceleration, from `gps_speed_kmh`.

    `pca_mount_yaw` returns an *axis*, and forward and backward share it. This resolves the sign,
    and it has to be resolved rather than assumed: a 180-degree mount error is a vehicle driving
    backwards and NHC will not converge it out.

    The fixes are ~9 s apart, so this is a step function -- the mean forward acceleration across
    each fix interval, held over that interval's samples. That is coarse for a magnitude and
    entirely adequate for a sign, which is all `pca_mount_yaw` uses it for.
    """
    gnss = seq.gnss
    if "gps_speed_kmh" not in gnss.columns:
        return None
    idx = gnss["sample_idx"].to_numpy(dtype=int)
    speed = gnss["gps_speed_kmh"].to_numpy(dtype=float) / 3.6
    ok = np.isfinite(speed) & (idx >= 0) & (idx < n)
    idx, speed = idx[ok], speed[ok]
    if idx.size < 2:
        return None

    out = np.zeros(n)
    dt_s = np.diff(idx) / SAMPLE_RATE_HZ
    accel_fwd = np.divide(
        np.diff(speed), dt_s, out=np.zeros(dt_s.shape), where=dt_s > 0
    )
    for a, lo, hi in zip(accel_fwd, idx[:-1], idx[1:], strict=True):
        out[lo:hi] = a
    return out


def initialise_filter(
    f: InEKF,
    seq: Sequence,
    accel: np.ndarray,
    fix_idx: np.ndarray,
    fix_ned: np.ndarray,
    *,
    warmup_s: int = WARMUP_S,
) -> FilterInit:
    """Start the filter from the `S-` stream's own GNSS and gravity, never from truth.

    **Without this the filter does not converge, it diverges.** `run_filter` used to construct
    `InEKF(cfg)` and propagate from `R = I`, `R_sv = I`, `v = 0`, `p = 0`. A phone in a cradle is
    not aligned with the vehicle and the vehicle is not aligned with north, so gravity leaks into
    the horizontal axes and is integrated twice: measured on S3a, `norm(v)` reached **1223 m/s at
    100 s** -- a sustained 12.2 m/s^2, about 1 g -- and the state then sat so far from every fix
    that the chi-squared gate rejected **59 of 60** of them, locking out the only correction until
    `P` ran away to 1e70 and `np.linalg.inv` raised. See D-094.

    Truth is not read here and must not be. `eval.baselines.initial_state_from_truth` exists for
    the *strapdown baseline*, which is deliberately handed truth (D-064) because it is a floor
    rather than a system; the filter is the system, and it gets what a phone would have.

    Four things, all from inside the warmup window:

    * **Position** -- the first fix. It is the measurement, not an estimate of one.
    * **Velocity and yaw** -- the first and last warmup fixes, differenced. Course over ground
      needs motion, so if the vehicle has not moved far enough to have a heading the yaw prior
      stands at zero and `initial_covariance`'s 14.56-degree block carries it.
    * **`R_sv`** -- `pca_mount_yaw` over the warmup accelerometer and the stream's own `GRAVITY`
      channel, which D-085 established points up. This is D-073's initialiser, which until now was
      called from `tests/test_mount.py` and nowhere else.
    * **`P0`** -- `initial_covariance` with the PCA's measured `spread_rad` in the mount block,
      instead of the stated 5-degree fallback it uses when nobody has measured one.
    """
    n_warm = min(int(warmup_s * SAMPLE_RATE_HZ), accel.shape[0])
    in_warmup = np.flatnonzero((fix_idx >= 0) & (fix_idx < n_warm))

    # The mount comes first, because the attitude is expressed through it -- see below.
    mount_spread: float | None = None
    mount_yaw = 0.0
    resolved = False
    gravity_cols = ["gravity_x", "gravity_y", "gravity_z"]
    if all(c in seq.imu.columns for c in gravity_cols) and n_warm >= 3:
        gravity = seq.imu[gravity_cols].to_numpy(dtype=float)[:n_warm]
        finite = np.isfinite(gravity).all(axis=1)
        if finite.sum() >= 3:
            reference = _forward_reference(seq, accel.shape[0])
            mount = pca_mount_yaw(
                accel[:n_warm][finite],
                gravity[finite].mean(axis=0),
                forward_reference=None if reference is None else reference[:n_warm][finite],
            )
            # An unresolved sign is reported, never guessed -- see `pca_mount_yaw`. The rotation
            # is still applied: PCA has found the mount *axis*, which is most of the answer, and
            # `mount_sign_resolved` travels to `summary.json` so a run made on an unresolved stem
            # can be read as one.
            f.state.R_sv = mount.r_sv
            mount_spread = mount.spread_rad
            mount_yaw = mount.yaw_rad
            resolved = mount.sign_resolved

    yaw = 0.0
    speed = 0.0
    if in_warmup.size:
        f.state.p = np.asarray(fix_ned[in_warmup[0]], dtype=float).copy()
    if in_warmup.size >= 2:
        first, last = in_warmup[0], in_warmup[-1]
        step = np.asarray(fix_ned[last], dtype=float) - np.asarray(fix_ned[first], dtype=float)
        span_s = float(fix_idx[last] - fix_idx[first]) / SAMPLE_RATE_HZ
        if span_s > 0 and float(np.linalg.norm(step[:2])) >= MIN_HEADING_DISPLACEMENT_M:
            yaw = float(np.arctan2(step[1], step[0]))
            f.state.v = np.array([step[0] / span_s, step[1] / span_s, 0.0])
            speed = float(np.linalg.norm(f.state.v[:2]))

    # **`state.R` is phone->NED, not vehicle->NED**, and getting that wrong is a 1 g error rather
    # than a small one. `_h_vehicle_velocity` computes `v_veh = R_sv @ R.T @ v`, so `R.T` takes NED
    # into the *phone* frame and `R_sv` takes phone into the vehicle; and `propagate` applies `R`
    # to the raw accelerometer, which is a phone-frame quantity. Course over ground measures the
    # **vehicle's** heading, so the phone's attitude is that composed with the mount:
    # `v_ned = R_vn @ R_sv @ v_phone`, hence `R = R_vn @ R_sv`. Setting `R = R_vn` alone leaves the
    # mount rotation out of the gravity cancellation, and the leaked component is integrated twice
    # -- measured at 12.2 m/s^2 on S3a, which is what D-094 is about.
    f.state.R = yaw_only_rotation(yaw) @ f.state.R_sv

    f.P = initial_covariance(f.cfg, mount_sigma_rad=mount_spread)
    return FilterInit(
        yaw_rad=yaw,
        speed_mps=speed,
        mount_yaw_rad=mount_yaw,
        mount_spread_rad=float("nan") if mount_spread is None else mount_spread,
        mount_sign_resolved=resolved,
        n_warmup_fixes=int(in_warmup.size),
    )


def window_trajectory(position_ned: np.ndarray, outage: Outage) -> BaselineTrajectory:
    """Slice one outage window's epoch boundaries out of a whole-sequence position series."""
    idx = np.arange(outage.start_idx, outage.end_idx + 1, EPOCH_STRIDE)
    if idx[-1] != outage.end_idx:
        raise ValueError(
            f"outage [{outage.start_idx}, {outage.end_idx}) is not a whole number of "
            f"{EPOCH_STRIDE}-sample epochs"
        )
    if idx[-1] >= position_ned.shape[0]:
        raise ValueError(f"outage window runs past the end of the sequence at sample {idx[-1]}")
    disp = np.diff(position_ned[idx], axis=0)
    return BaselineTrajectory(disp, course_over_ground(disp))


# --------------------------------------------------------------------------------------------
# Per-sequence evaluation
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class WindowResult:
    method: str
    sequence: str
    length_s: int
    start_idx: int
    metrics: OutageMetrics

    def as_row(self) -> dict[str, object]:
        return {
            "method": self.method,
            "sequence": self.sequence,
            "length_s": self.length_s,
            "start_idx": self.start_idx,
            **self.metrics.as_row(),
        }


@dataclass(frozen=True)
class DroppedWindow:
    """One outage window the paired `V-` track does not cover, and why (D-089).

    A dropped window is **not** a failed sequence. `align_to_sequence` refusing a stem says the
    two files do not describe the same drive, and the whole stem goes. A `TruthPairingError` here
    says a handful of epochs inside one window have no truth sample within
    `eval.loaders.truth.MAX_EPOCH_OFFSET_S`, which is a statement about those epochs only -- so
    the window goes and the rest of the stem still grades.
    """

    sequence: str
    length_s: int
    start_idx: int
    #: "no_truth_coverage" (D-089) or "zero_distance" (D-093). Broken out so the summary says
    #: *why* a window went: a gap in the truth track and a parked vehicle are different findings
    #: and a single total would conflate a pairing problem with an ordinary traffic light.
    kind: str
    reason: str

    def as_row(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "length_s": self.length_s,
            "start_idx": self.start_idx,
            "kind": self.kind,
            "reason": self.reason,
        }


def evaluate_sequence(
    seq: Sequence,
    truth,
    lengths: list[int],
    *,
    cfg: FilterConfig | None = None,
    replay: dict | None = None,
    stamp: Stamp | None = None,
    dropped: list[DroppedWindow] | None = None,
) -> list[WindowResult]:
    """Every window of every length for one sequence, all three methods.

    One filter pass **per outage length**, because the GNSS mask differs between lengths and a
    single pass cannot have GNSS both open and closed at the same sample.

    If `replay` is a dict and this sequence is in `MANDATORY_PLOT_SEQUENCES`, the first
    `REPLAY_LENGTH_S` window is recorded into it for the renderer, stamped with `stamp`. First
    rather than a chosen one: picking the window that plots best is the same error as picking the
    sequence that scores best.

    If `dropped` is a list, any window the truth track does not cover is appended to it as a
    `DroppedWindow` and contributes nothing to the results (D-089). An out-parameter rather than a
    second return value for the same reason `replay` is one: every existing caller stays a call
    that returns `list[WindowResult]`, and a caller that does not pass a sink is not silently
    handed a count it will not report.
    """
    if replay is not None and stamp is None:
        raise ValueError(
            "a replay record must carry the run's stamp; an artefact whose provenance came from a "
            "placeholder is one nobody can regenerate (H-5)"
        )
    cfg = cfg or FilterConfig()
    report = align_to_sequence(seq, truth)
    if not report.is_usable:
        raise SequenceUnusable(
            f"{seq.name}: the paired `V-` track is not usable as truth -- median residual "
            f"{report.residual_median_m:.1f} m at lag {report.best_lag_s:+.2f} s over "
            f"{report.n_matched}/{report.n_s_fixes} fixes, monotonic={report.s_time_is_monotonic}. "
            "Drop the stem from the protocol; do not grade against a track that does not describe "
            "this drive."
        )

    gyro, accel, t_rel_s = imu_stream(seq)
    dt = assert_uniform_grid(seq.name, t_rel_s)
    offset = truth_clock_offset_s(seq)
    # Absolute time of day per sample. **Not** `index / SAMPLE_RATE_HZ + offset`: eleven of the
    # fourteen held-out stems are excerpts cut from a longer recording and keep that recording's
    # clock, so `time_since_start_ms` opens at 1118 s on Vta11 and 13365 s on Vw8 rather than at
    # zero. Deriving the epoch from the row index instead of the row's own timestamp shifts the
    # window by exactly that opening value -- up to 3.7 hours -- and grades the drive against a
    # stretch of road it never travelled.
    t_abs_s = t_rel_s + offset
    fix_idx, fix_ned, fix_sigma = fix_arrays(seq, float(truth.lat[0]), float(truth.lon[0]))

    n = gyro.shape[0]
    sweep = generate_sweep({seq.name: n}, tuple(lengths))
    out: list[WindowResult] = []

    for length_s, windows in sorted(sweep.items()):
        if not windows:
            continue
        assert_non_overlapping(windows)
        run = run_filter(
            gyro, accel, dt, fix_idx, fix_ned, fix_sigma,
            mask_gnss(n, windows), cfg=cfg, seq=seq,
        )
        for outage in windows:
            t0 = float(t_abs_s[outage.start_idx])
            want_replay = (
                replay is not None
                and seq.name in MANDATORY_PLOT_SEQUENCES
                and length_s == REPLAY_LENGTH_S
                and seq.name not in replay
            )
            # **The whole window is built before any of it is kept.** Three paths below reach the
            # truth track and each can raise `TruthPairingError` for the same window:
            # `_strapdown_for` -> `initial_state_from_truth` -> `truth.ned_at`, `score` ->
            # `truth.displacements_ned`/`distance_m`, and `_replay_record` -> the same. Catching
            # around any one of them would leave `filter` appended and `strapdown` not, and the
            # per-method window counts in `summary.json` would stop matching while every
            # individual number stayed correct -- a summary that misreports without a wrong
            # number in it. (`_gnss_for` reads the fix arrays and never touches truth, so it is
            # not a fourth path.) `score` can also raise `ZeroDistanceOutage` when the vehicle
            # did not move at all over the window, which is a real and ordinary condition -- a
            # traffic light -- and leaves drift-% with no value to report (D-093). Both are
            # dropped the same way; nothing broader is caught, because `evaluate_outage`'s other
            # `ValueError`s are real defects.
            try:
                trajectories = {
                    "filter": window_trajectory(run.position_ned, outage),
                    "strapdown": _strapdown_for(gyro, accel, dt, outage, truth, t0),
                    "gnss_available": _gnss_for(fix_idx, fix_ned, fix_sigma, outage, t_abs_s, t0),
                }
                window_results = [
                    WindowResult(
                        method=method,
                        sequence=seq.name,
                        length_s=length_s,
                        start_idx=outage.start_idx,
                        metrics=score(traj, truth, outage, t0_s=t0),
                    )
                    for method, traj in trajectories.items()
                    if traj is not None
                ]
                record = (
                    _replay_record(
                        seq, truth, outage, t0, run, trajectories, gyro, accel, stamp=stamp
                    )
                    if want_replay
                    else None
                )
            except (TruthPairingError, ZeroDistanceOutage) as exc:
                # D-089. The error's own instruction, which until now nothing implemented: drop
                # the window rather than interpolate across the gap -- and drop it rather than
                # lose the stem's other windows, or, as before, the whole run's.
                #
                # Printed whether or not a sink was passed. A caller that forgets the sink would
                # otherwise get a quietly smaller result set, which is the one failure D-067
                # rules out by name -- "under-reporting the count is a far worse failure than a
                # small count" -- and it would look exactly like a stem that simply had fewer
                # windows.
                print(
                    f"[idr-eval] DROPPED WINDOW {seq.name} {length_s}s @{outage.start_idx}: {exc}",
                    file=sys.stderr,
                )
                if dropped is not None:
                    dropped.append(
                        DroppedWindow(
                            sequence=seq.name,
                            length_s=length_s,
                            start_idx=outage.start_idx,
                            kind=(
                                "no_truth_coverage"
                                if isinstance(exc, TruthPairingError)
                                else "zero_distance"
                            ),
                            reason=str(exc),
                        )
                    )
                continue

            out.extend(window_results)
            if record is not None:
                replay[seq.name] = record
    return out


def _cumulative(trajectory) -> np.ndarray:
    """Displacements -> positions relative to the window start, with the leading zero."""
    disp = np.asarray(trajectory.displacements_ned, dtype=float)
    return np.vstack([np.zeros((1, 2)), np.cumsum(disp, axis=0)])


def _replay_record(seq, truth, outage, t0, run, trajectories, gyro, accel, *, stamp):
    """Assemble one window's trajectory record for the renderer."""
    from eval.baselines import epoch_times

    times = epoch_times(t0, outage.length_s)
    true_disp = truth.displacements_ned(times)
    truth_ned = np.vstack([np.zeros((1, 2)), np.cumsum(true_disp, axis=0)])
    idx = np.arange(outage.start_idx, outage.end_idx + 1, EPOCH_STRIDE)
    gnss = trajectories["gnss_available"]
    return trajectory_record(
        sequence=seq.name,
        outage=outage,
        stamp=stamp,
        truth_ned=truth_ned,
        filter_ned=_cumulative(trajectories["filter"]),
        strapdown_ned=_cumulative(trajectories["strapdown"]),
        gnss_ned=None if gnss is None else _cumulative(gnss),
        position_sigma_m=np.sqrt(run.position_var[idx]),
        filter_yaw_rad=run.yaw_rad[idx],
        truth_yaw_rad=np.concatenate(
            [[course_over_ground(true_disp)[0]], course_over_ground(true_disp)]
        ),
        accel=accel[outage.start_idx : outage.end_idx],
        gyro=gyro[outage.start_idx : outage.end_idx],
        distance_m=truth.distance_m(times[0], times[-1]),
    )


def _strapdown_for(gyro, accel, dt, outage: Outage, truth, t0_s: float):
    """The naive strapdown baseline over one window, initialised from truth (D-064)."""
    rot0, v0 = initial_state_from_truth(truth, t0_s)
    sl = slice(outage.start_idx, outage.end_idx)
    step = float(np.median(dt[sl]))
    return naive_strapdown(
        gyro[sl], accel[sl], step,
        initial_rotation=rot0, initial_velocity_ned=v0, epoch_stride=EPOCH_STRIDE,
    )


def _gnss_for(fix_idx, fix_ned, fix_sigma, outage: Outage, t_abs_s: np.ndarray, t0_s: float):
    """The GNSS-available baseline over one window, or None if no fix precedes it.

    None rather than an exception: a window that opens before the receiver's first fix is a real
    and ordinary condition near the start of a recording, and the correct answer is that this
    baseline has nothing to report for it -- not a fabricated position, and not a dropped window
    for the other two methods.
    """
    from eval.baselines import epoch_times

    t_fix = t_abs_s[fix_idx]
    times = epoch_times(t0_s, outage.length_s)
    usable = t_fix <= times[-1]
    if not usable.any() or t_fix[usable][0] > times[0]:
        return None
    return gnss_available(t_fix[usable], fix_ned[usable][:, :2], times)


#: Outage length, in seconds, of the window written out for the replay renderer. 60 s is the
#: reference case the whole error budget is sized against (docs/ERROR_BUDGET.md section 1).
REPLAY_LENGTH_S = 60

#: Schema version of a trajectory record. The renderer refuses a record it does not recognise
#: rather than drawing an older layout's fields in the wrong places.
TRAJECTORY_SCHEMA = "idr-trajectory/1"


def trajectory_record(
    *,
    sequence: str,
    outage: Outage,
    stamp: Stamp,
    truth_ned: np.ndarray,
    filter_ned: np.ndarray,
    strapdown_ned: np.ndarray,
    gnss_ned: np.ndarray | None,
    position_sigma_m: np.ndarray,
    filter_yaw_rad: np.ndarray,
    truth_yaw_rad: np.ndarray,
    accel: np.ndarray,
    gyro: np.ndarray,
    distance_m: float,
) -> dict:
    """One outage window, in the form the replay renderer reads. **Every field is measured here.**

    The renderer contains no physics and no simulation, so anything it can display has to be
    produced by this function -- which is why the per-epoch drift-% and yaw error are computed on
    this side rather than left for the page to work out. A renderer that computes a displayed
    number is a renderer that can display a number the evaluation never produced.

    Positions are cumulative NED metres relative to the outage's first truth position, one per 1 s
    epoch boundary. `position_sigma_m` is the filter's own `sqrt(diag(P))` on north and east at the
    same boundaries -- the ellipse that grows through the outage and collapses at re-acquisition.
    The sensor traces are the raw `S-` stream at 10 Hz, so there are `10 x length_s` of them
    against `length_s + 1` positions; the renderer captions the rate and must not imply 200 Hz.
    """
    truth_ned = np.asarray(truth_ned, dtype=float)
    n = truth_ned.shape[0]
    drift = [
        float(100.0 * np.linalg.norm(filter_ned[k] - truth_ned[k]) / distance_m)
        if distance_m > 0 else 0.0
        for k in range(n)
    ]
    yaw_err_deg = [
        float(np.degrees(wrap_to_pi(filter_yaw_rad[k] - truth_yaw_rad[k]))) for k in range(n)
    ]
    return {
        "schema": TRAJECTORY_SCHEMA,
        "stamp": stamp.caption(),
        "reproducible": stamp.is_reproducible(),
        "sequence": sequence,
        "stream": "S-",
        "imu_rate_hz": SAMPLE_RATE_HZ,
        "length_s": outage.length_s,
        "start_idx": outage.start_idx,
        "distance_m": float(distance_m),
        "epoch_s": list(range(n)),
        "truth_ned": truth_ned.tolist(),
        "filter_ned": np.asarray(filter_ned, dtype=float).tolist(),
        "strapdown_ned": np.asarray(strapdown_ned, dtype=float).tolist(),
        "gnss_ned": None if gnss_ned is None else np.asarray(gnss_ned, dtype=float).tolist(),
        "position_sigma_m": np.asarray(position_sigma_m, dtype=float).tolist(),
        "drift_pct": drift,
        "yaw_error_deg": yaw_err_deg,
        "accel_mps2": np.asarray(accel, dtype=float).tolist(),
        "gyro_rps": np.asarray(gyro, dtype=float).tolist(),
    }


# --------------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------------


def summarise_by_method_and_length(results: list[WindowResult]) -> dict[str, dict[str, dict]]:
    """`{method: {length_s: summary}}`, each summary from `eval.metrics.core.summarise`."""
    grouped: dict[str, dict[int, list[OutageMetrics]]] = {}
    for r in results:
        grouped.setdefault(r.method, {}).setdefault(r.length_s, []).append(r.metrics)
    return {
        method: {str(length): summarise(ms) for length, ms in sorted(by_length.items())}
        for method, by_length in grouped.items()
    }


def gate1_ratio(by_method: dict[str, dict[str, dict]]) -> dict[str, object]:
    """The Gate 1 number: physics-only median drift over GNSS-available median drift, at 60 s.

    Reported, never judged. The gate is 3-5x and a human closes it against
    `docs/IMPLEMENTATION_PLAN.md` §7 -- this function's job is to make the number impossible to
    misquote by carrying the sequence count it rests on alongside it.
    """
    key = str(GATE1_LENGTH_S)
    have = [m for m in ("filter", "gnss_available") if key in by_method.get(m, {})]
    if len(have) < 2:
        return {"measured": False, "why": f"no {GATE1_LENGTH_S} s windows for {METHODS[0]} and/or "
                f"{METHODS[2]}"}
    num = by_method["filter"][key]
    den = by_method["gnss_available"][key]
    ratio = num["drift_pct_median"] / den["drift_pct_median"] if den["drift_pct_median"] else None
    return {
        "measured": True,
        "length_s": GATE1_LENGTH_S,
        "filter_drift_pct_median": num["drift_pct_median"],
        "gnss_available_drift_pct_median": den["drift_pct_median"],
        "ratio": ratio,
        "range_required": list(GATE1_RATIO_RANGE),
        "in_range": (
            None if ratio is None else GATE1_RATIO_RANGE[0] <= ratio <= GATE1_RATIO_RANGE[1]
        ),
        "n_windows_filter": num["n_sequences"],
        "n_windows_gnss_available": den["n_sequences"],
    }


def write_artefacts(
    out: Path,
    stamp: Stamp,
    results: list[WindowResult],
    replay: dict[str, dict] | None = None,
    dropped: list[DroppedWindow] | None = None,
) -> dict:
    """Write `summary.json`, `windows.csv` and one `trajectory_<seq>.json` per plotted
    sequence, all carrying the stamp.

    The stamp goes **inside** the artefact, never into a filename: a filename is renamed, copied
    and pasted into a slide, and the provenance is lost at the first of those (H-5).
    """
    out.mkdir(parents=True, exist_ok=True)
    by_method = summarise_by_method_and_length(results)
    # D-089. Carried beside the results, never folded into them: a run that graded 1260 windows
    # and dropped 3 is a different result from one that graded 1263, and the difference is
    # invisible in every metric. D-067's rule is that the omission travels with the number.
    dropped = list(dropped or [])
    summary = {
        "stamp": stamp.caption(),
        "reproducible": stamp.is_reproducible(),
        "crse_convention": CRSE_CONVENTION.value,
        "n_windows": len(results),
        "n_dropped_windows": len(dropped),
        "n_dropped_by_kind": {
            kind: sum(d.kind == kind for d in dropped)
            for kind in sorted({d.kind for d in dropped})
        },
        "by_method": by_method,
        "gate1": gate1_ratio(by_method),
        "trajectories": sorted(replay or {}),
        "dropped_windows": [d.as_row() for d in dropped],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    for name, record in sorted((replay or {}).items()):
        (out / f"trajectory_{name}.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )

    rows = [r.as_row() for r in results]
    with (out / "windows.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([f"# {stamp.caption()}"])
        if rows:
            writer.writerow(list(rows[0]))
            for row in rows:
                writer.writerow([row[k] for k in rows[0]])
    return summary


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="idr-eval", description="IDR 26168 evaluation harness")
    p.add_argument("--data", type=Path, default=Path("data/IO-VNBD"), help="dataset root")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", type=Path, default=Path("eval/figures"))
    p.add_argument(
        "--lengths",
        type=int,
        nargs="+",
        default=list(OUTAGE_LENGTHS_S),
        help="outage lengths in seconds (changing these needs a DECISION_LOG entry)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the protocol and plan the sweep without loading data",
    )
    return p


def plan_sweep(sequence_lengths: dict[str, int], lengths: list[int]) -> dict[int, list]:
    """Generate and validate the outage sweep. Validation is not optional."""
    sweep = generate_sweep(sequence_lengths, tuple(lengths))
    for windows in sweep.values():
        assert_non_overlapping(windows)
    return sweep


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp = seed_everything(args.seed)

    # Protocol invariants, checked before any data is touched. A run that violates the split is
    # worse than a run that does not happen.
    assert_split_disjoint()
    assert_split_is_loadable()

    print(f"[idr-eval] {stamp.caption()}")
    print(f"[idr-eval] CRSE convention: {CRSE_CONVENTION.value}")
    if not stamp.is_reproducible():
        print(
            "[idr-eval] WARNING: working tree is dirty or not a git repo. Artefacts from this run "
            "cannot be regenerated from a commit and must not reach the submission.",
            file=sys.stderr,
        )

    if args.dry_run:
        # Nominal lengths so the sweep can be planned before the dataset lands.
        nominal = {name: 20 * 60 * 10 for name in test_sequences()}
        sweep = plan_sweep(nominal, args.lengths)
        print(f"[idr-eval] dry run over {len(nominal)} held-out sequences:")
        for length_s, windows in sorted(sweep.items()):
            print(f"    {length_s:>4} s -> {len(windows):>5} non-overlapping windows")
        print(f"[idr-eval] long-outage plot set: {', '.join(LONG_OUTAGE)}")
        return 0

    if not args.data.exists():
        print(
            f"[idr-eval] dataset not found at {args.data}\n"
            "           See docs/DATASETS.md, then record the download in data/manifest/.\n"
            "           Use --dry-run to validate the protocol without data.",
            file=sys.stderr,
        )
        return 2

    sequences = load_split(args.data, test_sequences())
    results: list[WindowResult] = []
    replay: dict[str, dict] = {}
    skipped: list[str] = []
    skipped_names: list[str] = []
    dropped: list[DroppedWindow] = []
    for name, seq in sorted(sequences.items()):
        try:
            truth = load_truth(paired_truth_path(name, args.data), name)
            results.extend(
                evaluate_sequence(
                    seq, truth, args.lengths, replay=replay, stamp=stamp, dropped=dropped
                )
            )
        except SequenceUnusable as exc:
            skipped.append(f"{name}: {exc}")
            skipped_names.append(name)
            print(f"[idr-eval] SKIPPED {exc}", file=sys.stderr)
        else:
            print(f"[idr-eval] {name}: {sum(r.sequence == name for r in results)} window results")

    if not results:
        print(
            "[idr-eval] no results: every held-out sequence was skipped. See the messages above; "
            "reporting nothing is correct here, reporting a number from a partial set is not.",
            file=sys.stderr,
        )
        return 3

    summary = write_artefacts(args.out, stamp, results, replay, dropped)

    # A mandatory figure that is simply absent (D-089). Before dropped windows existed, a hole
    # inside a `MANDATORY_PLOT_SEQUENCES` replay window aborted the run, so this could not happen
    # quietly; now it can, and `eval/splits.py` says such a figure should "fail the run rather
    # than being noticed the night before" while nothing in the code has ever enforced it. A stem
    # that was skipped whole is already reported as skipped and is not counted twice here.
    mandatory_missing = [
        name
        for name in MANDATORY_PLOT_SEQUENCES
        if name not in replay and name not in skipped_names
    ]

    if skipped:
        summary["skipped"] = skipped
    if mandatory_missing:
        summary["mandatory_plots_missing"] = mandatory_missing
    if skipped or mandatory_missing:
        (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if skipped:
        print(
            f"[idr-eval] {len(skipped)} sequence(s) skipped -- listed in summary.json. Report the "
            "count with every number from this run.",
            file=sys.stderr,
        )
    if dropped:
        print(
            f"[idr-eval] {len(dropped)} window(s) dropped for want of truth coverage -- listed in "
            "summary.json. Report the count with every number from this run (D-089).",
            file=sys.stderr,
        )
    if mandatory_missing:
        print(
            f"[idr-eval] MANDATORY PLOT MISSING: {', '.join(mandatory_missing)} produced no "
            f"{REPLAY_LENGTH_S} s replay window. eval/splits.MANDATORY_PLOT_SEQUENCES names these "
            "so a missing figure is found now rather than the night before; the submission is "
            "not complete without them.",
            file=sys.stderr,
        )
    print(json.dumps(summary["gate1"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
