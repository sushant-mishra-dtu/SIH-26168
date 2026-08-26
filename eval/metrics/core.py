"""The four metrics. This module owns every number in the submission.

Read docs/EVALUATION.md section 4 before changing anything here. After the Gate 0 freeze, a change
to this file requires a DECISION_LOG row naming which results it invalidated.

On CTE/CRSE naming: these are Onyekpe's *Cumulative True Error* and *Cumulative Root Square Error*.
They are NOT cross-track error and NOT ATE. The task brief mislabels them and so does most
secondary writing about this dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from idr.geo import wrap_to_pi


class CrseConvention(str, Enum):
    """Unresolved definitional ambiguity -- see docs/EVALUATION.md section 4.2.

    Our source for the CTE/CRSE definitions is a secondary summary, not the paper's equations.
    "Cumulative Root Square Error" admits two readings:

      SUM_SQUARES  sqrt(sum(e_i^2))    -- 'cumulative', grows with outage length
      RMS          sqrt(mean(e_i^2))   -- 'root mean square', length-independent

    Consistency check against WhONet's published 180 s physics baseline (CTE 2.90 m,
    CRSE 13.67 m, ~180 one-second epochs): under SUM_SQUARES a typical per-epoch error is
    13.67/sqrt(180) ~ 1.0 m, which sits sensibly beside a signed sum of 2.90 m after cancellation.
    Under RMS every epoch would average 13.67 m of error while the signed sum stayed at 2.90 m,
    which requires implausible cancellation. SUM_SQUARES is therefore the default.

    This is a reasoned default, not a verified one. Seat D pins it against the paper's equation
    numbers before Gate 0; flipping this enum is then a one-line change rather than a rewrite.
    """

    SUM_SQUARES = "sum_squares"
    RMS = "rms"


#: Default until seat D confirms against the paper. Tracked as the Gate 0 blocker.
CRSE_CONVENTION = CrseConvention.SUM_SQUARES


@dataclass(frozen=True)
class OutageMetrics:
    """Result for a single outage sequence. Every field is reported; none is optional."""

    cte_m: float
    crse_m: float
    drift_pct: float
    yaw_rmse_rad: float
    yaw_max_rad: float
    distance_m: float
    duration_s: float
    n_epochs: int

    def as_row(self) -> dict[str, float]:
        return {
            "cte_m": self.cte_m,
            "crse_m": self.crse_m,
            "drift_pct": self.drift_pct,
            "yaw_rmse_deg": np.degrees(self.yaw_rmse_rad),
            "yaw_max_deg": np.degrees(self.yaw_max_rad),
            "distance_m": self.distance_m,
            "duration_s": self.duration_s,
            "n_epochs": self.n_epochs,
        }


def _validate(estimated: np.ndarray, truth: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    est = np.asarray(estimated, dtype=float)
    tru = np.asarray(truth, dtype=float)
    if est.shape != tru.shape:
        raise ValueError(f"shape mismatch: estimated {est.shape} vs truth {tru.shape}")
    if est.ndim != 2 or est.shape[1] != 2:
        raise ValueError(f"expected (n, 2) NED arrays, got {est.shape}")
    if est.shape[0] < 1:
        raise ValueError("empty sequence")
    if not np.isfinite(est).all() or not np.isfinite(tru).all():
        raise ValueError(
            "non-finite values in trajectory -- fix the filter, do not filter the NaNs"
        )
    return est, tru


def per_epoch_errors(estimated: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Signed per-epoch displacement error in metres, one value per 1 s prediction epoch.

    Both inputs are per-epoch *displacements* in NED (n, 2), not absolute positions. The sign is
    the projection onto the true direction of travel: positive means we over-predicted the
    distance covered, negative means we fell short. Sign is what lets CTE expose a systematic bias
    that an RMS would hide.
    """
    est, tru = _validate(estimated, truth)
    norms = np.linalg.norm(tru, axis=1)
    # Where the vehicle did not move, there is no direction to project onto; fall back to the
    # error magnitude, which is unsigned but correct in size.
    with np.errstate(invalid="ignore", divide="ignore"):
        safe = np.where(norms[:, None] > 0, norms[:, None], 1.0)
        unit = np.where(norms[:, None] > 1e-9, tru / safe, 0.0)
    delta = est - tru
    signed = np.einsum("ij,ij->i", delta, unit)
    stationary = norms <= 1e-9
    signed[stationary] = np.linalg.norm(delta[stationary], axis=1)
    return signed


def cte(estimated: np.ndarray, truth: np.ndarray) -> float:
    """Cumulative True Error: the *signed* sum of per-epoch errors, in metres.

    Signed on purpose. A speed head that consistently under-predicts by 2% shows up here as a
    large negative number, while CRSE would report the same magnitude as an equally-sized positive
    one and hide the bias.
    """
    return float(np.sum(per_epoch_errors(estimated, truth)))


def crse(
    estimated: np.ndarray, truth: np.ndarray, *, convention: CrseConvention | None = None
) -> float:
    """Cumulative Root Square Error, in metres. See CrseConvention for the open ambiguity."""
    conv = convention or CRSE_CONVENTION
    errors = per_epoch_errors(estimated, truth)
    if conv is CrseConvention.SUM_SQUARES:
        return float(np.sqrt(np.sum(errors**2)))
    return float(np.sqrt(np.mean(errors**2)))


def drift_percent(final_error_m: float, distance_m: float) -> float:
    """Final position error as a percentage of ground-truth distance travelled.

    **This is the number PS 26168 grades. Under 10%.**

    Note that no paper in this line reports it -- Onyekpe and WhONet report CTE/CRSE only -- so
    this is computed by us and must be defined unambiguously in the write-up.
    """
    if distance_m <= 0:
        raise ValueError(
            f"distance travelled must be positive, got {distance_m}. A zero-distance outage has "
            "no meaningful drift percentage and must be excluded from the sweep, not divided by."
        )
    return float(100.0 * final_error_m / distance_m)


def yaw_error(estimated_yaw: np.ndarray, truth_yaw: np.ndarray) -> tuple[float, float]:
    """(RMSE, max absolute) yaw error in radians, wrapped to (-pi, pi].

    Always reported alongside position error, never instead of it. Yaw is the dominant error term
    against the 10% benchmark -- see docs/ERROR_BUDGET.md section 3 -- and a run that reports
    position without yaw cannot tell you *why* it drifted.
    """
    est = np.asarray(estimated_yaw, dtype=float).ravel()
    tru = np.asarray(truth_yaw, dtype=float).ravel()
    if est.shape != tru.shape:
        raise ValueError(f"yaw shape mismatch: {est.shape} vs {tru.shape}")
    if est.size == 0:
        raise ValueError("empty yaw sequence")
    err = wrap_to_pi(est - tru)
    return float(np.sqrt(np.mean(err**2))), float(np.max(np.abs(err)))


def evaluate_outage(
    est_disp: np.ndarray,
    true_disp: np.ndarray,
    est_yaw: np.ndarray,
    true_yaw: np.ndarray,
    distance_m: float,
    duration_s: float,
) -> OutageMetrics:
    """Full metric set for one outage sequence.

    ``est_disp`` / ``true_disp`` are per-epoch NED displacements, shape (n, 2).
    ``distance_m`` is the Vincenty ground-truth path length over the outage.
    """
    est, tru = _validate(est_disp, true_disp)
    final_error = float(np.linalg.norm(est.sum(axis=0) - tru.sum(axis=0)))
    yaw_rmse, yaw_max = yaw_error(est_yaw, true_yaw)
    return OutageMetrics(
        cte_m=cte(est, tru),
        crse_m=crse(est, tru),
        drift_pct=drift_percent(final_error, distance_m),
        yaw_rmse_rad=yaw_rmse,
        yaw_max_rad=yaw_max,
        distance_m=distance_m,
        duration_s=duration_s,
        n_epochs=int(est.shape[0]),
    )


def summarise(results: list[OutageMetrics]) -> dict[str, float]:
    """Aggregate across sequences.

    Reports the **median and 95th percentile** of drift, not just the mean. The mean hides the
    tail and the tail is what a judge finds -- see docs/EVALUATION.md section 4.3.
    """
    if not results:
        raise ValueError("no results to summarise")
    drift = np.array([r.drift_pct for r in results])
    return {
        "n_sequences": len(results),
        "drift_pct_median": float(np.median(drift)),
        "drift_pct_p95": float(np.percentile(drift, 95)),
        "drift_pct_max": float(np.max(drift)),
        "frac_under_10pct": float(np.mean(drift < 10.0)),
        "cte_m_mean": float(np.mean([r.cte_m for r in results])),
        "crse_m_mean": float(np.mean([r.crse_m for r in results])),
        "yaw_rmse_deg_mean": float(np.degrees(np.mean([r.yaw_rmse_rad for r in results]))),
        "yaw_max_deg": float(np.degrees(np.max([r.yaw_max_rad for r in results]))),
        "total_distance_m": float(np.sum([r.distance_m for r in results])),
    }
