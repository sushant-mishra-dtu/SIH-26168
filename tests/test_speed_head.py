"""P-08's NumPy-only contracts: labels, leakage, calibration, and no-torch behaviour."""

from __future__ import annotations

import builtins
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from models.train_speed_head import (
    FEATURE_COLUMNS,
    HYPERPARAMETERS,
    SpeedWindows,
    assert_features_are_clean,
    audit_table,
    build_windows,
    calibration_summary,
    main,
    monotonic_prefix_length,
)


class _LinearTruth:
    """A one-metre-per-second northbound truth track for direct window-label checks."""

    def ned_at(self, times_s: np.ndarray) -> np.ndarray:
        t = np.asarray(times_s, dtype=float)
        return np.column_stack([t, np.zeros_like(t)])


def _sequence(n_samples: int = 50):
    t_s = np.arange(n_samples, dtype=float) / 10.0
    imu = pd.DataFrame(
        {
            "accel_x": np.zeros(n_samples),
            "accel_y": np.zeros(n_samples),
            "accel_z": np.full(n_samples, 9.81),
            "gravity_x": np.zeros(n_samples),
            "gravity_y": np.zeros(n_samples),
            "gravity_z": np.full(n_samples, 9.81),
            "gyro_yaw": np.zeros(n_samples),
            "gyro_pitch": np.zeros(n_samples),
            "gyro_roll": np.zeros(n_samples),
            "time_since_start_ms": t_s * 1000.0,
        }
    )
    gnss = pd.DataFrame(
        {
            "date": ["2020-01-01 00:00:00.000"] * n_samples,
            "time_since_start_ms": t_s * 1000.0,
            "sample_idx": np.arange(n_samples),
        }
    )
    return SimpleNamespace(name="TOY", imu=imu, gnss=gnss)


def test_the_exact_nine_tensor_columns_clear_the_repo_leakage_guard():
    text = assert_features_are_clean()
    assert len(FEATURE_COLUMNS) == 9
    assert "no `V-` column reaches the input" in text
    assert "gps_" not in text


def test_every_omitted_training_choice_names_the_reserved_decision_row():
    for setting in HYPERPARAMETERS:
        if "OMITTED" in setting.source:
            assert setting.decision == "D-132"


def test_audit_exposes_the_stated_and_chosen_settings_without_reading_data():
    text = audit_table()
    assert "stated" in text and "ours" in text
    assert "Gaussian NLL" in text
    assert main(["--audit"]) == 0


def test_speed_targets_are_differenced_truth_positions_not_integrated_acceleration():
    windows = build_windows(_sequence(), _LinearTruth())
    assert windows.x.shape == (4, 20, 9)
    assert np.allclose(windows.absolute_speed_mps, 1.0)
    assert np.allclose(windows.delta_speed_mps, 0.0)
    x_delta, y_delta = windows.for_target("delta_speed")
    assert x_delta.shape == (4, 20, 9)
    assert np.allclose(y_delta, 0.0)


def test_a_clock_restart_keeps_the_prefix_and_excludes_the_second_clock():
    times = np.array([0.0, 0.1, 0.2, 0.3, 0.0, 0.1])
    assert monotonic_prefix_length(times) == 4


def test_calibration_reports_coverage_before_accuracy_and_rejects_invalid_variance():
    summary = calibration_summary(
        np.array([0.0, 2.0]), np.array([1.0, 1.0]), np.array([0.0, 5.0])
    )
    assert summary["n"] == 2
    assert summary["coverage_1sigma"] == 0.5
    assert summary["coverage_2sigma"] == 0.5
    assert summary["rmse_mps"] == pytest.approx(3.0 / np.sqrt(2.0))
    with pytest.raises(ValueError, match="positive"):
        calibration_summary(np.array([0.0]), np.array([0.0]), np.array([0.0]))


def test_delta_target_drops_only_the_nan_window():
    stem = SpeedWindows(
        "S1",
        np.ones((2, 20, 9), dtype="float32"),
        np.array([2.0, 3.0], dtype="float32"),
        np.array([np.nan, 1.0], dtype="float32"),
    )
    x, y = stem.for_target("delta_speed")
    assert x.shape[0] == 1
    assert y.tolist() == [1.0]


def test_running_without_torch_refuses_instead_of_fabricating_a_calibration(monkeypatch):
    real_import = builtins.__import__

    def no_torch(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise ImportError("no torch in this environment")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_torch)
    assert main([]) == 4
