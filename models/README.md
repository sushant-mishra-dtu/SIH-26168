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

Scaffold only. Sprint 0: extract every stated hyperparameter from the Onyekpe INS paper, list the
ones it omits as choices we must make and log, pick the backbone, build the reproduction skeleton.
**No training until the harness exists.**
