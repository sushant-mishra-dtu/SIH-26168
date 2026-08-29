"""Tests for the implemented parts of the reference filter: detectors and gating.

Propagation and the update family are Sprint 1. The gating conditions are tested now because they
are where a plausible-looking filter goes quietly wrong -- an ungated NHC through a slip produces
smooth, confident, incorrect output that no position plot reveals until it is compared to truth.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.reference.inekf import (
    ERROR_STATE_DIM,
    IDX_ATTITUDE,
    IDX_MOUNT,
    FilterConfig,
    InEKF,
    NavState,
    chi2_gate,
    detect_mount_disturbance,
    is_stationary,
    nhc_is_valid,
)

CFG = FilterConfig()
RNG = np.random.default_rng(0)


# ------------------------------------------------------------------------------------------
# State layout
# ------------------------------------------------------------------------------------------


def test_error_state_slices_tile_the_vector_without_gaps_or_overlap():
    """A mis-indexed error state corrupts the wrong block of the covariance, which shows up as a
    filter that 'almost works' -- the hardest failure mode to diagnose."""
    covered = np.zeros(ERROR_STATE_DIM, dtype=int)
    for sl in (IDX_ATTITUDE, slice(3, 6), slice(6, 9), slice(9, 12), slice(12, 15), IDX_MOUNT):
        covered[sl] += 1
    assert (covered == 1).all()


def test_yaw_is_read_from_the_rotation_matrix():
    s = NavState()
    assert s.yaw == pytest.approx(0.0)
    theta = 0.4
    s.R = np.array(
        [[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]]
    )
    assert s.yaw == pytest.approx(theta)


# ------------------------------------------------------------------------------------------
# Stationary detection
# ------------------------------------------------------------------------------------------


def test_stationary_phone_is_detected():
    """Gravity dominates accelerometer *magnitude* even at rest, which is why the test is on
    variance. A magnitude threshold would never fire."""
    accel = np.tile([0.0, 0.0, 9.80665], (10, 1)) + RNG.normal(0, 0.01, (10, 3))
    gyro = RNG.normal(0, 0.001, (10, 3))
    assert is_stationary(accel, gyro, CFG)


def test_driving_is_not_stationary():
    accel = np.tile([0.0, 0.0, 9.80665], (10, 1)) + RNG.normal(0, 1.5, (10, 3))
    gyro = RNG.normal(0, 0.3, (10, 3))
    assert not is_stationary(accel, gyro, CFG)


def test_turning_at_constant_speed_is_not_stationary():
    """Smooth cornering has low accel variance but high gyro -- the case a variance-only detector
    would misclassify as a stop, injecting a false ZUPT mid-turn."""
    accel = np.tile([0.0, 0.0, 9.80665], (10, 1)) + RNG.normal(0, 0.01, (10, 3))
    gyro = np.tile([0.0, 0.0, 0.5], (10, 1))
    assert not is_stationary(accel, gyro, CFG)


def test_stationary_rejects_malformed_windows():
    with pytest.raises(ValueError, match=r"\(n, 3\)"):
        is_stationary(np.zeros((10,)), np.zeros((10, 3)), CFG)


# ------------------------------------------------------------------------------------------
# NHC gating
# ------------------------------------------------------------------------------------------


def test_nhc_applies_on_a_straight_at_speed():
    assert nhc_is_valid(speed_mps=16.7, yaw_rate=0.01, lateral_accel=0.1, cfg=CFG)


@pytest.mark.parametrize(
    ("speed", "yaw_rate", "lat_accel", "why"),
    [
        (0.2, 0.0, 0.0, "stopped: no direction of travel to be lateral to"),
        (16.7, 1.2, 0.0, "hard cornering"),
        (16.7, 0.0, 6.0, "approaching slip"),
    ],
)
def test_nhc_is_gated_off_when_the_assumption_breaks(speed, yaw_rate, lat_accel, why):
    assert not nhc_is_valid(speed, yaw_rate, lat_accel, CFG), why


# ------------------------------------------------------------------------------------------
# chi-squared gate -- the mechanism that makes GNSS optional rather than a mode switch
# ------------------------------------------------------------------------------------------


def test_consistent_fix_is_accepted():
    assert chi2_gate(np.array([0.5, 0.3, 0.1]), np.eye(3) * 4.0, CFG.chi2_gate_3dof)


def test_multipath_outlier_is_rejected():
    """A 50 m jump on tunnel exit, against a 2 m-sigma covariance."""
    assert not chi2_gate(np.array([50.0, 10.0, 2.0]), np.eye(3) * 4.0, CFG.chi2_gate_3dof)


def test_singular_covariance_rejects_rather_than_crashes():
    assert not chi2_gate(np.array([1.0, 1.0, 1.0]), np.zeros((3, 3)), CFG.chi2_gate_3dof)


def test_inflated_covariance_admits_a_larger_correction():
    """After a long outage the filter is genuinely uncertain, so a big correction is consistent --
    this is what makes re-acquisition smooth instead of a snap."""
    innovation = np.array([20.0, 0.0, 0.0])
    assert not chi2_gate(innovation, np.eye(3) * 4.0, CFG.chi2_gate_3dof)
    assert chi2_gate(innovation, np.eye(3) * 400.0, CFG.chi2_gate_3dof)


# ------------------------------------------------------------------------------------------
# Mount disturbance
# ------------------------------------------------------------------------------------------


def test_bump_is_detected():
    gyro = RNG.normal(0, 0.01, (20, 3))
    gyro[10] += 8.0  # phone knocked
    assert detect_mount_disturbance(gyro, CFG)


def test_normal_driving_is_not_a_bump():
    gyro = np.column_stack([np.zeros(20), np.zeros(20), np.linspace(0, 0.4, 20)])
    assert not detect_mount_disturbance(gyro, CFG)


# ------------------------------------------------------------------------------------------
# Unimplemented surface
# ------------------------------------------------------------------------------------------


def test_filter_initialises_with_a_well_formed_covariance():
    f = InEKF()
    assert f.P.shape == (ERROR_STATE_DIM, ERROR_STATE_DIM)
    assert np.allclose(f.P, f.P.T), "covariance must be symmetric"
    assert (np.linalg.eigvalsh(f.P) > 0).all(), "covariance must be positive definite"


@pytest.mark.parametrize("method", ["update_gnss", "update_nhc", "update_zupt"])
def test_sprint1_surface_fails_loudly_rather_than_silently(method):
    """Placeholders raise. A stub that returns None would let the harness produce plausible
    all-zero trajectories and report them as results.

    `propagate` left this list when P-02 implemented it. That was this case's job: it is a
    tripwire that fires the moment a placeholder becomes real, forcing the migration of the
    SE_2(3) derivation tests off their local helpers and onto `core.reference.inekf` (see the
    module docstring of tests/test_se23_derivation.py). The remaining three still guard the
    surface, and each leaves the same way -- by being implemented, in P-03.
    """
    f = InEKF()
    args = {
        "propagate": (np.zeros(3), np.zeros(3), 0.01),
        "update_gnss": (np.zeros(3), np.eye(3)),
        "update_nhc": (),
        "update_zupt": (),
    }[method]
    with pytest.raises(NotImplementedError, match="Sprint 1"):
        getattr(f, method)(*args)
