"""Onyekpe "Learning to Localise" INS baseline -- the number we must beat.

Requires the `ml` extra. This is a *reproduction*, not our method: it exists so that our result has
an honest phone-grade reference point rather than being compared to AI-IMU's automotive-grade IMU
or WhONet's wheel speed, neither of which we are allowed to claim (docs/METHOD.md section 14).

Published hyperparameters (docs/DATASETS.md section 3):

    window      1 second (10 samples at 10 Hz)
    loss        MAE
    optimizer   Adamax, lr 7e-4
    batch       128
    dropout     0.05
    model       vanilla RNN, 1 hidden layer, 72 units (~8,200 params)

The source papers do **not** state epochs, and the INS paper does not fully surface its loss and
optimizer -- those two rows come from the WhONet paper. Where we have to choose, the choice goes in
DECISION_LOG rather than sitting silently in a config (D-009 discipline).
"""

from __future__ import annotations

import torch
import torch.nn as nn

WINDOW_SAMPLES = 10  # 1 s at 10 Hz
HIDDEN_UNITS = 72
DROPOUT = 0.05
BATCH_SIZE = 128
LEARNING_RATE = 7e-4

#: accel xyz + gyro xyz in NED, per the published setup.
N_INPUT_CHANNELS = 6


class OnyekpeBaseline(nn.Module):
    """Vanilla RNN correcting INS displacement error and orientation-rate error.

    Input  ``(batch, WINDOW_SAMPLES, N_INPUT_CHANNELS)``
    Output ``(batch, 2)`` -- displacement-error correction, orientation-rate correction.

    Deliberately a *vanilla* RNN, not an LSTM: matching the published architecture is the point.
    Improving on it here would make the baseline unfalsifiable as a comparison.
    """

    def __init__(self, hidden: int = HIDDEN_UNITS, dropout: float = DROPOUT) -> None:
        super().__init__()
        self.rnn = nn.RNN(
            input_size=N_INPUT_CHANNELS,
            hidden_size=hidden,
            num_layers=1,
            nonlinearity="tanh",
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(hidden, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 3 or x.shape[2] != N_INPUT_CHANNELS:
            raise ValueError(
                f"expected (batch, {WINDOW_SAMPLES}, {N_INPUT_CHANNELS}), got {tuple(x.shape)}"
            )
        h, _ = self.rnn(x)
        return self.out(self.dropout(h[:, -1, :]))

    def n_parameters(self) -> int:
        """Should land near the published ~8,200. A large divergence means the architecture was
        misread, and a baseline that is not the published baseline proves nothing."""
        return sum(p.numel() for p in self.parameters())


def make_optimizer(model: nn.Module, lr: float = LEARNING_RATE) -> torch.optim.Optimizer:
    """Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the distinction is
    exactly the kind of detail that makes a reproduction fail to reproduce."""
    return torch.optim.Adamax(model.parameters(), lr=lr)


def loss_fn() -> nn.Module:
    """MAE, as published."""
    return nn.L1Loss()
