"""Measure which `S-` gyroscope column carries the vehicle's yaw rate, and what it costs.

`eval.run.imu_stream` builds the body rate as ``[gyro_yaw, gyro_pitch, gyro_roll]`` and hands it
to ``InEKF.propagate`` as device x/y/z, on the strength of D-047: the categorised folder spells
those three columns ``GYROSCOPE Yaw/Pitch/Roll``, the uncategorised folder spells the same three
columns ``GYROSCOPE X/Y/Z``, and they are byte-identical -- so the labels are AndroSensor's and
"gyro_yaw is device x, not the vertical axis".

That argument is sound about the *labels* and says nothing about which physical axis each column
carries. This module measures that, because the answer decides whether the filter integrates the
vehicle's yaw as a yaw or as a tilt, and a tilt tips gravity into the horizontal axes where it is
integrated twice.

**Tracked, not scratch** (D-090): the numbers below are cited in DECISION_LOG D-095 and in
phases.md section 11, and a number nobody can regenerate is a number nobody can defend (H-5).

Usage::

    .venv/bin/python -m eval.axis_check --data-root data
    .venv/bin/python -m eval.axis_check --data-root data --stems S3a S3c

Two independent estimators, because the per-fix one degrades badly on the 1 Hz-GNSS stems:

* **per-fix** -- Pearson correlation between the fix-to-fix course rate and each gyro column
  averaged over the same interval. Cheap, but differencing a 1 Hz course amplifies receiver noise.
* **block** -- regress the course change over a 30 s block on the *integrated* gyro over the same
  block. Integration averages the noise out; the slope is dimensionless and should be -1 or +1 for
  the column that is the yaw axis, and the R^2 says whether to believe it.

The third column is the consequence: the mean and RMS of ``R @ accel + GRAVITY_NED`` over the
first 60 s, with ``R`` started by `eval.run.initialise_filter` and propagated by the gyro. That
residual is the vehicle's own acceleration when the attitude is right, and gravity when it is not.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np

from core.reference.inekf import (
    GRAVITY_NED,
    FilterConfig,
    InEKF,
    chi2_gate,
    is_stationary,
    nhc_is_valid,
    propagate_nominal,
    skew,
)
from eval.loaders.io_vnbd import load_split
from eval.loaders.truth import load_truth, paired_truth_path
from eval.run import (
    SAMPLE_RATE_HZ,
    assert_uniform_grid,
    fix_arrays,
    imu_stream,
    initialise_filter,
)

#: The order `imu_stream` reads them in, which is also their order in the shipped file.
GYRO_COLUMNS = ("gyro_yaw", "gyro_pitch", "gyro_roll")

#: Blocks shorter than this do not accumulate enough heading change to regress against; longer
#: ones start to average opposing turns away. 30 s is the warmup window `run_filter` already uses.
BLOCK_S = 30.0

#: Below this the reported course over ground is receiver noise rather than a heading, so the
#: interval carries no information about the yaw rate. **D-085's own threshold**, 15 km/h, taken
#: rather than invented; `--min-speed` sweeps it because the fit quality depends on it and that
#: dependence is itself evidence -- a column that is really the yaw axis fits *better* as the
#: noisier low-speed intervals are excluded, and one that is not does not.
MIN_SPEED_MPS = 15.0 / 3.6

#: Fewer than this and neither estimator is worth reporting for the stem.
MIN_INTERVALS = 10


@dataclass(frozen=True)
class AxisMeasurement:
    """What one stem says about which column is the yaw axis."""

    stem: str
    n_intervals: int
    n_blocks: int
    corr: tuple[float, float, float]
    slope: tuple[float, float, float]
    r2: tuple[float, float, float]
    residual_shipped_rms: float
    residual_corrected_rms: float
    attitude_change_deg: float

    @property
    def best_column(self) -> str:
        """The column whose integrated rate best explains the measured course change."""
        return GYRO_COLUMNS[int(np.argmax(self.r2))]


def _course_and_gyro(seq, gyro: np.ndarray, dt: np.ndarray, min_speed: float):
    """`(course_rate, gyro_mean, course_change, gyro_integral, keep)` over fix intervals.

    Everything both estimators need, computed once. `keep` is the moving mask -- a standstill's
    course over ground is noise, not a heading.
    """
    gnss = seq.gnss
    if "gps_orientation_deg" not in gnss.columns or "gps_speed_mps" not in gnss.columns:
        return None
    idx = gnss["sample_idx"].to_numpy(dtype=int)
    course = gnss["gps_orientation_deg"].to_numpy(dtype=float)
    # The column is in metres per second -- see D-096, D-102.
    speed_mps = gnss["gps_speed_mps"].to_numpy(dtype=float)
    ok = (
        np.isfinite(course)
        & np.isfinite(speed_mps)
        & (idx >= 0)
        & (idx < gyro.shape[0])
    )
    idx, course, speed_mps = idx[ok], course[ok], speed_mps[ok]
    if idx.size < 3:
        return None

    heading = np.unwrap(np.radians(course))
    span_s = np.diff(idx) / SAMPLE_RATE_HZ
    rate = np.diff(heading) / np.where(span_s > 0, span_s, np.nan)
    gyro_mean = np.array(
        [
            gyro[idx[i] : idx[i + 1]].mean(axis=0)
            if idx[i + 1] > idx[i]
            else np.full(3, np.nan)
            for i in range(idx.size - 1)
        ]
    )
    moving = (speed_mps[:-1] > min_speed) & (speed_mps[1:] > min_speed)
    keep = moving & np.isfinite(rate) & np.isfinite(gyro_mean).all(axis=1)

    cumulative = np.vstack([np.zeros(3), np.cumsum(gyro[1:] * dt[:, None], axis=0)])
    return idx, heading, speed_mps, rate, gyro_mean, keep, cumulative


def regress_heading_on_integrated_gyro(
    d_heading: np.ndarray, d_gyro: np.ndarray
) -> tuple[list[float], list[float]]:
    """Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.

    The column that is the vehicle's yaw axis regresses on the measured heading change with a
    slope of +/-1 -- both are angles in radians over the same block, so the relation is an
    identity up to the axis sign, and there is no scale factor to fit or to get wrong. A column
    that is not the yaw axis has no such relation and shows it in R^2.
    """
    if d_gyro.ndim != 2 or d_gyro.shape[1] != 3:
        raise ValueError(f"expected (n, 3) integrated rates, got {d_gyro.shape}")
    if d_heading.shape != (d_gyro.shape[0],):
        raise ValueError(
            f"{d_heading.shape} heading changes against {d_gyro.shape[0]} blocks; they must be "
            "the same blocks"
        )
    slope: list[float] = []
    r2: list[float] = []
    total = float(((d_heading - d_heading.mean()) ** 2).sum())
    for c in range(3):
        x = d_gyro[:, c]
        coefficients = np.polyfit(x, d_heading, 1)
        residual = d_heading - np.polyval(coefficients, x)
        slope.append(float(coefficients[0]))
        r2.append(float(1 - (residual**2).sum() / total) if total > 0 else float("nan"))
    return slope, r2


def _residual_specific_force(
    seq, gyro: np.ndarray, accel: np.ndarray, dt: np.ndarray, fix_idx, fix_ned, seconds: float
):
    """`(rms, attitude change)` of `R @ accel + GRAVITY_NED` with `R` propagated by `gyro`.

    The filter's own initialiser supplies `R`, so this is what `run_filter` actually integrates.
    """
    f = InEKF(FilterConfig())
    initialise_filter(f, seq, accel, fix_idx, fix_ned)
    r0 = f.state.R.copy()
    n = min(int(seconds * SAMPLE_RATE_HZ), gyro.shape[0])
    rot = r0.copy()
    residual = np.zeros((n, 3))
    for k in range(n):
        residual[k] = rot @ accel[k] + GRAVITY_NED
        if k + 1 < n:
            rot, _, _ = propagate_nominal(
                rot, np.zeros(3), np.zeros(3), gyro[k + 1], accel[k + 1], float(dt[k])
            )
    turned = np.degrees(np.arccos(np.clip((np.trace(r0.T @ rot) - 1) / 2, -1, 1)))
    return float(np.sqrt((residual**2).sum(axis=1)).mean()), float(turned)


def measure(
    stem: str,
    data_root: str,
    *,
    seconds: float = 60.0,
    min_speed: float = MIN_SPEED_MPS,
) -> AxisMeasurement | None:
    """Everything one stem has to say, or None if it cannot say anything."""
    seq = load_split(data_root, (stem,))[stem]
    raw_gyro = seq.imu[list(GYRO_COLUMNS)].to_numpy(dtype=float)
    _, accel, t_rel_s = imu_stream(seq)
    dt = assert_uniform_grid(seq.name, t_rel_s)
    truth = load_truth(paired_truth_path(stem, data_root), stem)
    fix_idx, fix_ned, _ = fix_arrays(seq, float(truth.lat[0]), float(truth.lon[0]))

    prepared = _course_and_gyro(seq, raw_gyro, dt, min_speed)
    if prepared is None:
        return None
    idx, heading, speed_mps, rate, gyro_mean, keep, cumulative = prepared
    if keep.sum() < MIN_INTERVALS:
        return None

    corr = tuple(
        float(np.corrcoef(gyro_mean[keep][:, c], rate[keep])[0, 1]) for c in range(3)
    )

    # Blocks of BLOCK_S, measured in fixes rather than samples so a 1 Hz and a 9 s stem both get
    # a block of the same duration.
    cadence_s = float(np.median(np.diff(idx))) / SAMPLE_RATE_HZ
    step = max(1, int(round(BLOCK_S / cadence_s)))
    if idx.size <= step + 1:
        return None
    d_heading = heading[step:] - heading[:-step]
    d_gyro = cumulative[idx[step:]] - cumulative[idx[:-step]]
    block_keep = (
        (speed_mps[:-step] > min_speed)
        & (speed_mps[step:] > min_speed)
        & np.isfinite(d_heading)
        & np.isfinite(d_gyro).all(axis=1)
    )
    if block_keep.sum() < MIN_INTERVALS:
        return None

    slope, r2 = regress_heading_on_integrated_gyro(d_heading[block_keep], d_gyro[block_keep])

    shipped_rms, turned = _residual_specific_force(
        seq, raw_gyro, accel, dt, fix_idx, fix_ned, seconds
    )
    # The correction under test: the measured yaw column moved into the vertical slot. The two
    # horizontal channels are zeroed rather than assigned, because which of them is device x and
    # which is device y is NOT measured by anything here -- see D-095.
    vertical_only = np.column_stack(
        [np.zeros(raw_gyro.shape[0]), np.zeros(raw_gyro.shape[0]), raw_gyro[:, int(np.argmax(np.abs(r2)))]]
    )
    corrected_rms, _ = _residual_specific_force(
        seq, vertical_only, accel, dt, fix_idx, fix_ned, seconds
    )

    return AxisMeasurement(
        stem=stem,
        n_intervals=int(keep.sum()),
        n_blocks=int(block_keep.sum()),
        corr=corr,
        slope=tuple(slope),
        r2=tuple(r2),
        residual_shipped_rms=shipped_rms,
        residual_corrected_rms=corrected_rms,
        attitude_change_deg=turned,
    )



#: The eight signed assignments of the two remaining columns to device x and y, restricted to the
#: **four** whose permutation matrix has determinant +1. A gyroscope triad is right-handed, so a
#: relabelling that recovers the true frame is a proper rotation; the improper four would be a
#: reflection and cannot describe a mislabelled sensor. This narrows the choice without measuring
#: anything, which is the only narrowing available -- see D-095 for why the last step is not taken.
PROPER_HORIZONTAL_CANDIDATES: tuple[tuple[int, int, int, int], ...] = (
    (0, 2, +1, -1),
    (0, 2, -1, +1),
    (2, 0, +1, +1),
    (2, 0, -1, -1),
)


def candidate_gyro(gyro: np.ndarray, vertical: int, spec: tuple[int, int, int, int] | None):
    """The body rate under one candidate mapping. `spec=None` zeroes the horizontal channels.

    `vertical` is the column measured to carry the yaw rate; it goes into the device-z slot
    unchanged, because the sign there is measured and the sign of the horizontals is not.
    """
    if spec is None:
        zero = np.zeros(gyro.shape[0])
        return np.column_stack([zero, zero, gyro[:, vertical]])
    ix, iy, sx, sy = spec
    return np.column_stack([sx * gyro[:, ix], sy * gyro[:, iy], gyro[:, vertical]])


def innovation_sequence(
    seq, truth, gyro: np.ndarray, accel: np.ndarray, dt: np.ndarray, n_fixes: int
) -> tuple[list[float], list[float], int]:
    """`(innovation norms, chi-squared distances, accepted count)` over the first `n_fixes` fixes.

    `run_filter`'s loop, opened up so the gate can be read rather than only its verdict. The gate
    decision and the update are the filter's own -- `chi2_gate` and `update_gnss` are called, not
    reimplemented -- so this reports what `run_filter` would do and cannot drift away from it.
    """
    fix_idx, fix_ned, fix_sigma = fix_arrays(seq, float(truth.lat[0]), float(truth.lon[0]))
    cfg = FilterConfig()
    f = InEKF(cfg)
    initialise_filter(f, seq, accel, fix_idx, fix_ned)
    fix_at = {int(i): k for k, i in enumerate(fix_idx)}
    window = max(1, int(round(cfg.zupt_window_s * SAMPLE_RATE_HZ)))

    innovations: list[float] = []
    distances: list[float] = []
    accepted = 0
    for k in range(gyro.shape[0]):
        if k > 0:
            f.propagate(gyro[k], accel[k], float(dt[k - 1]))
        lo = max(0, k - window + 1)
        if k + 1 >= window and is_stationary(accel[lo : k + 1], gyro[lo : k + 1], cfg):
            f.update_zupt()
            f.update_zaru(gyro[k])
        elif nhc_is_valid(
            float(np.linalg.norm(f.state.v)),
            float(gyro[k][2] - f.state.b_g[2]),
            float(accel[k][1] - f.state.b_a[1]),
            cfg,
        ):
            f.update_nhc()

        j = fix_at.get(k)
        if j is None:
            continue
        cov = np.eye(3) * float(fix_sigma[j]) ** 2
        z = f.state.p - fix_ned[j]
        h = np.zeros((3, f.P.shape[0]))
        h[:, 0:3] = -skew(f.state.p)
        h[:, 6:9] = np.eye(3)
        s = h @ f.P @ h.T + cov
        innovations.append(float(np.linalg.norm(z)))
        distances.append(float(z @ np.linalg.solve(s, z)))
        if chi2_gate(z, s, cfg.chi2_gate_3dof):
            f.update_gnss(fix_ned[j], cov)
            accepted += 1
        if len(innovations) >= n_fixes:
            break
    return innovations, distances, accepted


def report_innovations(stem: str, data_root: str, n_fixes: int, min_speed: float) -> None:
    """D-094's table, under the shipped mapping and under every candidate D-095 could not rule out.

    This is the number the diagnosis rests on, so it is regenerable from a tracked command rather
    than from a scratch file nobody else has -- D-090.
    """
    seq = load_split(data_root, (stem,))[stem]
    truth = load_truth(paired_truth_path(stem, data_root), stem)
    raw_gyro = seq.imu[list(GYRO_COLUMNS)].to_numpy(dtype=float)
    _, accel, t_rel_s = imu_stream(seq)
    dt = assert_uniform_grid(seq.name, t_rel_s)

    measured = measure(stem, data_root, min_speed=min_speed)
    vertical = GYRO_COLUMNS.index(measured.best_column) if measured else 1
    print(f"{stem}: |innovation| in m at the first {n_fixes} GNSS fixes, then chi^2 at fix 1")
    print(f"  measured yaw axis: {GYRO_COLUMNS[vertical]}")
    header = " ".join(f"{i:>8}" for i in range(n_fixes))
    print(f"  {'mapping':>44} {header} {'chi2@1':>10} {'acc':>6}")

    def line(label: str, g: np.ndarray) -> None:
        innovations, distances, accepted = innovation_sequence(
            seq, truth, g, accel, dt, n_fixes
        )
        body = " ".join(f"{v:>8.1f}" for v in innovations)
        chi = distances[1] if len(distances) > 1 else float("nan")
        print(f"  {label:>44} {body} {chi:>10.1f} {accepted:>3}/{len(innovations)}")

    line("AS SHIPPED (yaw, pitch, roll)", raw_gyro)
    for spec in PROPER_HORIZONTAL_CANDIDATES:
        ix, iy, sx, sy = spec
        label = (
            f"({'+-'[sx < 0]}{GYRO_COLUMNS[ix]}, {'+-'[sy < 0]}{GYRO_COLUMNS[iy]}, "
            f"+{GYRO_COLUMNS[vertical]})"
        )
        line(label, candidate_gyro(raw_gyro, vertical, spec))
    line(f"(0, 0, +{GYRO_COLUMNS[vertical]})", candidate_gyro(raw_gyro, vertical, None))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--stems", nargs="*", default=None)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument(
        "--min-speed",
        type=float,
        default=MIN_SPEED_MPS,
        help="m/s below which course over ground is not treated as a heading (default: D-085's "
        "15 km/h)",
    )
    ap.add_argument(
        "--innovations",
        metavar="STEM",
        default=None,
        help="print D-094's GNSS innovation table for one stem under every candidate mapping",
    )
    ap.add_argument("--n-fixes", type=int, default=6)
    args = ap.parse_args()

    if args.innovations:
        report_innovations(args.innovations, args.data_root, args.n_fixes, args.min_speed)
        return 0

    if args.stems:
        stems = list(args.stems)
    else:
        from eval.splits import CHALLENGING, LONG_OUTAGE, TRAIN

        stems = list(
            dict.fromkeys(
                list(LONG_OUTAGE)
                + [s for group in CHALLENGING.values() for s in group]
                + list(TRAIN)
            )
        )

    print(f"{'stem':>8} {'blk':>5} " + " ".join(f"{c:>9}" for c in GYRO_COLUMNS) + "   " + " ".join(
        f"{'R2 ' + c.split('_')[1]:>9}" for c in GYRO_COLUMNS
    ) + f" {'yaw axis':>11} {'resid rms shipped->vert':>25} {'dR deg':>7}")
    results: list[AxisMeasurement] = []
    for stem in stems:
        try:
            m = measure(
                stem, args.data_root, seconds=args.seconds, min_speed=args.min_speed
            )
        except Exception as exc:  # a stem the protocol cannot use is not this module's problem
            print(f"{stem:>8}  skipped: {type(exc).__name__}: {exc}"[:110])
            continue
        if m is None:
            print(f"{stem:>8}  skipped: too few moving intervals")
            continue
        results.append(m)
        print(
            f"{m.stem:>8} {m.n_blocks:>5} "
            + " ".join(f"{v:>+9.3f}" for v in m.slope)
            + "   "
            + " ".join(f"{v:>9.3f}" for v in m.r2)
            + f" {m.best_column:>11} "
            + f"{m.residual_shipped_rms:>11.2f} ->{m.residual_corrected_rms:>9.2f}"
            + f" {m.attitude_change_deg:>7.1f}"
        )

    if results:
        votes = {c: sum(r.best_column == c for r in results) for c in GYRO_COLUMNS}
        print("\nyaw axis by best R^2: " + "  ".join(f"{k}={v}" for k, v in votes.items()))
        print(
            f"residual specific force rms over the first {args.seconds:.0f} s, median across "
            f"{len(results)} stems: shipped "
            f"{np.median([r.residual_shipped_rms for r in results]):.2f} m/s^2 -> vertical-only "
            f"{np.median([r.residual_corrected_rms for r in results]):.2f} m/s^2"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
