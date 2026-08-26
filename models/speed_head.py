"""Learned forward-speed head: regresses speed **and its variance** from an IMU window.

Requires the `ml` extra (`pip install -e ".[ml]"`). Kept out of the harness import path so the
evaluation critical path never blocks on a torch install.

Two design commitments, both from DECISION_LOG:

  D-003  Speed is regressed, never obtained by double-integrating acceleration. 10 mg of accel
         bias is ~176 m of error in 60 s -- 176% of the budget from a single term.
  D-017  No pedestrian weights. RoNIN/IONet/TLIO encode a 0.5-2 m/s gait prior and under-predict
         badly at 16.7 m/s. Architectures transfer; weights do not.

The variance output is not decoration. Gate 2 tests calibration (>=95% of errors inside +/-2 sigma),
not accuracy, because a confidently wrong covariance corrupts a Kalman filter worse than a noisy
mean.
"""

from __future__ import annotations

import torch
import torch.nn as nn

#: Input channels: accel xyz, gravity xyz, gyro xyz (yaw/pitch/roll). Magnetometer is excluded --
#: cabin ferromagnetics make it a weak prior at best (docs/DATASETS.md).
N_INPUT_CHANNELS = 9

#: 2 s at 10 Hz. IO-VNBD's smartphone stream is 10 Hz and no resampling changes that.
WINDOW_SAMPLES = 20

#: Floor on predicted variance. An unclamped variance head can output ~0 and hand the filter an
#: infinitely-trusted measurement, which drives the covariance singular in one step.
MIN_VARIANCE = 1e-4


class TemporalBlock(nn.Module):
    """Dilated causal conv block. Causal because at deployment there is no future window."""

    def __init__(self, in_ch: int, out_ch: int, kernel: int = 3, dilation: int = 1) -> None:
        super().__init__()
        self.pad = (kernel - 1) * dilation
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel, padding=self.pad, dilation=dilation)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel, padding=self.pad, dilation=dilation)
        self.norm1 = nn.BatchNorm1d(out_ch)
        self.norm2 = nn.BatchNorm1d(out_ch)
        self.act = nn.ReLU()
        self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.downsample(x)
        y = self.act(self.norm1(self.conv1(x)[:, :, : -self.pad or None]))
        y = self.act(self.norm2(self.conv2(y)[:, :, : -self.pad or None]))
        return self.act(y + residual)


class SpeedHead(nn.Module):
    """TCN regressing (forward speed, log-variance) from a body-frame IMU window.

    Input  ``(batch, N_INPUT_CHANNELS, WINDOW_SAMPLES)`` -- body frame, per the AirIO result that
    body-frame input beats world-frame by a wide margin.
    Output ``(speed_mps, variance)``, both ``(batch,)``.

    Predicting *log* variance rather than variance keeps the output unconstrained and the loss
    well-conditioned; the exp on the way out guarantees positivity without a clamp fighting the
    optimiser.
    """

    def __init__(self, channels: tuple[int, ...] = (32, 64, 64), dropout: float = 0.1) -> None:
        super().__init__()
        blocks: list[nn.Module] = []
        in_ch = N_INPUT_CHANNELS
        for i, out_ch in enumerate(channels):
            blocks.append(TemporalBlock(in_ch, out_ch, dilation=2**i))
            in_ch = out_ch
        self.tcn = nn.Sequential(*blocks)
        self.dropout = nn.Dropout(dropout)
        self.speed = nn.Linear(in_ch, 1)
        self.log_var = nn.Linear(in_ch, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if x.dim() != 3 or x.shape[1] != N_INPUT_CHANNELS:
            raise ValueError(
                f"expected (batch, {N_INPUT_CHANNELS}, {WINDOW_SAMPLES}), got {tuple(x.shape)}"
            )
        h = self.tcn(x)[:, :, -1]  # last timestep: causal, so this is 'now'
        h = self.dropout(h)
        speed = self.speed(h).squeeze(-1)
        variance = torch.exp(self.log_var(h).squeeze(-1)).clamp_min(MIN_VARIANCE)
        return speed, variance


def gaussian_nll(pred: torch.Tensor, variance: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Heteroscedastic Gaussian NLL: the loss that makes the variance head mean something.

    An MSE loss would train the mean and leave the variance arbitrary. This one is minimised only
    when the predicted variance actually matches the realised squared error, which is precisely
    what Gate 2 measures.
    """
    return (0.5 * (torch.log(variance) + (pred - target) ** 2 / variance)).mean()


def calibration_fraction(
    pred: torch.Tensor, variance: torch.Tensor, target: torch.Tensor, n_sigma: float = 2.0
) -> float:
    """Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_sigma = 2.**

    Report this beside every speed-accuracy number. A head with excellent RMSE and 60% coverage is
    a head that will damage the filter.
    """
    with torch.no_grad():
        inside = (pred - target).abs() <= n_sigma * variance.sqrt()
        return float(inside.float().mean())
