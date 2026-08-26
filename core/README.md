# core/ — filter core & edge engine

**Seat S.** Language: C++ or Rust — *decision pending, log it in
[../docs/DECISION_LOG.md](../docs/DECISION_LOG.md) once made.*

The spine of the whole system, and the half of the project the sponsor cares most about given the
FOG-IMU and EW-resilience framing in the problem statement.

## What lives here

| Path | Contents |
|---|---|
| `filter/` | SE₂(3) state, propagation, gated measurement updates |
| `constraints/` | NHC / ZUPT / ZARU pseudo-measurements **and their gating conditions** |
| `ffi/` | JNI surface for Android; the same library feeds the edge build |

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

Scaffold only. Sprint 0: choose the language, stand up the build and CI, start the multi-hour
stationary log for Allan variance, work the SE₂(3) propagation on paper.
