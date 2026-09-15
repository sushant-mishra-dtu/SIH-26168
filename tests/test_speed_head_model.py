"""Torch-specific P-08 architecture checks, explicitly skipped in the torch-free CI job."""

from __future__ import annotations

import pytest


def _speed_head_symbols():
    torch = pytest.importorskip("torch")
    from models.speed_head import (
        MIN_VARIANCE,
        N_INPUT_CHANNELS,
        WINDOW_SAMPLES,
        SpeedHead,
        gaussian_nll,
    )

    return torch, MIN_VARIANCE, N_INPUT_CHANNELS, WINDOW_SAMPLES, SpeedHead, gaussian_nll


def test_speed_head_outputs_one_positive_variance_per_window():
    torch, min_variance, n_input_channels, window_samples, speed_head, _ = _speed_head_symbols()
    model = speed_head()
    speed, variance = model(torch.zeros(3, n_input_channels, window_samples))
    assert speed.shape == (3,)
    assert variance.shape == (3,)
    assert bool(torch.all(variance >= min_variance))


def test_gaussian_nll_penalises_a_worse_mean_when_variance_is_fixed():
    torch, _, _, _, _, gaussian_nll = _speed_head_symbols()
    target = torch.tensor([1.0])
    variance = torch.tensor([1.0])
    assert gaussian_nll(torch.tensor([1.0]), variance, target) < gaussian_nll(
        torch.tensor([2.0]), variance, target
    )
