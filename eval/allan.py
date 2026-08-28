"""Allan variance from IO-VNBD's own stationary segments.

Seeds the InEKF process noise `Q_c` from the sensors that produced the graded data, rather than
from a teammate's phone on a desk (D-038). Everything here reads through the guarded `S-` loader;
there is no path in this file to the `V-` stream.

**What the numbers mean.** For a rate signal `x` sampled at `dt`, the overlapping Allan deviation
`sigma(tau)` decomposes the noise by averaging time:

* the **-1/2 slope** is white noise. Its coefficient read at tau = 1 s is the angle random walk
  (gyro) or velocity random walk (accel). `sigma(1 s)` in rad/s is numerically the same number as
  the rad/s/sqrt(Hz) PSD amplitude the filter wants, which is why `FilterConfig` can take it
  directly.
* the **flat minimum** is the flicker floor. IEEE Std 952 gives
  `sigma_min = B * sqrt(2 ln2 / pi) = 0.664 * B`, so the bias instability is
  **`B = sigma_min / 0.664`** -- a division, not a multiplication. Reading it the other way
  under-states B by 2.3x. See D-046.
* the **+1/2 slope** is rate random walk, `sigma(tau) = K sqrt(tau/3)`. Resolving it needs a
  record far longer than anything IO-VNBD's `S-` stream contains; see `MAX_TAU_FRACTION` and
  docs/ERROR_BUDGET.md section 9.

Background: docs/ERROR_BUDGET.md section 9, docs/DATASETS.md section 1.4.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from core.reference.inekf import FilterConfig
from eval.loaders.io_vnbd import SAMPLE_RATE_HZ, Sequence, load_sequence
from idr.stamp import seed_everything

#: Canonical accelerometer axes, in the order this module reports them. Units m/s^2.
ACCEL_AXES: tuple[str, str, str] = ("accel_x", "accel_y", "accel_z")

#: Canonical gyro axes. Units rad/s.
#:
#: AndroSensor's "Yaw/Pitch/Roll" labels are its names for device x/y/z -- the uncategorised folder
#: ships the identical columns spelled "GYROSCOPE X/Y/Z" (see eval/loaders/columns.py). So
#: "gyro_yaw" is the device x axis and is *not* the vertical axis of a phone lying flat.
GYRO_AXES: tuple[str, str, str] = ("gyro_yaw", "gyro_pitch", "gyro_roll")

#: Longest tau to trust, as a fraction of the segment. The overlapping estimator returns a value
#: for any tau < T/2, but with fewer than ~10 independent clusters the estimate is dominated by its
#: own sampling error and the curve turns up in a way that mimics rate random walk. T/10 is the
#: usual working limit and is what we report to.
MAX_TAU_FRACTION = 0.1

#: A stationary segment is quiet enough to characterise *sensor* noise on only if it sits this
#: far inside the ZUPT detector's thresholds. The detector answers "is the vehicle stopped", and a
#: car idling with someone shifting in the seat passes it comfortably -- IO-VNBD's S-A6 segments
#: carry 20-30x the mechanical energy of its S-T ones and return a "gyro ARW" 6x larger. That
#: number is real, but it measures the cabin, not the gyroscope, and an Allan curve computed over
#: it is not estimating the quantity its axis labels claim. Vibration belongs in the error budget
#: as an explicit inflation term, not smuggled into the ARW.
QUIET_MARGIN = 10.0

#: How far the fitted log-log slope may sit from -1/2 before the white-noise band is declared
#: contaminated and the random-walk coefficient read from it is refused. Not cosmetic: on segment
#: S-T2 the accel_x curve carries a low-frequency bump that flattens tau = 0.6-1.4 s to a plateau,
#: and reading an "ARW" off it returns a number 4x the other two axes that is not an ARW at all.
SLOPE_TOLERANCE = 0.15

#: IEEE Std 952 flicker-floor coefficient: sigma_min = BIAS_INSTABILITY_COEFF * B.
BIAS_INSTABILITY_COEFF = math.sqrt(2.0 * math.log(2.0) / math.pi)  # 0.6643

# Unit conversions, all one-way from SI into the units the error budget is written in.
RAD_PER_S_SQRT_S_TO_DEG_PER_SQRT_HR = math.degrees(1.0) * 60.0  # rad/sqrt(s) -> deg/sqrt(hr)
RAD_PER_S_TO_DEG_PER_HR = math.degrees(1.0) * 3600.0
MPS2_TO_MILLI_G = 1000.0 / 9.80665
MPS2_SQRT_S_TO_MPS_SQRT_HR = 60.0


# --------------------------------------------------------------------------------------------
# Stationary segments
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StationarySegment:
    """One continuous, uniformly-sampled, stationary stretch of an `S-` sequence.

    `start`/`stop` index the sequence's own IMU frame so a reader can go back to the raw rows.
    """

    sequence: str
    path: str
    start: int
    stop: int  # exclusive
    n_samples: int
    dt_s: float
    duration_s: float
    max_gap_s: float
    duplicate_dt_fraction: float
    accel_var_mean: float
    gyro_norm_mean: float
    is_quiet: bool

    @property
    def max_tau_s(self) -> float:
        """Longest averaging time this segment supports at MAX_TAU_FRACTION."""
        return self.duration_s * MAX_TAU_FRACTION


def imu_arrays(seq: Sequence) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pull `(t_s, accel, gyro)` out of a loaded sequence as float arrays.

    Rows with a non-finite timestamp or sample are dropped rather than interpolated: a synthesised
    IMU sample inside an Allan run is indistinguishable from a real one and biases sigma(tau)
    downward at exactly the taus we care about.
    """
    imu = seq.imu
    missing = [c for c in (*ACCEL_AXES, *GYRO_AXES, "time_since_start_ms") if c not in imu.columns]
    if missing:
        raise ValueError(f"{seq.name}: sequence is missing {missing}")

    t = pd.to_numeric(imu["time_since_start_ms"], errors="coerce").to_numpy(dtype=float) / 1000.0
    accel = imu[list(ACCEL_AXES)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    gyro = imu[list(GYRO_AXES)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)

    keep = np.isfinite(t) & np.isfinite(accel).all(axis=1) & np.isfinite(gyro).all(axis=1)
    return t[keep], accel[keep], gyro[keep]


def _rolling_mean(x: np.ndarray, window: int) -> np.ndarray:
    """Mean over every length-`window` slice, via cumulative sums. Shape (n - window + 1, ...)."""
    csum = np.cumsum(np.concatenate([np.zeros((1, *x.shape[1:])), x], axis=0), axis=0)
    return (csum[window:] - csum[:-window]) / window


def _true_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Half-open [start, stop) index pairs of every run of True."""
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    return list(zip(edges[0::2], edges[1::2], strict=True))


def find_stationary_segments(
    seq: Sequence,
    *,
    cfg: FilterConfig | None = None,
    min_duration_s: float = 120.0,
    window_s: float = 10.0,
    max_gap_s: float = 0.5,
    max_duplicate_dt_fraction: float = 0.02,
) -> list[StationarySegment]:
    """Find stretches long and clean enough to compute an Allan curve on.

    Stationarity uses the filter's own ZUPT criteria (`core.reference.inekf.is_stationary`:
    mean per-axis accelerometer variance *and* mean gyro magnitude, both under
    `FilterConfig`'s thresholds), vectorised over a sliding window. Sharing the definition means
    the segments we characterise noise on are exactly the segments the filter will ZUPT on --
    tuning Q on a stricter notion of "stopped" than the runtime one would measure a sensor the
    filter never sees.

    Two sampling checks on top, both learned from the data rather than assumed. IO-VNBD's `S-`
    files are mostly a clean 10 Hz, but at least one (`S-I`) contains a 285 s recorder pause and a
    burst-mode section whose timestamps repeat at ~1 ms. Allan variance assumes a uniform grid, so
    a run is rejected if it holds a gap over `max_gap_s` or more than `max_duplicate_dt_fraction`
    non-advancing timestamps.
    """
    cfg = cfg or FilterConfig()
    t, accel, gyro = imu_arrays(seq)
    window = max(2, int(round(window_s * SAMPLE_RATE_HZ)))
    if len(t) < 2 * window:
        return []

    # mean over axes of the per-axis variance, matching is_stationary()
    accel_var = (_rolling_mean(accel**2, window) - _rolling_mean(accel, window) ** 2).mean(axis=1)
    gyro_norm = _rolling_mean(np.linalg.norm(gyro, axis=1)[:, None], window).ravel()
    stationary = (accel_var < cfg.zupt_accel_var_thresh) & (
        gyro_norm < cfg.zupt_gyro_norm_thresh
    )

    segments: list[StationarySegment] = []
    for run_start, run_stop in _true_runs(stationary):
        start, stop = int(run_start), int(run_stop + window - 1)
        dt_all = np.diff(t[start:stop])
        if dt_all.size < 2:
            continue
        dt_s = float(np.median(dt_all))
        duration_s = float(t[stop - 1] - t[start])
        if duration_s < min_duration_s:
            continue
        max_gap = float(dt_all.max())
        duplicate_fraction = float((dt_all <= 0.0).mean())
        if max_gap > max_gap_s or duplicate_fraction > max_duplicate_dt_fraction:
            continue

        segments.append(
            StationarySegment(
                sequence=seq.name,
                path=str(getattr(seq, "source_path", "")),
                start=start,
                stop=stop,
                n_samples=stop - start,
                dt_s=dt_s,
                duration_s=duration_s,
                max_gap_s=max_gap,
                duplicate_dt_fraction=duplicate_fraction,
                accel_var_mean=(accel_var_mean := float(accel_var[run_start:run_stop].mean())),
                gyro_norm_mean=(gyro_norm_mean := float(gyro_norm[run_start:run_stop].mean())),
                is_quiet=bool(
                    accel_var_mean * QUIET_MARGIN < cfg.zupt_accel_var_thresh
                    and gyro_norm_mean * QUIET_MARGIN < cfg.zupt_gyro_norm_thresh
                ),
            )
        )
    return segments


# --------------------------------------------------------------------------------------------
# The estimator
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AllanCurve:
    """An overlapping Allan deviation curve for one axis of one segment."""

    segment: str
    axis: str
    unit: str
    tau_s: np.ndarray
    adev: np.ndarray
    n_clusters: np.ndarray
    rel_error: np.ndarray

    def at(self, tau_s: float) -> float:
        """Log-log interpolated deviation at an arbitrary tau."""
        return float(
            np.exp(np.interp(np.log(tau_s), np.log(self.tau_s), np.log(self.adev)))
        )


def octave_taus(n_samples: int, dt_s: float, *, points_per_decade: int = 12) -> np.ndarray:
    """Log-spaced cluster times from `dt` up to `MAX_TAU_FRACTION` of the record.

    Returns the realisable taus -- each is an integer multiple of `dt`, deduplicated -- so that
    nothing downstream has to wonder whether a plotted tau was rounded.
    """
    total_s = n_samples * dt_s
    max_m = int(total_s * MAX_TAU_FRACTION / dt_s)
    if max_m < 1:
        return np.empty(0)
    decades = math.log10(max(max_m, 2))
    count = max(2, int(round(decades * points_per_decade)))
    m = np.unique(np.round(np.logspace(0, math.log10(max_m), count)).astype(int))
    return m[m >= 1] * dt_s


def overlapping_allan_deviation(
    x: np.ndarray,
    dt_s: float,
    *,
    axis: str = "",
    unit: str = "",
    segment: str = "",
    taus: np.ndarray | None = None,
) -> AllanCurve:
    """Overlapping Allan deviation of a rate signal.

    `sigma^2(tau) = 1 / (2 tau^2 (N - 2m + 1)) * sum_k (theta_{k+2m} - 2 theta_{k+m} + theta_k)^2`

    with `theta` the cumulative integral of `x`. Overlapping rather than non-overlapping because it
    reuses every sample at every cluster size, which roughly halves the confidence interval at the
    long taus -- and long tau is precisely where a 7-minute segment has the least to give.

    A constant offset (gravity on the accelerometer's vertical axis) is annihilated by the second
    difference, so nothing needs removing first.
    """
    x = np.asarray(x, dtype=float).ravel()
    n = x.size
    if n < 4:
        raise ValueError(f"need at least 4 samples, got {n}")
    if taus is None:
        taus = octave_taus(n, dt_s)

    theta = np.concatenate(([0.0], np.cumsum(x))) * dt_s

    tau_out, adev, clusters, rel = [], [], [], []
    for tau in np.atleast_1d(taus):
        m = int(round(float(tau) / dt_s))
        if m < 1 or 2 * m >= n:
            continue
        d = theta[2 * m :] - 2.0 * theta[m : -m] + theta[: -2 * m]
        n_terms = d.size
        tau_actual = m * dt_s
        variance = float(d @ d) / (2.0 * tau_actual**2 * n_terms)
        # Independent clusters, not overlapping terms: the confidence follows the former.
        independent = max(n / m - 1.0, 1.0)
        tau_out.append(tau_actual)
        adev.append(math.sqrt(variance))
        clusters.append(independent)
        rel.append(1.0 / math.sqrt(2.0 * independent))

    return AllanCurve(
        segment=segment,
        axis=axis,
        unit=unit,
        tau_s=np.array(tau_out),
        adev=np.array(adev),
        n_clusters=np.array(clusters),
        rel_error=np.array(rel),
    )


# --------------------------------------------------------------------------------------------
# Reading coefficients off the curve
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NoiseCoefficients:
    """What one Allan curve says about one axis."""

    segment: str
    axis: str
    unit: str
    random_walk: float  # sigma at tau = 1 s, unit * sqrt(s)
    random_walk_slope: float  # fitted log-log slope; -0.5 if the fit region is really white
    random_walk_is_white: bool  # False => random_walk is not an ARW/VRW, whatever its units
    bias_instability: float  # unit
    bias_instability_tau_s: float
    bias_instability_at_edge: bool
    tau_max_s: float
    rel_error_at_min: float


def _loglog_slope(tau: np.ndarray, adev: np.ndarray) -> float:
    return float(np.polyfit(np.log(tau), np.log(adev), 1)[0])


def random_walk_coefficient(
    curve: AllanCurve, *, fit_lo_s: float = 0.2, fit_hi_s: float = 2.0
) -> tuple[float, float]:
    """Read the white-noise coefficient at tau = 1 s, and report the slope it was read from.

    In the white-noise region `sigma(tau) = N / sqrt(tau)`, so `N = sigma(tau) sqrt(tau)` is
    constant there and `N = sigma(1 s)`. Averaging `sigma sqrt(tau)` in log space across the fit
    band rather than reading the single tau = 1 s point uses the whole region and is not hostage to
    one noisy estimate.

    The returned slope is the check: if it is not close to -0.5 the band is not white noise and the
    coefficient is not an ARW, whatever the units say.
    """
    band = (curve.tau_s >= fit_lo_s) & (curve.tau_s <= fit_hi_s)
    if band.sum() < 2:
        band = curve.tau_s <= max(fit_hi_s, curve.tau_s[min(3, curve.tau_s.size - 1)])
    tau, adev = curve.tau_s[band], curve.adev[band]
    coefficient = float(np.exp(np.mean(np.log(adev * np.sqrt(tau)))))
    return coefficient, _loglog_slope(tau, adev)


def bias_instability(curve: AllanCurve) -> tuple[float, float, bool, float]:
    """Bias instability `B` from the flat minimum: `B = sigma_min / 0.664` (IEEE Std 952).

    Returns `(B, tau_at_minimum, minimum_is_at_the_edge, rel_error_there)`. The edge flag matters:
    if the smallest sigma sits at the last tau the record supports, the curve has not been observed
    to turn back up, so what has been measured is an upper bound on where the floor is -- not the
    floor. Reporting it as a measurement would be reporting the length of the recording.
    """
    k = int(np.argmin(curve.adev))
    at_edge = k >= curve.adev.size - 1
    return (
        float(curve.adev[k] / BIAS_INSTABILITY_COEFF),
        float(curve.tau_s[k]),
        bool(at_edge),
        float(curve.rel_error[k]),
    )


def coefficients(curve: AllanCurve, *, segment: str = "") -> NoiseCoefficients:
    rw, slope = random_walk_coefficient(curve)
    bi, tau_bi, at_edge, rel = bias_instability(curve)
    return NoiseCoefficients(
        segment=segment,
        axis=curve.axis,
        unit=curve.unit,
        random_walk=rw,
        random_walk_slope=slope,
        random_walk_is_white=bool(abs(slope + 0.5) <= SLOPE_TOLERANCE),
        bias_instability=bi,
        bias_instability_tau_s=tau_bi,
        bias_instability_at_edge=at_edge,
        tau_max_s=float(curve.tau_s[-1]),
        rel_error_at_min=rel,
    )


def gauss_markov_bias_driving_noise(
    bias_instability_value: float, tau_correlation_s: float
) -> float:
    """Process-noise amplitude for a bias modelled as first-order Gauss-Markov.

    A record of a few hundred seconds cannot resolve the +1/2 rate-random-walk slope, so
    `FilterConfig.gyro_bias_rw` / `accel_bias_rw` cannot be *measured* here. They are instead
    derived from the two things that were measured: a bias whose steady-state spread is `B` and
    whose correlation time is the tau of the Allan minimum is driven by white noise of amplitude
    `B sqrt(2 / tau_c)`, which is the standard first-order Gauss-Markov result.

    This is a modelling choice, not a measurement, and it is labelled as such everywhere it
    surfaces. It is also the conservative direction: it puts more noise into the bias states than a
    fitted rate random walk would at these taus.
    """
    if tau_correlation_s <= 0:
        raise ValueError("correlation time must be positive")
    return float(bias_instability_value * math.sqrt(2.0 / tau_correlation_s))


# --------------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------------


@dataclass
class AllanReport:
    """Everything one run of this module produced, ready to stamp and write."""

    segments: list[StationarySegment] = field(default_factory=list)
    curves: list[AllanCurve] = field(default_factory=list)
    coefficients: list[NoiseCoefficients] = field(default_factory=list)

    def select(
        self, axes: tuple[str, ...], *, white_only: bool = False
    ) -> list[NoiseCoefficients]:
        """Per-axis, per-segment coefficients for one sensor, optionally white-band fits only."""
        return [
            c
            for c in self.coefficients
            if c.axis in axes and (c.random_walk_is_white or not white_only)
        ]

    def worst(self, axes: tuple[str, ...], attribute: str, *, white_only: bool = False) -> float:
        """Largest value of `attribute` over every axis of every segment.

        `FilterConfig` carries one scalar per quantity while the sensor has three axes and the
        record has several segments, so a choice is forced. The worst is the safe one: an
        undersized Q makes the filter over-trust its own propagation and reject good measurements
        at the chi-squared gate, and that failure presents as a sensor fault rather than as a
        tuning error (D-031).

        Taking the max across *segments* as well as axes also means the seed is not hostage to
        whichever segment happened to be longest -- IO-VNBD's stationary stretches come from
        different vehicles, devices and days, and the spread between them is itself a result.
        """
        chosen = self.select(axes, white_only=white_only)
        if not chosen:
            raise ValueError(f"no usable coefficients for {axes}")
        return max(getattr(c, attribute) for c in chosen)

    def spread(
        self, axes: tuple[str, ...], attribute: str, *, white_only: bool = False
    ) -> tuple[float, float]:
        """(min, max) of `attribute`, for reporting the range rather than a false point estimate."""
        chosen = self.select(axes, white_only=white_only)
        if not chosen:
            raise ValueError(f"no usable coefficients for {axes}")
        values = [getattr(c, attribute) for c in chosen]
        return min(values), max(values)


def analyse_segment(
    seq: Sequence, segment: StationarySegment
) -> tuple[list[AllanCurve], list[NoiseCoefficients]]:
    """Allan curves and coefficients for all six axes of one stationary segment."""
    _, accel, gyro = imu_arrays(seq)
    label = f"{segment.sequence}[{segment.start}:{segment.stop}]"
    curves: list[AllanCurve] = []
    for i, axis in enumerate(GYRO_AXES):
        curves.append(
            overlapping_allan_deviation(
                gyro[segment.start : segment.stop, i],
                segment.dt_s,
                axis=axis,
                unit="rad/s",
                segment=label,
            )
        )
    for i, axis in enumerate(ACCEL_AXES):
        curves.append(
            overlapping_allan_deviation(
                accel[segment.start : segment.stop, i],
                segment.dt_s,
                axis=axis,
                unit="m/s^2",
                segment=label,
            )
        )
    return curves, [coefficients(c, segment=label) for c in curves]


def write_report(report: AllanReport, out_dir: Path, stamp) -> None:
    """Write the curve, the coefficients, the segment inventory and the provenance stamp.

    CSV rather than a plot: matplotlib is not installed on the primary dev box, and a table that
    exists beats a figure that does not. The figure is a one-liner over `allan_curve.csv` whenever
    the plotting dependency lands.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    caption = stamp.caption()

    with (out_dir / "allan_segments.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# {caption}"])
        w.writerow([f.name for f in StationarySegment.__dataclass_fields__.values()])
        for s in report.segments:
            w.writerow(list(asdict(s).values()))

    with (out_dir / "allan_curve.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# {caption}"])
        w.writerow(
            ["segment", "axis", "unit", "tau_s", "adev", "independent_clusters", "rel_error"]
        )
        for c in report.curves:
            for tau, ad, nc, re_ in zip(
                c.tau_s, c.adev, c.n_clusters, c.rel_error, strict=True
            ):
                w.writerow(
                    [
                        c.segment, c.axis, c.unit,
                        f"{tau:.6g}", f"{ad:.6g}", f"{nc:.6g}", f"{re_:.4g}",
                    ]
                )

    with (out_dir / "allan_coefficients.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# {caption}"])
        w.writerow([f.name for f in NoiseCoefficients.__dataclass_fields__.values()])
        for c in report.coefficients:
            w.writerow(list(asdict(c).values()))

    stamp.to_json(out_dir / "allan_stamp.json")


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def _summarise(report: AllanReport) -> dict[str, float]:
    """Collapse the per-axis, per-segment table into the four scalars `FilterConfig` takes.

    Random walk uses white-band fits only -- a coefficient read off a contaminated slope is not an
    ARW and must not become one by being the largest number in the column. Bias instability uses
    every fit, because its estimator does not depend on the fit band.
    """
    gyro_arw = report.worst(GYRO_AXES, "random_walk", white_only=True)
    accel_vrw = report.worst(ACCEL_AXES, "random_walk", white_only=True)
    gyro_bi = report.worst(GYRO_AXES, "bias_instability")
    accel_bi = report.worst(ACCEL_AXES, "bias_instability")
    # Shortest observed correlation time drives the most process noise, so it is the safe pick.
    gyro_tau = min(c.bias_instability_tau_s for c in report.select(GYRO_AXES))
    accel_tau = min(c.bias_instability_tau_s for c in report.select(ACCEL_AXES))
    arw_lo, arw_hi = report.spread(GYRO_AXES, "random_walk", white_only=True)
    vrw_lo, vrw_hi = report.spread(ACCEL_AXES, "random_walk", white_only=True)
    return {
        "gyro_arw_rad_s_sqrt_hz": gyro_arw,
        "gyro_arw_deg_sqrt_hr": gyro_arw * RAD_PER_S_SQRT_S_TO_DEG_PER_SQRT_HR,
        "gyro_arw_deg_sqrt_hr_min": arw_lo * RAD_PER_S_SQRT_S_TO_DEG_PER_SQRT_HR,
        "gyro_arw_deg_sqrt_hr_max": arw_hi * RAD_PER_S_SQRT_S_TO_DEG_PER_SQRT_HR,
        "accel_vrw_mps2_sqrt_hz": accel_vrw,
        "accel_vrw_mps_sqrt_hr": accel_vrw * MPS2_SQRT_S_TO_MPS_SQRT_HR,
        "accel_vrw_mps_sqrt_hr_min": vrw_lo * MPS2_SQRT_S_TO_MPS_SQRT_HR,
        "accel_vrw_mps_sqrt_hr_max": vrw_hi * MPS2_SQRT_S_TO_MPS_SQRT_HR,
        "gyro_bias_instability_rad_s": gyro_bi,
        "gyro_bias_instability_deg_hr": gyro_bi * RAD_PER_S_TO_DEG_PER_HR,
        "accel_bias_instability_mps2": accel_bi,
        "accel_bias_instability_mg": accel_bi * MPS2_TO_MILLI_G,
        "gyro_bias_rw_rad_s2_sqrt_hz": gauss_markov_bias_driving_noise(gyro_bi, gyro_tau),
        "accel_bias_rw_mps3_sqrt_hz": gauss_markov_bias_driving_noise(accel_bi, accel_tau),
        "gyro_bias_tau_s": gyro_tau,
        "accel_bias_tau_s": accel_tau,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths", nargs="*", help="'S-' CSV files to search for stationary segments"
    )
    parser.add_argument(
        "--paths-from",
        type=Path,
        help="file of newline-separated CSV paths. IO-VNBD's directory names contain spaces, "
        "which makes a shell-globbed argument list its own source of bugs.",
    )
    parser.add_argument("--out-dir", default="eval/figures", type=Path)
    parser.add_argument("--seed", type=int, default=26168)
    parser.add_argument("--min-duration-s", type=float, default=120.0)
    parser.add_argument(
        "--include-noisy",
        action="store_true",
        help="also compute curves for segments that fail the QUIET_MARGIN gate. For comparison "
        "only -- their coefficients describe the cabin, not the sensor.",
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="list the stationary segments found and stop, without computing curves",
    )
    args = parser.parse_args(argv)

    stamp = seed_everything(args.seed)
    report = AllanReport()
    loaded: dict[str, Sequence] = {}

    paths = list(args.paths)
    if args.paths_from:
        paths += [
            line.strip()
            for line in args.paths_from.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if not paths:
        parser.error("give at least one path, or --paths-from")

    for raw in paths:
        path = Path(raw)
        seq = load_sequence(path)
        loaded[seq.name] = seq
        found = find_stationary_segments(seq, min_duration_s=args.min_duration_s)
        for s in found:
            report.segments.append(
                StationarySegment(**{**asdict(s), "path": str(path).replace("\\", "/")})
            )

    report.segments.sort(key=lambda s: -s.duration_s)
    print(f"{stamp.caption()}\n")
    print(
        f"{'sequence':10s} {'start':>8s} {'stop':>8s} {'dur_s':>8s} {'dt_s':>6s} "
        f"{'tau_max_s':>9s} {'accel_var':>10s} {'gyro_norm':>10s}  quiet"
    )
    for s in report.segments:
        print(
            f"{s.sequence:10s} {s.start:8d} {s.stop:8d} {s.duration_s:8.1f} "
            f"{s.dt_s:6.3f} {s.max_tau_s:9.1f} {s.accel_var_mean:10.6f} "
            f"{s.gyro_norm_mean:10.6f}  {'yes' if s.is_quiet else 'NO'}"
        )
    if args.inventory_only or not report.segments:
        return 0 if report.segments else 1

    analysed = [s for s in report.segments if s.is_quiet or args.include_noisy]
    if not analysed:
        print("\nno segment is quiet enough to characterise sensor noise on")
        return 1

    for segment in analysed:
        curves, coeffs = analyse_segment(loaded[segment.sequence], segment)
        report.curves += curves
        report.coefficients += coeffs

    print(
        f"\n{'segment':22s} {'axis':12s} {'N(1s)':>11s} {'slope':>7s} {'B':>11s} {'tau_B':>7s}"
    )
    for c in report.coefficients:
        flags = "" if c.random_walk_is_white else "  not-white"
        flags += "  B-at-edge" if c.bias_instability_at_edge else ""
        print(
            f"{c.segment:22s} {c.axis:12s} {c.random_walk:11.4g} {c.random_walk_slope:+7.2f} "
            f"{c.bias_instability:11.4g} {c.bias_instability_tau_s:7.1f}{flags}"
        )

    summary = _summarise(report)
    print("\nFilterConfig seeds (worst axis over all segments):")
    for k, v in summary.items():
        print(f"  {k:32s} {v:.6g}")

    write_report(report, args.out_dir, stamp)
    (args.out_dir / "allan_summary.json").write_text(
        json.dumps(
            {
                "stamp": asdict(stamp),
                "segments": [asdict(s) for s in report.segments],
                "summary": summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {args.out_dir}/allan_{{segments,curve,coefficients}}.csv + summary/stamp json")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
