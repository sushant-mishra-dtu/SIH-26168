# models/ — learned components

**Seat M.** PyTorch.

Two networks, both small. The high-leverage one is the smaller of the two.

## What lives here

| Component | Job | Size |
|---|---|---|
| **Speed + variance head** | Regress body-frame forward speed **and its variance** from an IMU window | TCN or 1D-ResNet |
| **Adaptive R_NHC CNN** | Output the NHC pseudo-measurement covariance per step | ~6k params (AI-IMU) |
| `export/` | FP16 TFLite / ExecuTorch, with a covariance-head degradation test | — |

## Contract

**Every network outputs an uncertainty, and the uncertainty is part of the deliverable.** The filter
needs to know how much to trust an estimate. A confidently wrong covariance corrupts a Kalman filter
worse than a noisy mean — which is why Gate 2 tests calibration (≥95% of speed errors inside ±2σ),
not accuracy.

**Acceleration is never double-integrated to obtain speed.** Not as a fallback, not as a baseline
component, nowhere. See [../docs/ERROR_BUDGET.md](../docs/ERROR_BUDGET.md) §2.

**No pedestrian weights.** RoNIN / IONet / RIDI / TLIO / IDOL / CTIN encode a 0.5–2 m/s gait prior
and under-predict badly at 16.7 m/s. Architectures and filter frameworks transfer; weights do not.

**No network before Gate 1 clears.** The physics-only filter must stand on its own first.

## Export

FP16 by default. INT8 only behind an explicit covariance-head degradation test — quantisation error
on a variance output does not show up in ordinary accuracy metrics but does corrupt the filter.

## Input representation

Body-frame IMU with attitude encoding (the AirIO result: +66.7% from body-frame representation over
world-frame). Window ~1–2 s.

## Status

**Architectures are defined; nothing is trained.**
[`speed_head.py`](speed_head.py) carries the TCN with its log-variance output, the Gaussian NLL and
the calibration metric; [`baseline_rnn.py`](baseline_rnn.py) carries the Onyekpe baseline at the
published hyperparameters (1 s window, MAE, Adamax 7e-4, batch 128, dropout 0.05, ~72 units).

> ⚠️ **Neither file is covered by CI.** `torch` is deliberately not installed there — the harness is
> the critical path and must never be blocked on a 2 GB download. That is an accepted gap, and it
> means these two files have never been executed in a clean environment. Run them locally before
> quoting anything from them.

**`update_speed` on the filter side is still `NotImplementedError`** — deliberately, because a stub
returning `None` would let the harness produce plausible all-zero trajectories and report them as
results.

**Gate 1 is currently blocked** (D-053), so the rule above is live rather than theoretical: no
network goes on top of a filter that has not cleared physics-only. The remaining seat-M work that
does *not* wait on Gate 1 is documentary — list every hyperparameter the Onyekpe INS paper states
against every one it omits, and log each omission we have to choose as a DECISION_LOG row rather
than letting it sit silently in a config file.
