# core/ — filter core & edge engine

**Seat S.** **The screening filter is the Python reference in `reference/`** (D-022). The compiled
core is an October port; the choice between C++ and Rust is deferred with it, and only the `ffi/`
interface is a screening deliverable (D-043).

The spine of the whole system, and the half of the project the sponsor cares most about given the
FOG-IMU and EW-resilience framing in the problem statement.

## What lives here

| Path | Contents | State |
|---|---|---|
| `reference/inekf.py` | **The screening filter.** SE₂(3) state, propagation, the update family, gating predicates, χ² gate | Written and tested |
| `filter/` | SE₂(3) state, propagation, gated measurement updates — the October port | Empty |
| `constraints/` | NHC / ZUPT / ZARU pseudo-measurements **and their gating conditions** | Empty |
| `ffi/` | JNI surface for Android; the same library feeds the edge build | Empty — D-043 wants a ~100-line interface definition at screening, not an implementation |

**Gating lives with the caller, not in the filter (D-052).** `is_stationary` needs accelerometer
variance over a window and `nhc_is_valid` needs yaw rate and lateral acceleration — none of which
is a property of the *state*. Putting them inside would mean the filter storing a raw-sample buffer
to re-derive what the caller already has, and would hide the one rule the error budget depends on:
**ZUPT and ZARU fire together at every detected stop** (D-004). A stop where only one runs is a bug,
not a tuning choice, and that is only enforceable where the detector is called.

## Contract

**One library, two frontends.** Android via JNI (seat A) and the 200 Hz FOG edge engine consume the
identical code. There is no Android-specific filter and no edge-specific filter. This is what makes
the "edge deployable engine" requirement true by construction rather than a second project.

**The `ffi/` interface is agreed with seat A in writing before either side writes against it.**

**The learned components are swappable modules, not baked in.** TFLite/ExecuTorch on phone,
ONNX/TensorRT on edge. The filter must run correctly with every network disabled — that
configuration is the Gate 1 baseline.

## Design constraints

- One continuously-running filter. GNSS is a χ²-gated optional correction, never a mode switch.
- State: rotation, velocity, position on SE₂(3), plus gyro/accel biases, plus **R_sv** (phone→vehicle).
- Process noise Q is seeded from a measured Allan-variance run, not guessed.
- Never assume a nominal Δt. Use real timestamps.
- Every constraint has an explicit **off** condition. An ungated NHC during a slip is worse than no NHC.
- Filter propagation on a high-rate thread reading a lock-free ring buffer; NN inference at 1–10 Hz
  on a second thread posting measurement updates; GNSS callback on a third.

## Status

**`reference/inekf.py` is written: `propagate()` on SE₂(3), plus ZUPT, ZARU, NHC and gated GNSS.**
It is written from [../docs/SE23_PROPAGATION.md](../docs/SE23_PROPAGATION.md), which was derived
and CI-verified *before* the filter existed — do not re-derive it at the keyboard, and do not edit
the filter and the derivation independently.

Three things are open, in priority order:

1. **The filter is not consistent, and Gate 1 must not be declared on it (D-053).** Full-state NEES
   is **29.90** against a 95% band of **[16.843, 19.195]** — over-confident. Propagation-only
   (18.287) and propagation+ZUPT (18.929) are both in band and asserted by tests; **ZARU is the sole
   cause**, with two measured contributors. Numbers in
   [../docs/ERROR_BUDGET.md](../docs/ERROR_BUDGET.md) §9.4. P-04 owns it, together with `P₀`.
2. **`P₀` is still a flat `1e-3·I`** — far too tight on the mount block, too loose on position.
3. `update_speed` is `NotImplementedError` (Sprint 2), and `ffi/` is an empty directory (D-043).

Superseded, so it is not restarted: the multi-hour stationary log for Allan variance is **off** the
Gate 1 critical path (D-038) and `Q_c` now comes from IO-VNBD's own segments (D-045). The mount
block of `Q_c` is deliberately **zero** (D-048) — the model in force is a rigid mount, and nothing
in this repo measures otherwise.
