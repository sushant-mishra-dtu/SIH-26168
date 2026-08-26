"""Synthetic GNSS-outage injection.

Protocol: docs/EVALUATION.md section 3. Lengths 10/30/60/120/180 s, non-overlapping, held-out
scenarios only, 1 s prediction cadence.

During an outage the filter receives **no GNSS update at all** -- not a degraded one. Feeding a
noisier fix is a different experiment (and an easier one); it is not what the problem statement
describes when it says the signal is denied.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: The mandated sweep. Do not add lengths without a DECISION_LOG entry -- comparability to the
#: published Onyekpe/WhONet numbers depends on these exact values.
OUTAGE_LENGTHS_S: tuple[int, ...] = (10, 30, 60, 120, 180)

#: The challenging-scenario sets are evaluated at 10 s only; long-outage sets at 30 s and above.
CHALLENGING_LENGTH_S: int = 10
LONG_LENGTHS_S: tuple[int, ...] = (30, 60, 120, 180)

SAMPLE_RATE_HZ: int = 10
PREDICTION_CADENCE_S: int = 1


@dataclass(frozen=True)
class Outage:
    """One injected outage window, as sample indices into a sequence."""

    sequence: str
    start_idx: int
    end_idx: int  # exclusive
    length_s: int

    @property
    def n_samples(self) -> int:
        return self.end_idx - self.start_idx

    @property
    def n_epochs(self) -> int:
        """Number of 1 s prediction epochs in this outage."""
        return self.length_s // PREDICTION_CADENCE_S

    def __post_init__(self) -> None:
        if self.start_idx < 0 or self.end_idx <= self.start_idx:
            raise ValueError(f"degenerate outage window [{self.start_idx}, {self.end_idx})")


def generate_outages(
    sequence: str,
    n_samples: int,
    length_s: int,
    *,
    sample_rate_hz: int = SAMPLE_RATE_HZ,
    warmup_s: int = 30,
) -> list[Outage]:
    """Tile a sequence with non-overlapping outages of one length.

    Deterministic and exhaustive: windows are laid end to end from the first sample after warmup.
    There is no randomness here on purpose -- a random draw would make the sequence count depend
    on the seed, and the published counts we compare against are fixed.

    ``warmup_s`` gives the filter GNSS-available time to converge its biases and R_sv before the
    first outage begins. Starting an outage at sample zero measures initialisation, not dead
    reckoning.
    """
    if length_s <= 0:
        raise ValueError(f"length_s must be positive, got {length_s}")
    window = length_s * sample_rate_hz
    start = warmup_s * sample_rate_hz
    if n_samples < start + window:
        return []  # sequence too short for even one outage of this length

    outages: list[Outage] = []
    idx = start
    while idx + window <= n_samples:
        outages.append(Outage(sequence, idx, idx + window, length_s))
        idx += window
    return outages


def generate_sweep(
    sequence_lengths: dict[str, int],
    lengths_s: tuple[int, ...] = OUTAGE_LENGTHS_S,
    *,
    sample_rate_hz: int = SAMPLE_RATE_HZ,
    warmup_s: int = 30,
) -> dict[int, list[Outage]]:
    """The full sweep across every held-out sequence, keyed by outage length.

    ``sequence_lengths`` maps sequence name -> number of samples. Sequences too short for a given
    length simply contribute nothing at that length, which is why the per-length sequence counts
    differ -- the same reason the published counts differ across the WhONet tables.
    """
    sweep: dict[int, list[Outage]] = {}
    for length_s in lengths_s:
        windows: list[Outage] = []
        for name, n in sorted(sequence_lengths.items()):
            windows.extend(
                generate_outages(
                    name, n, length_s, sample_rate_hz=sample_rate_hz, warmup_s=warmup_s
                )
            )
        sweep[length_s] = windows
    return sweep


def assert_non_overlapping(outages: list[Outage]) -> None:
    """Verify the non-overlap guarantee. Cheap to check, expensive to discover violated."""
    by_seq: dict[str, list[Outage]] = {}
    for o in outages:
        by_seq.setdefault(o.sequence, []).append(o)
    for seq, group in by_seq.items():
        ordered = sorted(group, key=lambda o: o.start_idx)
        for a, b in zip(ordered, ordered[1:], strict=False):
            if b.start_idx < a.end_idx:
                raise AssertionError(
                    f"overlapping outages in {seq}: "
                    f"[{a.start_idx}, {a.end_idx}) and [{b.start_idx}, {b.end_idx})"
                )


def mask_gnss(n_samples: int, outages: list[Outage]) -> np.ndarray:
    """Boolean mask, True where a GNSS fix is available.

    The filter consumes this directly: where False, the GNSS update step is simply not called.
    There is no mode flag and no branch -- see DECISION_LOG D-001.
    """
    mask = np.ones(n_samples, dtype=bool)
    for o in outages:
        mask[o.start_idx : o.end_idx] = False
    return mask
