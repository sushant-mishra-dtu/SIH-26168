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
| `ffi/` | [`idr_core.h`](ffi/idr_core.h) — the FFI surface, **defined but not implemented** (D-043) |

## Contract

**One library, two frontends.** Android via JNI (seat A) and the 200 Hz FOG edge engine consume the
identical code. There is no Android-specific filter and no edge-specific filter. This is what makes
the "edge deployable engine" requirement true by construction rather than a second project.

**The `ffi/` interface is agreed with seat A in writing before either side writes against it.**
[`ffi/idr_core.h`](ffi/idr_core.h) is that writing. It is a C header rather than a C++ or Rust
surface for one reason: both frontends have to bind to it, and JNI binds C directly while Rust
reaches it through `extern "C"` — a C++ or Rust-native interface would force one of the two through
a shim (D-077). It defines `init`, `propagate`, the update family, mount re-inflation, and pose +
covariance out, with units, frames and buffer ownership stated on every entry point. **There is no
implementation behind it, by decision:** D-022 defers the port to October and the Python reference
in `reference/inekf.py` is the specification until then.

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

## Measured throughput of the Python reference

The screening filter is Python (D-011), and the question the October port has to answer is where
the time goes. Measured on this container, at the `S-` stream's 10 Hz, `dt` = 0.1 s:

| Call | Per call | Rate |
|---|---|---|
| `propagate` | **0.344 ms** | 2,905 /s |
| `update_nhc` | 0.085 ms | 11,710 /s |
| `update_zupt` | 0.074 ms | 13,593 /s |
| `update_gnss` | 0.090 ms | 11,177 /s |
| `update_zaru` | 0.014 ms | 70,128 /s |
| **A realistic 10 Hz step** (`propagate` + one constraint) | **0.430 ms** | **2,327 /s** |

That is **233× real time at 10 Hz**, so the full 14-sequence × 5-outage-length sweep runs in about
five minutes and nothing in the harness needs caching.

**The hotspot is the 36×36 matrix exponential**, and it is measured rather than assumed:
`van_loan` costs 0.172 ms, which is **50.1%** of `propagate`, and `expm_series` is the largest
single `tottime` in a cProfile of 600 steps (0.108 s of 0.226 s cumulative). It is there because
D-031 rejected the `Φ G Q_c Gᵀ Φᵀ Δt` shortcut on a measured 4.2% error at Δt = 0.1 s. **The
October port must validate any cheaper closed form against this one** rather than substituting it
— an undersized `Q_d` makes the filter reject good measurements at the χ² gate, and that failure
reads as a sensor problem rather than a tuning one.

At 200 Hz on the FOG build the same step budget is 5 ms and the Python reference would use 8.6% of
it, so the port is not needed for throughput; it is needed for the deployment target.

## Status

Scaffold, plus the FFI definition. The SE₂(3) propagation is **derived and CI-verified** —
[../docs/SE23_PROPAGATION.md](../docs/SE23_PROPAGATION.md) is what Sprint 1 writes
`propagate()` and the update family from; do not re-derive it at the keyboard.

Language choice is deferred to the October port by D-022 — the screening filter is the Python
reference. Allan variance is done and measured from IO-VNBD's own stationary segments (D-045), not
from a team phone; our own handset's multi-hour run is still worth doing for the demo and edge
story but is explicitly off the Gate 1 critical path (D-038).
