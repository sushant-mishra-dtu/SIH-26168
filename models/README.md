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

**Onyekpe INS baseline (P-06): trained.** `python -m models.train_baseline_rnn --data data` fits
it and scores it over the frozen outage sweep; `--audit` prints the stated-versus-omitted
hyperparameter table and trains nothing. Nine of the nineteen settings are ours rather than the
papers' (D-098), the regression target is a tenth (D-099), and the result is reported as an
improvement over raw INS because that is the shape the published claim takes (D-100).

Needs the `ml` extra and the dataset: `pip install -e ".[ml]"` then
`python -m eval.fetch --sync-only`. `torch` is imported inside the functions that need it, so the
audit and its tests still run in the CI job that has neither.

**The speed+variance head (P-08) is still untrained** — that is Sprint 2, and Gate 1 comes first.
