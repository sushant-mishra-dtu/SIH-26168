"""Metric unit tests, each against a hand-computed case.

Every number in the submission comes out of these functions. A metric that is merely
'probably right' is worse than no metric, because it produces confident wrong conclusions.
"""

from __future__ import annotations

import numpy as np
import pytest

from eval.metrics.core import (
    CrseConvention,
    crse,
    cte,
    drift_percent,
    evaluate_outage,
    per_epoch_errors,
    summarise,
    yaw_error,
)


def test_perfect_estimate_has_zero_error():
    truth = np.array([[10.0, 0.0], [10.0, 0.0], [10.0, 0.0]])
    assert cte(truth, truth) == pytest.approx(0.0)
    assert crse(truth, truth) == pytest.approx(0.0)


def test_cte_is_signed_and_exposes_systematic_bias():
    """Three epochs, each under-predicted by 1 m along-track.

    Hand-computed: per-epoch error = -1 m, CTE = -3 m. A systematic under-prediction must show as
    a negative number -- this is the entire reason CTE is signed rather than absolute.
    """
    truth = np.array([[10.0, 0.0], [10.0, 0.0], [10.0, 0.0]])
    est = np.array([[9.0, 0.0], [9.0, 0.0], [9.0, 0.0]])
    assert per_epoch_errors(est, truth) == pytest.approx([-1.0, -1.0, -1.0])
    assert cte(est, truth) == pytest.approx(-3.0)


def test_cte_cancels_where_crse_does_not():
    """The pair exists precisely because they disagree: +2 and -2 cancel in CTE but not in CRSE."""
    truth = np.array([[10.0, 0.0], [10.0, 0.0]])
    est = np.array([[12.0, 0.0], [8.0, 0.0]])
    assert cte(est, truth) == pytest.approx(0.0)
    assert crse(est, truth, convention=CrseConvention.SUM_SQUARES) == pytest.approx(np.sqrt(8.0))


def test_crse_conventions_differ_by_sqrt_n():
    """Documents the open ambiguity numerically -- see CrseConvention."""
    truth = np.tile([10.0, 0.0], (4, 1))
    est = np.tile([11.0, 0.0], (4, 1))
    total = crse(est, truth, convention=CrseConvention.SUM_SQUARES)
    mean = crse(est, truth, convention=CrseConvention.RMS)
    assert total == pytest.approx(2.0)  # sqrt(4 * 1^2)
    assert mean == pytest.approx(1.0)  # sqrt(mean(1^2))
    assert total == pytest.approx(mean * np.sqrt(4))


def test_drift_percent_hand_computed():
    """50 m of final error over a 1,000 m outage is 5%."""
    assert drift_percent(50.0, 1000.0) == pytest.approx(5.0)
    assert drift_percent(100.0, 1000.0) == pytest.approx(10.0)  # exactly at the PS 26168 limit


def test_drift_percent_rejects_zero_distance():
    """A stationary outage has no meaningful drift percentage. Excluding it is a decision;
    dividing by zero is a bug that produces inf and poisons the summary."""
    with pytest.raises(ValueError, match="must be positive"):
        drift_percent(5.0, 0.0)


def test_yaw_error_wraps_across_the_branch_cut():
    """An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26.

    Getting this wrong turns the single most important diagnostic in the project into noise.
    """
    truth = np.array([np.pi - 0.01])
    est = np.array([-np.pi + 0.01])
    rmse, mx = yaw_error(est, truth)
    assert rmse == pytest.approx(0.02, abs=1e-9)
    assert mx == pytest.approx(0.02, abs=1e-9)


def test_yaw_error_zero_when_identical():
    yaw = np.array([0.0, 1.0, -2.5, 3.0])
    assert yaw_error(yaw, yaw) == (pytest.approx(0.0), pytest.approx(0.0))


def test_evaluate_outage_end_to_end():
    """60 s outage, 10 m/s, perfect heading, 2% under-prediction of distance.

    Truth: 60 epochs x 10 m = 600 m travelled. Estimate: 9.8 m/epoch -> 588 m.
    Final error 12 m over 600 m = 2% drift.
    """
    n = 60
    truth = np.tile([10.0, 0.0], (n, 1))
    est = np.tile([9.8, 0.0], (n, 1))
    yaw = np.zeros(n)
    m = evaluate_outage(est, truth, yaw, yaw, distance_m=600.0, duration_s=60.0)
    assert m.drift_pct == pytest.approx(2.0)
    assert m.cte_m == pytest.approx(-12.0)
    assert m.yaw_rmse_rad == pytest.approx(0.0)
    assert m.n_epochs == 60


def test_shape_and_nan_guards():
    truth = np.tile([10.0, 0.0], (3, 1))
    with pytest.raises(ValueError, match="shape mismatch"):
        cte(np.tile([10.0, 0.0], (2, 1)), truth)
    with pytest.raises(ValueError, match="non-finite"):
        cte(np.array([[np.nan, 0.0], [1.0, 0.0], [1.0, 0.0]]), truth)


def test_summary_reports_tail_not_just_mean():
    """The mean hides the tail and the tail is what a judge finds."""
    n = 20
    truth = np.tile([10.0, 0.0], (n, 1))
    results = []
    for scale in (1.0, 1.0, 1.0, 1.0, 0.5):  # one bad sequence among four good
        est = np.tile([10.0 * scale, 0.0], (n, 1))
        yaw = np.zeros(n)
        results.append(evaluate_outage(est, truth, yaw, yaw, distance_m=200.0, duration_s=20.0))
    s = summarise(results)
    assert s["drift_pct_median"] == pytest.approx(0.0)
    assert s["drift_pct_max"] == pytest.approx(50.0)
    assert s["frac_under_10pct"] == pytest.approx(0.8)
