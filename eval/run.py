"""Harness entry point. One command regenerates every number.

    idr-eval --data data/IO-VNBD --seed 0 --out eval/figures

If regenerating the results needs manual steps, the figures will silently drift from the numbers
in the text. That is the failure this file exists to prevent.

Three trajectories are produced per outage window and scored through the same metrics path:

    filter           the physics-only InEKF -- IMU propagation, NHC, ZUPT, ZARU, gated GNSS
    strapdown        the naive strapdown baseline (eval/baselines.py)
    gnss_available   the zero-order-hold GNSS baseline, the Gate 1 denominator

**Every window is entered aided.** The filter makes one GNSS-aided pass over the sequence, its
state is snapshotted at the first sample of every window, and each window is dead-reckoned from
its own snapshot with the GNSS update never called. That is exactly one filter pass per window
with GNSS open everywhere except inside that window -- the outage the protocol describes, with a
re-acquisition on the far side of it (docs/EVALUATION.md section 3 and section 6) -- at the cost
of two passes rather than one per window. Until D-115 the harness masked *every* window of a
length in a single pass, which left GNSS closed from the end of warmup to the end of the
recording: the filter entered its second window having been unaided for the whole of the first,
its tenth having been unaided for nine, while the strapdown baseline was re-initialised from
truth at each. The 19.4x Gate 1 ratio in D-110 was measured under that mask.

**Gate 1 is the ratio of the first to the third, on median drift-%, at 60 s. The gate is 3-5x.**
It is reported here as a measured number and it is not this file's job to decide whether it passed.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from core.reference.inekf import (
    UNALIGNED_YAW_SIGMA_RAD,
    FilterConfig,
    InEKF,
    MountInit,
    NavState,
    initial_covariance,
    is_stationary,
    mount_yaw_from_dynamics,
    nhc_is_valid,
    pca_mount_yaw,
    right_invariant_from_plain,
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
)
from eval.splits import (
    LONG_OUTAGE,
    MANDATORY_PLOT_SEQUENCES,
    QUIET_MOUNT,
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

#: A speed no road vehicle in this dataset reaches (540 km/h), used only to catch a filter state
#: that has left physical reality before it reaches literal infinity a few hundred steps later.
#: Not a tuning knob: it exists to make `FilterDivergedError` fire early enough to name the sample
#: it happened at, not to decide what counts as "diverged" -- D-094 already measured that the
#: state can run away by two orders of magnitude in under ten fixes.
DIVERGENCE_SPEED_MPS = 150.0


class SequenceUnusable(RuntimeError):
    """This stem cannot be graded, and the run says so rather than reporting a number anyway."""


class FilterDivergedError(RuntimeError):
    """The filter's own state left the bounds a moving car can produce.

    Caught in `evaluate_sequence` and turned into `SequenceUnusable` -- a diverged state
    corrupts every window drawn from the rest of the run, not just the sample it is caught at,
    because `run_filter` integrates one continuous pass per length and every window slices a
    displacement out of it (D-089's atomicity argument applies here too). Raised before the state
    reaches literal infinity: unchecked, `van_loan`'s `expm_series` converts an infinite matrix
    norm to an int and raises an unnamed `OverflowError` several steps later, which is a crash a
    read of the traceback does not explain and a window drop cannot recover from.
    """


# --------------------------------------------------------------------------------------------
# Reading a loaded Sequence into the arrays the filter and the baselines consume
# --------------------------------------------------------------------------------------------


def imu_stream(seq: Sequence) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`(gyro, accel, t_rel_s)` for one sequence: `(n, 3)`, `(n, 3)`, `(n,)`.

    Axis mapping is the proper right-handed triad established by D-101 (superseding D-047 and
    D-095): `device_x = +gyro_yaw`, `device_y = -gyro_roll`, `device_z = +gyro_pitch`.
    `gyro_pitch` is the vertical body rate across 100% of synchronised IO-VNBD stems (R² > 0.99
    and unit slope against heading rate over turns), preventing the ~1.3 g gravity tilt into
    horizontal axes that previously corrupted dead-reckoning propagation.

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

    raw_yaw = imu["gyro_yaw"].to_numpy(dtype=float)
    raw_pitch = imu["gyro_pitch"].to_numpy(dtype=float)
    raw_roll = imu["gyro_roll"].to_numpy(dtype=float)
    # D-101 proper right-handed triad: (+gyro_yaw, -gyro_roll, +gyro_pitch)
    gyro = np.column_stack([raw_yaw, -raw_roll, raw_pitch])
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
    Where it is absent the config default stands. It is a *horizontal* accuracy; the vertical is
    `GNSS_VERTICAL_SIGMA_RATIO` times it (see there), and `fix_covariance` builds the 3x3.
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


#: GNSS altitude is worse than the horizontal fix by about this factor on a phone receiver, and
#: `gps_accuracy_m` is the horizontal figure. It matters here for a reason specific to the
#: right-invariant filter: `H_gnss = [-p^, 0, I]` couples the *down* innovation to roll and pitch
#: through the lever arm, so an altitude trusted to 3 m tells the filter its tilt to 0.3 deg
#: after one fix -- measured on S3a -- when the levelling it started from was good to 2 deg. A
#: tilt the filter believes it knows is a tilt it will not correct, and 2 deg is 0.3 m/s^2 of
#: gravity in the horizontal (D-115). 3 is the ratio the receiver literature gives for VDOP over
#: HDOP in the open; it is stated, not measured on this dataset, which carries no vertical truth.
GNSS_VERTICAL_SIGMA_RATIO = 3.0


def fix_covariance(sigma_m: float) -> np.ndarray:
    """3x3 fix covariance from the receiver's horizontal accuracy."""
    s2 = float(sigma_m) ** 2
    return np.diag([s2, s2, (GNSS_VERTICAL_SIGMA_RATIO**2) * s2])


def fix_course_arrays(seq: Sequence) -> tuple[np.ndarray, np.ndarray] | None:
    """`(course_rad, speed_mps)` per distinct fix, or None when the stream carries neither.

    `gps_orientation_deg` is the receiver's Doppler course over ground, degrees clockwise from
    north, and `gps_speed_mps` its speed (D-102). They are the heading the phone actually has:
    a fix-to-fix chord at the measured 9 s cadence turns through whatever the road did in those
    nine seconds, and against the paired `V-` course its p90 error is 18-38 deg on the 9 s stems
    where the receiver's own course is under 2 deg (D-115). Entries the file leaves non-finite
    stay NaN, and the caller must check both the value and the speed threshold before reading a
    course, because a stationary receiver reports its last one.
    """
    gnss = seq.gnss
    if "gps_orientation_deg" not in gnss.columns or "gps_speed_mps" not in gnss.columns:
        return None
    course = np.deg2rad(gnss["gps_orientation_deg"].to_numpy(dtype=float))
    speed = gnss["gps_speed_mps"].to_numpy(dtype=float)
    return wrap_to_pi(course), speed


def course_sigma_rad(cfg: FilterConfig, speed_mps: float) -> float:
    """1-sigma heading accuracy of the receiver's course at this speed.

    A Doppler course is a velocity direction, so its angular error is a cross-track velocity
    error over the speed: `atan(sigma_ct / v)`. `FilterConfig.course_cross_track_sigma_mps`
    records where the 0.5 m/s came from and what it reproduces.
    """
    return float(np.arctan2(cfg.course_cross_track_sigma_mps, max(float(speed_mps), 1e-6)))


def velocity_measurement(
    cfg: FilterConfig, course_rad: float, speed_mps: float
) -> tuple[np.ndarray, np.ndarray]:
    """The receiver's Doppler course and speed as a horizontal NED velocity with its 2x2
    covariance: `gnss_speed_sigma_mps` along the course, `course_cross_track_sigma_mps` across
    it, rotated into north/east. Both sigmas are measured against the paired `V-` track
    (`FilterConfig`, D-115).

    Why a velocity update at all, when the protocol's aiding is the position fix: ten of the
    twelve held-out stems carry GNSS at 9 s, and over 9 s a phone's tilt error, its accelerometer
    offset and its heading error all reach the position through the same double integral. The
    filter cannot tell them apart from position alone, and with a 0.2 deg/s turn-on prior the
    gyro bias is the explanation it prefers -- on S3a a single 13 m innovation moved `b_g` by
    0.25 deg/s, the wrong bias tilted the attitude a further 2 deg by the next fix, and the run
    left physical bounds at 59 s *with every fix available*. One Doppler velocity per fix pins
    speed and heading directly; the same run then holds to 0.8-11 m for six minutes.
    """
    c, s = np.cos(course_rad), np.sin(course_rad)
    rot = np.array([[c, -s], [s, c]])  # (along, cross) -> (north, east)
    cov = rot @ np.diag([cfg.gnss_speed_sigma_mps**2, cfg.course_cross_track_sigma_mps**2]) @ rot.T
    return np.array([speed_mps * c, speed_mps * s]), cov


#: `in_motion_config` reads the white level of each stream as its residual from a centred
#: moving average this many samples wide -- 0.5 s at 10 Hz, above which the vehicle's own
#: rigid-body motion lives and below which what is left is vibration, aliased or not, that the
#: integration cannot tell from noise.
NOISE_SMOOTH_SAMPLES = 5


def stream_white_level(x: np.ndarray, smooth: int = NOISE_SMOOTH_SAMPLES) -> np.ndarray:
    """Per-axis per-sample white noise sigma of an (n, 3) stream: the standard deviation of its
    residual from a `smooth`-sample centred moving average, corrected for the `1 - 1/smooth` of
    a white process's variance that the average removes. NaN rows are dropped."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x).all(axis=1)]
    if x.shape[0] < smooth + 2:
        return np.zeros(3)
    kernel = np.ones(smooth)
    count = np.convolve(np.ones(x.shape[0]), kernel, mode="same")
    residual = x - np.column_stack(
        [np.convolve(x[:, i], kernel, mode="same") / count for i in range(3)]
    )
    return np.sqrt(np.var(residual, axis=0) / (1.0 - 1.0 / smooth))


def in_motion_config(
    cfg: FilterConfig, gyro: np.ndarray, accel: np.ndarray, dt: np.ndarray, *, upto: int
) -> FilterConfig:
    """`cfg` with `gyro_arw` and `accel_vrw` raised to the white level the stream actually
    carries over its first `upto` samples, never lowered below the Allan-run defaults.

    The Allan-run process noise is a stationary phone's floor: 0.75 deg/sqrt(hr), 0.040 deg/s
    per 10 Hz sample (D-120; D-045 read 1.41 with the stop's settle still in the segment).
    Measured in motion against the paired `V-` truth (D-115), the same phone's tilt random-walks
    at about 0.5 deg/sqrt(s) on S3a -- 3.7 deg over 60 s, 40x the Allan figure in sigma (20x
    D-045's) -- and its 10 Hz gyro carries a per-sample white level of 1.7-1.9 deg/s.
    On the Vta/Vw stems the level is 4-20 deg/s and the heading random-walks 20-45 deg per
    60 s. A `Q` twenty to two hundred times too small in variance is why the filter believed its
    tilt to 0.3 deg after a minute of driving and could not re-level from either the
    accelerometer or the fixes (D-110's "process noise under-predicts by about 100x").

    Read from the warmup, causally, on the stream itself -- the same window the mount and the
    levelling come from -- so that a recording whose phone rattles is filtered as one, and one
    that sits still is not made to carry its noise. The worst axis is taken, as the Allan run
    did. It is an overestimate of the *random walk* where part of the high-frequency energy is
    bounded rattling rather than white noise -- by about 1.4x on S3a and 2x on Vta1a against the
    end-to-end heading drift -- which is the conservative direction, and the one D-045 chose.
    """
    upto = max(0, min(int(upto), gyro.shape[0]))
    if upto < NOISE_SMOOTH_SAMPLES + 2:
        return cfg
    step = float(np.median(dt[: max(1, upto - 1)]))
    if not np.isfinite(step) or step <= 0:
        return cfg
    sigma_g = float(np.max(stream_white_level(gyro[:upto])))
    sigma_a = float(np.max(stream_white_level(accel[:upto])))
    return replace(
        cfg,
        gyro_arw=max(cfg.gyro_arw, sigma_g * np.sqrt(step)),
        accel_vrw=max(cfg.accel_vrw, sigma_a * np.sqrt(step)),
    )


def vehicle_yaw(state: NavState) -> float:
    """Heading of the *vehicle's* forward axis in NED, which is what a GNSS course measures.

    `state.R` is phone->NED and `state.R_sv` phone->vehicle, so vehicle->NED is `R @ R_sv.T`
    and its yaw is the course. `state.yaw` is the phone's, which differs by the mount angle.
    """
    r_vn = state.R @ state.R_sv.T
    return float(np.arctan2(r_vn[1, 0], r_vn[0, 0]))


# --------------------------------------------------------------------------------------------
# The filter run -- one pass per sequence per outage length
# --------------------------------------------------------------------------------------------


@dataclass
class Snapshot:
    """The aided filter at the top of a sample, with whether it had aligned by then."""

    filter: InEKF
    aligned: bool


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
    #: The Doppler velocity update (`InEKF.update_gnss_velocity`), offered at every open fix
    #: that carries a course and is moving; zero on streams without a course column.
    n_gnss_velocity_applied: int = 0
    n_gnss_velocity_rejected: int = 0
    #: Position fixes applied with the gate overridden after `GNSS_REJECTIONS_BEFORE_REANCHOR`
    #: consecutive rejections. Counted within `n_gnss_applied` as well; this says how many of
    #: those were re-anchors rather than ordinary accepted fixes.
    n_gnss_reanchored: int = 0
    #: The process noise the pass actually ran with -- `in_motion_config` measured on the
    #: warmup -- so a number can be read next to the stem it came from.
    gyro_arw_used: float = float("nan")
    accel_vrw_used: float = float("nan")

    def aided_pass_summary(self) -> dict[str, object]:
        """What the aided pass did, for `summary.json`: how it aligned, what it was fed, and
        how many of each update it applied -- the numbers every D-115 claim rests on."""
        init = self.init
        return {
            "aligned_at_sample": self.aligned_at_sample,
            "heading_source": None if init is None else init.heading_source,
            "mount_source": None if init is None else init.mount_source,
            "mount_yaw_deg": None if init is None else float(np.degrees(init.mount_yaw_rad)),
            "mount_spread_deg": None if init is None else float(np.degrees(init.mount_spread_rad)),
            "gyro_arw_used": self.gyro_arw_used,
            "accel_vrw_used": self.accel_vrw_used,
            "n_gnss_applied": self.n_gnss_applied,
            "n_gnss_rejected": self.n_gnss_rejected,
            "n_gnss_reanchored": self.n_gnss_reanchored,
            "n_gnss_velocity_applied": self.n_gnss_velocity_applied,
            "n_gnss_velocity_rejected": self.n_gnss_velocity_rejected,
            "n_zupt": self.n_zupt,
            "n_zaru_applied": self.n_zaru_applied,
            "n_zaru_rejected": self.n_zaru_rejected,
            "n_nhc": self.n_nhc,
        }
    #: The filter, copied whole, at the top of each sample index in `snapshot_at` -- the aided
    #: state a window starting there is dead-reckoned from (`replay_window`).
    snapshots: dict[int, Snapshot] = field(default_factory=dict)
    #: Sample at which `align_heading` ran, or None if the heading was aligned from the outset
    #: (or never could be: no course column, or the vehicle never moved with GNSS open).
    aligned_at_sample: int | None = None


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
    snapshot_at: set[int] | None = None,
) -> FilterRun:
    """Drive the InEKF across one whole sequence, applying GNSS only where `gnss_open` is True.

    **There is no outage branch here, and that absence is the architectural claim.** During an
    injected outage the GNSS updates are simply not called; nothing switches mode, nothing
    re-initialises, and re-acquisition is an ordinary gated update. A rejected fix (multipath on
    tunnel exit) takes the same path as a masked one -- see D-001 and `InEKF.update_gnss`. The
    one exception is deliberate and counted: a fix rejected `GNSS_REJECTIONS_BEFORE_REANCHOR`
    times running is applied, because that many rejections is evidence against the covariance
    and not against the fixes (D-115).

    Two GNSS updates per open fix: the position, gated, and the receiver's Doppler velocity,
    ungated -- `velocity_measurement` and `FilterConfig.gate_gnss_velocity` say why each.

    Gating is the caller's job, per the filter's own contract: `is_stationary` and `nhc_is_valid`
    read the IMU stream (passing `gyro_bias=state.b_g` to `is_stationary`), which is not an
    intrinsic property of the state. ZUPT and ZARU are **offered together** at every detected
    stop (D-004); ZARU may decline at its own χ² gate (D-057), which is counted separately so a
    run can be read for how often that happens.
    """
    cfg = cfg or FilterConfig()
    n = gyro.shape[0]
    if seq is not None:
        cfg = in_motion_config(cfg, gyro, accel, dt, upto=min(n, WARMUP_S * SAMPLE_RATE_HZ))
    f = InEKF(cfg)

    # **Before the first propagate, not after it.** See `initialise_filter`: starting from
    # R = R_sv = I integrates gravity into the horizontal axes and the run diverges (D-094).
    init = None if seq is None else initialise_filter(
        f, seq, accel, fix_idx, fix_ned, gyro=gyro
    )
    aligned = init is None or init.heading_aligned
    aligned_at: int | None = None
    course = None if seq is None else fix_course_arrays(seq)

    fix_at = {int(i): k for k, i in enumerate(fix_idx)}
    window = max(1, int(round(cfg.zupt_window_s * SAMPLE_RATE_HZ)))
    snapshot_at = set() if snapshot_at is None else set(int(i) for i in snapshot_at)
    snapshots: dict[int, InEKF] = {}

    pos = np.zeros((n, 2))
    yaw = np.zeros(n)
    pvar = np.zeros((n, 2))
    counts = dict(
        gnss_ok=0, gnss_no=0, zupt=0, zaru_ok=0, zaru_no=0, nhc=0, vel_ok=0, vel_no=0, reanchor=0
    )
    rejected_run = 0

    for k in range(n):
        if k in snapshot_at:
            # The state a window opening at `k` starts from: everything up to and including
            # sample k-1 applied, sample k not yet propagated. `replay_window` takes it from here.
            snapshots[k] = Snapshot(filter=copy.deepcopy(f), aligned=aligned)

        # **Before alignment the filter is not running.** It has no heading and no mount, so
        # there is nothing to integrate the accelerometer through; it holds the last open fix
        # and waits (D-115). Propagating anyway integrated gravity through an unknown yaw and
        # took S3a to 3.5 km from its fix before the alignment window had filled.
        if aligned and k > 0:
            f.propagate(gyro[k], accel[k], float(dt[k - 1]))
            _check_physical(f, k, seq.name if seq is not None else "<unnamed>", "this pass")
        if aligned:
            _step_constraints(f, k, gyro, accel, cfg, window, counts)

        j = fix_at.get(k)
        if j is not None and gnss_open[k]:
            if aligned:
                cov = fix_covariance(fix_sigma[j])
                force = rejected_run + 1 >= GNSS_REJECTIONS_BEFORE_REANCHOR
                if f.update_gnss(fix_ned[j], cov, gate=not force):
                    counts["gnss_ok"] += 1
                    counts["reanchor"] += int(force)
                    rejected_run = 0
                else:
                    counts["gnss_no"] += 1
                    rejected_run += 1
                # The receiver's own velocity, at the same epoch and the same availability as
                # its position -- see `velocity_measurement` for why the position alone was
                # not enough to keep the filter on the road at a 9 s cadence.
                if course is not None:
                    c, v = float(course[0][j]), float(course[1][j])
                    if np.isfinite(c) and np.isfinite(v) and v >= cfg.course_min_speed_mps:
                        v_ne, r_ne = velocity_measurement(cfg, c, v)
                        if f.update_gnss_velocity(v_ne, r_ne):
                            counts["vel_ok"] += 1
                        else:
                            counts["vel_no"] += 1
            else:
                f.state.p = np.asarray(fix_ned[j], dtype=float).copy()
                if course is not None:
                    c, v = float(course[0][j]), float(course[1][j])
                    if np.isfinite(c) and np.isfinite(v) and v >= cfg.course_min_speed_mps:
                        if attempt_alignment(f, seq, gyro, accel, fix_idx, k, c, v):
                            aligned, aligned_at = True, k

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
        snapshots=snapshots,
        aligned_at_sample=aligned_at,
        n_gnss_velocity_applied=counts["vel_ok"],
        n_gnss_velocity_rejected=counts["vel_no"],
        n_gnss_reanchored=counts["reanchor"],
        gyro_arw_used=cfg.gyro_arw,
        accel_vrw_used=cfg.accel_vrw,
    )


def _check_physical(f: InEKF, k: int, name: str, where: str) -> None:
    speed = float(np.linalg.norm(f.state.v))
    if not np.isfinite(speed) or not np.isfinite(f.state.p).all() or speed > DIVERGENCE_SPEED_MPS:
        raise FilterDivergedError(
            f"{name}: filter state left physical bounds at sample {k} "
            f"({k / SAMPLE_RATE_HZ:.1f} s into {where}) -- |v| = {speed:.3g} m/s "
            f"(limit {DIVERGENCE_SPEED_MPS:g}), p = {f.state.p}. Nothing downstream of this "
            "sample is a navigation solution."
        )


#: A position fix rejected at the chi-squared gate is applied anyway when it is the N-th
#: consecutive rejection. The gate exists for the single multipath fix on tunnel exit; under
#: the filter's own model a rejection is a 1% event and three in a row are a 1e-6 one, so a
#: run of them is evidence that the *model* is wrong -- a tilt excursion the covariance did not
#: carry, a receiver whose reported accuracy is a third of its error (S3c: 21% of fixes beyond
#: 3 sigma of `gps_accuracy_m`) -- and not that three fixes were. Without this the position
#: block never re-admits a fix once it has drifted past the gate, because the velocity updates
#: keep the velocity right and `P_pp` grows at (0.5 m/s x 9 s)^2 per fix: S3a spent 100 of
#: 254 fixes locked out at 200-800 m with a 3 m fix in hand (D-115). Counted and reported as
#: `n_gnss_reanchored`; a stem that needs many of them is a stem whose aided pass is not
#: tracking, and the number says so.
GNSS_REJECTIONS_BEFORE_REANCHOR = 3

#: See `_step_constraints`: a detected stop is refused when the filter's own speed exceeds both
#: of these -- an absolute floor, and this many sigma of its velocity block.
ZUPT_VETO_MIN_SPEED_MPS = 1.0
ZUPT_VETO_NSIGMA = 3.0

#: Whether `replay_window` freezes the bias states for the outage (`InEKF.hold_biases`: bias
#: process noise zeroed before Van Loan, bias gain rows zeroed for every update but ZARU).
#: ERROR_BUDGET section 3.2 calls for the snapshot; the A/B did not support it (D-130). From
#: the same S3a + S3c aided snapshots, every 60 s window, hold on vs off, median / p90 drift-%:
#: S3a 42.5 / 97.2 vs 42.0 / 95.2 (40 windows); S3c 72.1 / 121.7 vs 69.5 / 121.5 (61); pooled
#: 56.9 / 119.7 vs 57.2 / 119.5. A wash inside the noise, with off ahead on both per-stem
#: medians and every p90 -- a mechanism that does not measurably help does not ship on.
#: The value travels in `summary.json` as `biases_held_in_outage` so an artefact says which
#: variant produced it; flip it here, never per call.
HOLD_BIASES_IN_OUTAGE = False


def _step_constraints(
    f: InEKF, k: int, gyro: np.ndarray, accel: np.ndarray, cfg: FilterConfig, window: int,
    counts: dict[str, int],
) -> None:
    """ZUPT+ZARU at a detected stop, else NHC where it is valid -- the same step for the aided
    pass and for every window replayed from it, so the two cannot drift apart.

    `nhc_is_valid` wants the *vehicle's* yaw rate and lateral acceleration. The raw sample is in
    the phone frame, and a phone yawed 90 deg in its cradle has the vehicle's forward
    acceleration on its own y axis -- so the gate used to read braking as cornering and
    cornering as nothing on every stem whose mount is not near zero (D-115). `R_sv` takes both
    into the vehicle frame first.
    """
    lo = max(0, k - window + 1)
    st = f.state
    if k + 1 >= window and is_stationary(
        accel[lo : k + 1], gyro[lo : k + 1], cfg, gyro_bias=st.b_g
    ):
        # **A steady cruise looks stationary to an IMU.** `is_stationary` reads accelerometer
        # variance and gyro magnitude, and a quiet phone at a constant 3.5 m/s on a smooth road
        # is under both thresholds -- S3a, 2 s in, on the first run this harness made with a
        # working alignment. A ZUPT there is not a small error: it sets the velocity to zero at
        # sigma 0.02 m/s and the filter rebuilds its speed from the accelerometer alone, 3 m/s
        # behind, until nothing passes the gate. The filter's own state is the one thing that
        # can refute the detector: a stop is vetoed when the estimated speed is more than
        # `ZUPT_VETO_MIN_SPEED_MPS` *and* more than three sigma from zero. Early, when the
        # velocity is worth 0.5 m/s, that vetoes anything over 1.5 m/s; deep into an outage,
        # when the velocity block has grown, it vetoes only what the filter is sure of, so a real
        # stop the dead-reckoned speed has drifted 2 m/s from still gets its ZUPT (D-115).
        speed = float(np.linalg.norm(st.v))
        sigma_v = float(np.sqrt(np.max(np.linalg.eigvalsh(f.P[3:6, 3:6]))))
        if speed > ZUPT_VETO_MIN_SPEED_MPS and speed > ZUPT_VETO_NSIGMA * sigma_v:
            counts["zupt_vetoed"] = counts.get("zupt_vetoed", 0) + 1
            return
        f.update_zupt()
        counts["zupt"] += 1
        if f.update_zaru(gyro[k]):
            counts["zaru_ok"] += 1
        else:
            counts["zaru_no"] += 1
        return
    omega_veh = st.R_sv @ (gyro[k] - st.b_g)
    accel_veh = st.R_sv @ (accel[k] - st.b_a)
    if nhc_is_valid(
        float(np.linalg.norm(st.v)), float(omega_veh[2]), float(accel_veh[1]), cfg
    ):
        f.update_nhc()
        counts["nhc"] += 1


@dataclass
class WindowRun:
    """One outage window, dead-reckoned from the aided state at its first sample.

    Row `i` of each array is sample `start_idx + i`; there are `n_samples + 1` rows, the last
    being the sample at which the outage ends and the window's final epoch is read.
    """

    start_idx: int
    position_ned: np.ndarray  # (n_samples + 1, 2)
    yaw_rad: np.ndarray  # (n_samples + 1,)
    position_var: np.ndarray  # (n_samples + 1, 2)
    n_zupt: int
    n_zaru_applied: int
    n_zaru_rejected: int
    n_nhc: int
    #: Whether the filter had aligned -- levelled, mount resolved, heading set -- when this
    #: window opened. A window from an unaligned snapshot is scored like any other and is
    #: exactly what a phone that had not yet moved would have produced; the flag travels to
    #: `windows.csv` so the count can be read.
    aligned: bool = True


def replay_window(
    snapshot: Snapshot, gyro: np.ndarray, accel: np.ndarray, dt: np.ndarray, outage: Outage,
    *, name: str = "<unnamed>",
) -> WindowRun:
    """Dead-reckon one window from the aided filter state at its first sample.

    The GNSS update is never called here -- there is no mask to consult, because inside an
    outage there is nothing to consult it about. Propagation, ZUPT, ZARU and NHC run exactly as
    in the aided pass, through `_step_constraints`. The snapshot is copied before use so a
    window cannot leave its state in the one the next window of the same start reads.

    Runs through `outage.end_idx` inclusive: `pos[end_idx]` is the position at the instant the
    outage ends, which is the window's last epoch, and it is read *before* any fix at that sample
    could be applied -- a re-acquisition belongs to the aided pass, not to the outage it closes.
    """
    f = copy.deepcopy(snapshot.filter)
    f.hold_biases = HOLD_BIASES_IN_OUTAGE
    cfg = f.cfg
    window = max(1, int(round(cfg.zupt_window_s * SAMPLE_RATE_HZ)))
    n_rows = outage.n_samples + 1
    pos = np.zeros((n_rows, 2))
    yaw = np.zeros(n_rows)
    pvar = np.zeros((n_rows, 2))
    counts = dict(zupt=0, zaru_ok=0, zaru_no=0, nhc=0)
    for i, k in enumerate(range(outage.start_idx, outage.end_idx + 1)):
        # An unaligned snapshot has no dead-reckoning solution: the filter was holding its last
        # fix when the outage opened and it keeps holding it. Scored like any other window --
        # the error is the distance the vehicle drove -- and flagged (`WindowRun.aligned`).
        if snapshot.aligned and k > 0:
            f.propagate(gyro[k], accel[k], float(dt[k - 1]))
            _check_physical(f, k, name, f"the {outage.length_s} s window at {outage.start_idx}")
        if snapshot.aligned:
            _step_constraints(f, k, gyro, accel, cfg, window, counts)
        pos[i] = f.state.p[:2]
        yaw[i] = f.state.yaw
        pvar[i] = np.diag(f.P)[6:8]
    return WindowRun(
        start_idx=outage.start_idx,
        position_ned=pos,
        yaw_rad=yaw,
        position_var=pvar,
        n_zupt=counts["zupt"],
        n_zaru_applied=counts["zaru_ok"],
        n_zaru_rejected=counts["zaru_no"],
        n_nhc=counts["nhc"],
        aligned=snapshot.aligned,
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
    #: Whether the filter was aligned when it started -- levelled, mount resolved, heading set.
    #: False means the yaw block of `P0` is `UNALIGNED_YAW_SIGMA_RAD`, NHC is withheld, and
    #: `run_filter` completes the alignment at the first open fix where the data allow it.
    heading_aligned: bool = True
    heading_source: str = "chord"  # "course" | "chord" | "none"
    mount_source: str = "none"  # "dynamics" | "pca" | "none"
    yaw_sigma_rad: float = float("nan")
    level_sigma_rad: float = float("nan")


# --------------------------------------------------------------------------------------------
# Alignment -- levelling, mount and heading, from what the phone has (D-115)
#
# Three things have to be known before the accelerometer can be integrated: which way is up
# (levelling), which way the vehicle points in the phone (the mount), and which way the vehicle
# points in the world (the heading). Each comes from a different source and each can be
# unavailable when the recording opens, so alignment is an *attempt* that either completes or
# reports what it is still missing, and it is retried at every open fix until it completes.
# --------------------------------------------------------------------------------------------

#: Trailing window an in-motion alignment attempt reads, in seconds. `mount_yaw_from_dynamics`
#: needs the vehicle to have accelerated and, ideally, turned; 60 s of driving usually holds
#: both. The initial attempt reads the warmup instead, which is `WARMUP_S`.
ALIGN_WINDOW_S = 60

#: Levelling at a detected stop is bounded by `sqrt(zupt_accel_var_thresh) / g` (D-055; 0.83 deg
#: at the D-115 threshold);
#: a moving window's levelling is that plus the window's mean dynamic acceleration over g, which
#: `_level_sigma` adds from the reference.
LEVEL_SIGMA_STATIONARY_RAD = float(np.sqrt(FilterConfig().zupt_accel_var_thresh) / 9.80665)


@dataclass(frozen=True)
class VehicleReference:
    """Per-sample vehicle-frame acceleration built from the receiver's speed and the gyro."""

    forward: np.ndarray  # m/s^2, finite-differenced GNSS speed held over each fix interval
    right: np.ndarray  # m/s^2, speed * yaw rate about down
    speed: np.ndarray  # m/s, the last fix's speed held forward


def vehicle_reference(
    seq: Sequence, gyro: np.ndarray, up: np.ndarray, fix_idx: np.ndarray, n: int, *, upto: int
) -> VehicleReference | None:
    """The vehicle's own acceleration, per sample, from what the phone has -- or None when the
    stream carries no `gps_speed_mps` (the unit-test fixtures).

    **Causal to `upto`.** A fix interval's forward acceleration is known only once its later
    fix has arrived, so intervals ending after `upto` contribute nothing; the speed is the
    last fix at or before each sample, held. Both would otherwise read a window's own future,
    which is the leak `initialise_filter`'s docstring rules out.

    The fixes are ~9 s apart on most stems, so `forward` is a step function -- coarse for a
    magnitude, adequate for a sign. `right` is at the full 10 Hz: centripetal force is
    `speed * omega_down`, and `omega_down` is the gyro projected on `-up`. Between them they
    carry every acceleration and every turn the vehicle made, each with its sign.
    """
    gnss = seq.gnss
    if "gps_speed_mps" not in gnss.columns:
        return None
    idx = gnss["sample_idx"].to_numpy(dtype=int)
    speed = gnss["gps_speed_mps"].to_numpy(dtype=float)
    ok = np.isfinite(speed) & (idx >= 0) & (idx < n) & (idx <= upto)
    idx, speed = idx[ok], speed[ok]
    if idx.size == 0:
        return None

    last = np.searchsorted(idx, np.arange(n), side="right") - 1
    held = np.where(last >= 0, speed[np.clip(last, 0, None)], np.nan)

    forward = np.zeros(n)
    if idx.size >= 2:
        dt_s = np.diff(idx) / SAMPLE_RATE_HZ
        accel_fwd = np.divide(np.diff(speed), dt_s, out=np.zeros(dt_s.shape), where=dt_s > 0)
        for a, lo, hi in zip(accel_fwd, idx[:-1], idx[1:], strict=True):
            forward[lo:hi] = a

    omega_down = -(gyro @ up)
    return VehicleReference(forward=forward, right=held * omega_down, speed=held)


@dataclass(frozen=True)
class Alignment:
    """One attempt's result: the vertical, the mount, and how well each is known."""

    up: np.ndarray  # unit, phone frame
    mount: MountInit
    mount_source: str  # "dynamics" | "pca" | "none"
    level_sigma_rad: float

    @property
    def mount_resolved(self) -> bool:
        return self.mount.sign_resolved


def level_and_mount(
    seq: Sequence, gyro: np.ndarray, accel: np.ndarray, fix_idx: np.ndarray, lo: int, hi: int,
    *, upto: int,
) -> Alignment | None:
    """Levelling and mount over samples `[lo, hi)`, reading nothing after `upto`.

    **Up is the accelerometer's mean.** The stream's `gravity_*` channel is not a sensor: it is
    `(0, 0, 9.807)` to within 0.05 m/s^2 for the whole of every held-out recording, while the
    accelerometer's own mean direction drifts up to 6 deg from it over 35 min (Vta1a). A vertical
    that never moves cannot level a phone that does; the mean specific force over a window can,
    to the window's mean dynamic acceleration over g.

    **The mount comes from `mount_yaw_from_dynamics`** when the stream carries GNSS speed -- a
    signed fit with no 180-degree ambiguity -- and from `pca_mount_yaw` otherwise, which is the
    fixtures' path. The dynamics fit reports itself unresolved when its correlation or sample
    count is below its bar, and the caller then withholds NHC and tries again at the next fix,
    rather than constraining velocity through an axis it does not have.
    """
    hi = min(hi, accel.shape[0])
    if hi - lo < 3:
        return None
    window = accel[lo:hi]
    finite = np.isfinite(window).all(axis=1)
    if finite.sum() < 3:
        return None
    mean = window[finite].mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if norm < 1e-6:
        return None
    up = mean / norm

    ref = vehicle_reference(seq, gyro, up, fix_idx, accel.shape[0], upto=upto)
    if ref is None:
        mount = pca_mount_yaw(window[finite], up)
        return Alignment(
            up=up, mount=mount, mount_source="pca",
            level_sigma_rad=_level_sigma(ref, lo, hi, residual=0.0),
        )

    mount = mount_yaw_from_dynamics(
        window[finite], up, ref.forward[lo:hi][finite], ref.right[lo:hi][finite]
    )
    residual = 0.0
    if mount.sign_resolved:
        # The mean specific force over a window that accelerated is not vertical: it leans
        # forward by the window's mean acceleration over g, and taking it as up puts that
        # acceleration back into the filter as a standing deceleration. S3a's warmup runs 3 to
        # 12 m/s, a 0.3 m/s^2 mean that levelling alone got 1.8 deg wrong. With the mount known,
        # the mean acceleration is known in the phone frame -- the speed change over the window
        # along the fitted forward axis -- and is taken out before the vertical is read. What is
        # left in the levelling is the part the speed samples cannot see, which `_level_sigma`
        # carries as their own residual.
        mean_dynamic, residual = _mean_forward_acceleration(ref, lo, hi)
        forward_phone = mount.r_sv[0]
        corrected = mean - mean_dynamic * forward_phone
        norm = float(np.linalg.norm(corrected))
        if norm > 1e-6:
            up = corrected / norm
            mount = mount_yaw_from_dynamics(
                window[finite], up, ref.forward[lo:hi][finite], ref.right[lo:hi][finite]
            )
    return Alignment(
        up=up,
        mount=mount,
        mount_source="dynamics" if mount.sign_resolved else "none",
        level_sigma_rad=_level_sigma(ref, lo, hi, residual=residual),
    )


def _mean_forward_acceleration(ref: VehicleReference, lo: int, hi: int) -> tuple[float, float]:
    """`(mean, residual)` of the vehicle's forward acceleration over `[lo, hi)` from the held
    GNSS speed: the speed change over the window's span, and what the held speed's staleness
    could hide, as the uncertainty on that mean."""
    speed = ref.speed[lo:hi]
    finite = np.isfinite(speed)
    if finite.sum() < 2:
        return 0.0, 0.0
    span_s = max((hi - lo) / SAMPLE_RATE_HZ, 1e-6)
    mean = float(speed[finite][-1] - speed[finite][0]) / span_s
    # The held speed is stale by up to one fix interval, so the window's mean can be wrong by
    # one interval's worth of the largest acceleration the reference saw, over the span.
    changes = np.flatnonzero(np.diff(speed[finite]) != 0)
    stale_s = float(np.max(np.diff(changes))) / SAMPLE_RATE_HZ if changes.size >= 2 else span_s
    largest = float(np.nanmax(np.abs(ref.forward[lo:hi]))) if hi > lo else 0.0
    residual = largest * min(stale_s, span_s) / span_s
    return mean, residual


def _level_sigma(ref: VehicleReference | None, lo: int, hi: int, *, residual: float) -> float:
    """1-sigma roll/pitch error of levelling on this window: the stationary bound, plus the
    part of the window's mean acceleration that was *not* taken out -- all of it when the mount
    was unresolved and none could be, the held speed's staleness when it was -- over g."""
    sigma = LEVEL_SIGMA_STATIONARY_RAD
    if ref is not None:
        uncorrected = residual
        speed = ref.speed[lo:hi]
        finite = np.isfinite(speed)
        if residual == 0.0 and finite.sum() >= 2:
            span_s = max((hi - lo) / SAMPLE_RATE_HZ, 1e-6)
            uncorrected = abs(float(speed[finite][-1] - speed[finite][0])) / span_s
        sigma = float(np.hypot(sigma, uncorrected / 9.80665))
    return sigma


def apply_alignment(
    f: InEKF, alignment: Alignment, course_rad: float, speed_mps: float
) -> tuple[float, float]:
    """Write an alignment into the filter: `R_sv`, `R`, `v`, and a fresh `P` for everything the
    alignment (re)initialised. Returns `(yaw_sigma_rad, level_sigma_rad)`.

    `R = R_vn @ R_sv`: the phone's attitude is the vehicle's heading composed with the mount
    (see `initialise_filter`), with the vehicle taken as level. The heading is the receiver's
    course at this fix, worth `course_sigma_rad` at this speed; the mount block carries the
    estimator's spread; roll and pitch carry the levelling's.

    The velocity block is worth the receiver's Doppler velocity, `course_cross_track_sigma_mps`
    (0.5 m/s), and not `initial_covariance`'s 4.24 m/s position chord: the velocity was set from
    the Doppler speed and course, and the block has to say so for the stationary veto in
    `_step_constraints` to hold from the first sample -- at 4.24 m/s the filter could not
    exclude being stopped while doing 3.5 m/s, and on S3a a false ZUPT 2 s into the run took
    the velocity to zero and the filter never recovered (D-115).

    `P` is replaced whole: before alignment the filter was not running (`run_filter`), so
    there is nothing in it to keep.
    """
    cfg = f.cfg
    f.state.R_sv = alignment.mount.r_sv
    f.state.R = yaw_only_rotation(course_rad) @ f.state.R_sv
    f.state.v = np.array([speed_mps * np.cos(course_rad), speed_mps * np.sin(course_rad), 0.0])
    yaw_sigma = course_sigma_rad(cfg, speed_mps)
    fresh = initial_covariance(
        cfg,
        mount_sigma_rad=alignment.mount.spread_rad,
        yaw_sigma_rad=yaw_sigma,
        level_sigma_rad=alignment.level_sigma_rad,
        velocity_sigma_mps=cfg.course_cross_track_sigma_mps,
    )
    # Every sigma above is a plain error about the vehicle; the filter's error is
    # right-invariant, about the origin. See `right_invariant_from_plain`.
    f.P = right_invariant_from_plain(fresh, f.state.p, f.state.v)
    return yaw_sigma, alignment.level_sigma_rad


def attempt_alignment(
    f: InEKF, seq: Sequence, gyro: np.ndarray, accel: np.ndarray, fix_idx: np.ndarray, k: int,
    course_rad: float, speed_mps: float,
) -> bool:
    """In-motion alignment at open fix `k`, completing the initialisation `initialise_filter`
    could not: reads the trailing `ALIGN_WINDOW_S` and nothing after `k`, and returns whether it
    aligned.

    Done once, and only ever from an *open* fix, so an outage that begins before the vehicle
    has aligned is scored exactly as a phone would experience it: unaligned. It is not a mode and
    not a re-initialisation on re-acquisition -- after this the heading and the mount are the
    filter's to keep, corrected by the ordinary gated updates (D-001).
    """
    lo = max(0, k + 1 - ALIGN_WINDOW_S * SAMPLE_RATE_HZ)
    alignment = level_and_mount(seq, gyro, accel, fix_idx, lo, k + 1, upto=k)
    if alignment is None or not alignment.mount_resolved:
        return False
    apply_alignment(f, alignment, course_rad, speed_mps)
    return True


def initialise_filter(
    f: InEKF,
    seq: Sequence,
    accel: np.ndarray,
    fix_idx: np.ndarray,
    fix_ned: np.ndarray,
    *,
    warmup_s: int = WARMUP_S,
    gyro: np.ndarray | None = None,
) -> FilterInit:
    """Start the filter from the `S-` stream's own GNSS and IMU, never from truth.

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

    Everything comes from inside the warmup window:

    * **Position** -- the first fix. It is the measurement, not an estimate of one.
    * **Levelling and the mount** -- `level_and_mount` over the warmup: up from the accelerometer
      mean, the mount from `mount_yaw_from_dynamics` (D-115). Until D-115 the mount came from
      `pca_mount_yaw` with its sign from a reference that was constant over a stationary warmup,
      and on Vta1a it came out backwards with `sign_resolved` True.
    * **Velocity and heading** -- the receiver's own course and speed at the first fix
      (`fix_course_arrays`), when the vehicle is moving. The state being initialised is the one
      at sample zero, so the fix that describes it is the first one, not a chord to the last: a
      30 s chord is the *mean* direction over the warmup, and on the held-out stems where the
      road turns in those 30 s it was 61-105 deg from the heading at the moment the first
      outage opens. Streams without a course column -- the unit-test fixtures -- fall back to the
      first-to-last chord, which is exact for a fixture driving straight.

    A vehicle that is stationary at its first fix, or whose warmup holds too little dynamics to
    resolve the mount, is **not aligned**: the yaw block is `UNALIGNED_YAW_SIGMA_RAD`, NHC is
    withheld, and `run_filter` calls `attempt_alignment` at each open fix until it completes.
    The vertical is still set, so that propagation cancels gravity while it waits.

    `gyro` is optional for the callers that predate D-115; without it the mount falls back to
    PCA, which is the fixtures' path anyway.
    """
    n_warm = min(int(warmup_s * SAMPLE_RATE_HZ), accel.shape[0])
    in_warmup = np.flatnonzero((fix_idx >= 0) & (fix_idx < n_warm))
    if in_warmup.size:
        f.state.p = np.asarray(fix_ned[in_warmup[0]], dtype=float).copy()

    if gyro is None:
        gyro = np.zeros_like(accel)
    alignment = level_and_mount(seq, gyro, accel, fix_idx, 0, n_warm, upto=n_warm - 1)

    yaw = 0.0
    speed = 0.0
    aligned = False
    source = "none"
    course = fix_course_arrays(seq)
    if course is not None:
        if in_warmup.size:
            j = in_warmup[0]
            c, v = float(course[0][j]), float(course[1][j])
            if np.isfinite(c) and np.isfinite(v) and v >= f.cfg.course_min_speed_mps:
                yaw, speed = c, v
                aligned, source = True, "course"
    elif in_warmup.size >= 2:
        first, last = in_warmup[0], in_warmup[-1]
        step = np.asarray(fix_ned[last], dtype=float) - np.asarray(fix_ned[first], dtype=float)
        span_s = float(fix_idx[last] - fix_idx[first]) / SAMPLE_RATE_HZ
        if span_s > 0 and float(np.linalg.norm(step[:2])) >= MIN_HEADING_DISPLACEMENT_M:
            yaw = float(np.arctan2(step[1], step[0]))
            speed = float(np.linalg.norm(step[:2])) / span_s
            aligned, source = True, "chord"

    # A heading without a resolved mount is not an alignment: `R = R_vn @ R_sv` needs both, and
    # a heading composed with a backwards mount integrates every acceleration as a braking. The
    # chord path (fixtures) keeps its PCA mount as it always did.
    mount_ok = alignment is not None and (alignment.mount_resolved or source == "chord")
    aligned = aligned and mount_ok

    if aligned:
        yaw_sigma, level_sigma = apply_alignment(f, alignment, yaw, speed)
    else:
        # Level the phone so gravity cancels while the filter waits for a heading; the yaw and
        # mount are unknown and `P0` says so. `R_sv`'s down row is right whatever its yaw is.
        if alignment is not None:
            f.state.R_sv = alignment.mount.r_sv
            level_sigma = alignment.level_sigma_rad
            mount_sigma = float(np.pi / 2)
        else:
            level_sigma = None
            mount_sigma = None
        f.state.R = f.state.R_sv.copy()
        f.state.v = np.zeros(3)
        yaw_sigma = UNALIGNED_YAW_SIGMA_RAD
        f.P = right_invariant_from_plain(
            initial_covariance(
                f.cfg, mount_sigma_rad=mount_sigma, yaw_sigma_rad=yaw_sigma,
                level_sigma_rad=level_sigma,
            ),
            f.state.p,
            f.state.v,
        )
        yaw, speed = 0.0, 0.0

    mount = None if alignment is None else alignment.mount
    return FilterInit(
        yaw_rad=yaw,
        speed_mps=speed,
        mount_yaw_rad=float("nan") if mount is None else mount.yaw_rad,
        mount_spread_rad=float("nan") if mount is None else mount.spread_rad,
        mount_sign_resolved=False if mount is None else mount.sign_resolved,
        n_warmup_fixes=int(in_warmup.size),
        heading_aligned=aligned,
        heading_source=source if aligned else "none",
        mount_source="none" if alignment is None else alignment.mount_source,
        yaw_sigma_rad=float(np.sqrt(f.P[2, 2])),
        level_sigma_rad=float(np.sqrt(f.P[0, 0])),
    )


def window_trajectory(
    position_ned: np.ndarray, outage: Outage, *, origin: int = 0
) -> BaselineTrajectory:
    """Slice one outage window's epoch boundaries out of a position series.

    Row `i` of `position_ned` is sample `origin + i`: zero for a whole-sequence series, the
    window's own `start_idx` for a `WindowRun`.
    """
    idx = np.arange(outage.start_idx, outage.end_idx + 1, EPOCH_STRIDE)
    if idx[-1] != outage.end_idx:
        raise ValueError(
            f"outage [{outage.start_idx}, {outage.end_idx}) is not a whole number of "
            f"{EPOCH_STRIDE}-sample epochs"
        )
    rows = idx - origin
    if rows[0] < 0 or rows[-1] >= position_ned.shape[0]:
        raise ValueError(f"outage window runs past the end of the sequence at sample {idx[-1]}")
    disp = np.diff(position_ned[rows], axis=0)
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
    #: For the filter: whether it had aligned when the window opened (`WindowRun.aligned`). A
    #: window from an unaligned filter is a held fix, not a navigation solution, and the count of
    #: those travels with every number (`summary.json`: `n_filter_windows_unaligned`). Always
    #: True for the two baselines, which are initialised per window.
    aligned: bool = True

    def as_row(self) -> dict[str, object]:
        return {
            "method": self.method,
            "sequence": self.sequence,
            "length_s": self.length_s,
            "start_idx": self.start_idx,
            "aligned": self.aligned,
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
    aided_passes: dict[str, dict] | None = None,
) -> list[WindowResult]:
    """Every window of every length for one sequence, all three methods.

    One GNSS-aided filter pass for the sequence, snapshotted at the first sample of every window
    of every length, and one dead-reckoned replay per window from its snapshot -- so each window
    is entered aided, exactly as if the filter had been run once per window with GNSS open
    everywhere but inside it. See the module docstring for what this replaced and why.

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
    for windows in sweep.values():
        assert_non_overlapping(windows)
    starts = {o.start_idx for windows in sweep.values() for o in windows}
    if not starts:
        return out

    try:
        aided = run_filter(
            gyro, accel, dt, fix_idx, fix_ned, fix_sigma, np.ones(n, dtype=bool),
            cfg=cfg, seq=seq, snapshot_at=starts,
        )
    except FilterDivergedError as exc:
        # The *aided* pass left physical bounds: with every fix available to correct it, the
        # filter still ran away, and every snapshot after that sample -- and, since the state was
        # wrong before it was caught, some before it -- describes nothing. The stem is unusable.
        raise SequenceUnusable(str(exc)) from exc
    if aided_passes is not None:
        aided_passes[seq.name] = aided.aided_pass_summary()

    for length_s, windows in sorted(sweep.items()):
        for outage in windows:
            t0 = float(t_abs_s[outage.start_idx])
            try:
                run = replay_window(
                    aided.snapshots[outage.start_idx], gyro, accel, dt, outage, name=seq.name
                )
            except FilterDivergedError as exc:
                # Window-scoped, unlike the aided pass: the next window starts from its own
                # aided snapshot and is untouched by this one. The window is dropped and
                # counted (D-089's rule -- the omission travels with the number), never scored
                # from a state that reached 150 m/s and never silently left out.
                print(
                    f"[idr-eval] DROPPED WINDOW {seq.name} {length_s}s @{outage.start_idx}: "
                    f"{exc}",
                    file=sys.stderr,
                )
                if dropped is not None:
                    dropped.append(
                        DroppedWindow(
                            sequence=seq.name, length_s=length_s, start_idx=outage.start_idx,
                            kind="filter_diverged", reason=str(exc),
                        )
                    )
                continue
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
                    "filter": window_trajectory(
                        run.position_ned, outage, origin=outage.start_idx
                    ),
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
                        aligned=run.aligned if method == "filter" else True,
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
    idx = np.arange(outage.start_idx, outage.end_idx + 1, EPOCH_STRIDE) - run.start_idx
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


def gate1_by_mount_class(results: list[WindowResult]) -> dict[str, dict[str, object]]:
    """Gate 1 drift ratio and window counts partitioned by mount class (D-115).

    The in-motion gyro white level on quiet mounts (S3a, S3c) is 1.7-1.9 deg/s vs 4-20 deg/s on
    every Vta/Vw stem; heading random walk 2.9 deg vs 21-44 deg at 60 s. On vibrating mounts the
    IMU stream carries un-anti-aliased engine and cabin vibration aliased into 10 Hz, random-walking
    the heading integral. Gate 1 should be quoted with this split, never pooled (D-115).
    """
    windows_60s = [r for r in results if r.length_s == GATE1_LENGTH_S]
    out: dict[str, dict[str, object]] = {}
    for mount_class in ("quiet", "vibrating"):
        class_windows = [
            r
            for r in windows_60s
            if (
                r.sequence in QUIET_MOUNT
                if mount_class == "quiet"
                else r.sequence not in QUIET_MOUNT
            )
        ]
        filter_drifts = [r.metrics.drift_pct for r in class_windows if r.method == "filter"]
        gnss_drifts = [r.metrics.drift_pct for r in class_windows if r.method == "gnss_available"]

        n_filter = len(filter_drifts)
        n_gnss = len(gnss_drifts)

        filter_med = float(np.median(filter_drifts)) if n_filter > 0 else None
        gnss_med = float(np.median(gnss_drifts)) if n_gnss > 0 else None

        ratio = filter_med / gnss_med if filter_med is not None and gnss_med else None
        in_range = None if ratio is None else GATE1_RATIO_RANGE[0] <= ratio <= GATE1_RATIO_RANGE[1]

        out[mount_class] = {
            "filter_drift_pct_median": filter_med,
            "gnss_available_drift_pct_median": gnss_med,
            "ratio": ratio,
            "in_range": in_range,
            "n_windows_filter": n_filter,
            "n_windows_gnss_available": n_gnss,
        }
    return out


def gate1_ratio(
    by_method: dict[str, dict[str, dict]],
    results: list[WindowResult] | None = None,
) -> dict[str, object]:
    """The Gate 1 number: physics-only median drift over GNSS-available median drift, at 60 s.

    Reported, never judged. The gate is 3-5x and a human closes it against
    `docs/IMPLEMENTATION_PLAN.md` §7 -- this function's job is to make the number impossible to
    misquote by carrying the sequence count it rests on alongside it.
    """
    key = str(GATE1_LENGTH_S)
    have = [m for m in ("filter", "gnss_available") if key in by_method.get(m, {})]
    if len(have) < 2:
        out: dict[str, object] = {
            "measured": False,
            "why": f"no {GATE1_LENGTH_S} s windows for {METHODS[0]} and/or {METHODS[2]}",
        }
        if results is not None:
            out["by_mount_class"] = gate1_by_mount_class(results)
        return out
    num = by_method["filter"][key]
    den = by_method["gnss_available"][key]
    ratio = num["drift_pct_median"] / den["drift_pct_median"] if den["drift_pct_median"] else None
    out = {
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
    if results is not None:
        out["by_mount_class"] = gate1_by_mount_class(results)
    return out


def write_artefacts(
    out: Path,
    stamp: Stamp,
    results: list[WindowResult],
    replay: dict[str, dict] | None = None,
    dropped: list[DroppedWindow] | None = None,
    aided_passes: dict[str, dict] | None = None,
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
        # Filter windows opened before the phone had a heading and a mount (D-115). They are in
        # every filter number above as a held fix; this is how many.
        "n_filter_windows_unaligned": sum(
            1 for r in results if r.method == "filter" and not r.aligned
        ),
        "n_dropped_windows": len(dropped),
        "n_dropped_by_kind": {
            kind: sum(d.kind == kind for d in dropped)
            for kind in sorted({d.kind for d in dropped})
        },
        "by_method": by_method,
        # Whether outage windows froze the bias states (`HOLD_BIASES_IN_OUTAGE`, D-130).
        "biases_held_in_outage": HOLD_BIASES_IN_OUTAGE,
        "gate1": gate1_ratio(by_method, results=results),
        "trajectories": sorted(replay or {}),
        "dropped_windows": [d.as_row() for d in dropped],
        # The aided pass each stem's windows were replayed from (D-115): alignment, the process
        # noise it ran with, and its update counts, so a claim about any of them is checkable.
        "aided_pass": dict(sorted((aided_passes or {}).items())),
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
    aided_passes: dict[str, dict] = {}
    for name, seq in sorted(sequences.items()):
        try:
            truth = load_truth(paired_truth_path(name, args.data), name)
            results.extend(
                evaluate_sequence(
                    seq, truth, args.lengths, replay=replay, stamp=stamp, dropped=dropped,
                    aided_passes=aided_passes,
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

    summary = write_artefacts(args.out, stamp, results, replay, dropped, aided_passes)

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
