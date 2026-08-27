# Implementation Plan v2 — consolidated plan of record

**Written:** Thu 27 Aug 2026 · **Submission:** Tue 8 Sep 2026 · **12 days out**
**Shareable page:** https://claude.ai/code/artifact/a6858ba3-8b13-460c-bb82-5cc5bc50e52b
**Supersedes:** the sprint calendar in [AGENTS.md](../AGENTS.md), the calendar in
[SPRINT_BOARD.md](SPRINT_BOARD.md), and the standalone *Master Implementation Plan — SIH26168 (ISRO)*
document in its entirety.

This plan is consolidated from four sources, all of which were read in full before it was written:

| # | Source | What it contributes | What is discarded |
|---|---|---|---|
| 1 | **Engineering survey** (`compass_artifact_…md` = `SIH26168_complete.md`) — 10-task literature review | The architecture, the error analysis, the citation hygiene, the honest limits | Nothing. This remains the technical authority. |
| 2 | **Master Implementation Plan — SIH26168 (ISRO)** — the demo-first plan | The presentation layer: 4-trajectory comparison, uncertainty ellipse, audience framing, research-proofs panel | Its filter (15-state quaternion ES-EKF), its stack (FastAPI/React/MapmyIndia/LangGraph), and its headline numbers. See §4. |
| 3 | **Delhi Road Graph** (seat P, 26 Aug) — OSM extract sizing and CSR design | The map layer's design, sized not built; decisions D-034–D-037 | Nothing. Deferred, not rejected. |
| 4 | **The repo itself** — 2 commits, clean tree, 88 test functions | Everything already built. The audit in §2 is against the code, not against a document. | Nine items need correcting. See §2B. |

---

## 1. What has not changed

The thesis survives consolidation intact, and nothing below reopens it:

> One continuously-running error-state **Invariant EKF on SE₂(3)**. The IMU always propagates; GNSS
> is an *optional* χ²-gated correction. There is no second system and no handoff, so "seamless
> transition within milliseconds" is satisfied **by construction**. Three inputs keep it honest: a
> **learned forward-speed head** (never double-integrated accel), **kinematic constraints**
> (NHC + ZUPT + ZARU), and **HMM map matching** as the outer layer.
>
> **The dominant error term is yaw, not speed.**

Also unchanged, and not up for negotiation in the next 12 days:

1. `S-` smartphone channels only. `V-` wheel speed is banned and CI-enforced.
2. Acceleration is never double-integrated for speed.
3. The evaluation harness is frozen before any model trains.
4. Gate 1 is a hard stop.
5. Every plot and table carries the commit SHA and seed that produced it.
6. Yaw error is logged separately, always.
7. AI-IMU's 1.10% and WhONet's 0.15% are never quoted as ours.

---

## 2. Audit — what is done, what needs redoing, what is left

### 2A. Done, verified in code, no rework

Every row here has tests. The counts are `def test_` functions per file.

| Component | Location | Tests |
|---|---|---|
| Vincenty inverse geodesic, geodetic→NED, angle wrapping | [`idr/geo.py`](../idr/geo.py) | 9 |
| Provenance stamping (commit SHA + seed, dirty-tree flag), seeding | [`idr/stamp.py`](../idr/stamp.py) | in protocol |
| CTE, CRSE, drift %, yaw error — each against a hand-computed case | [`eval/metrics/core.py`](../eval/metrics/core.py) | 11 |
| Wheel-speed leakage guard — allowlist + **its own CI job that verifies rejection** | [`eval/loaders/columns.py`](../eval/loaders/columns.py) | 8 |
| Outage injection 10/30/60/120/180 s + non-overlap proof | [`eval/outages/inject.py`](../eval/outages/inject.py) | in protocol |
| Frozen train/test split, defined in code, disjointness asserted | [`eval/splits.py`](../eval/splits.py) | 17 |
| `S-` loader with no unguarded path to the data | [`eval/loaders/io_vnbd.py`](../eval/loaders/io_vnbd.py) | in leakage |
| **SE₂(3) propagation derived on paper and checked numerically in CI** | [`SE23_PROPAGATION.md`](SE23_PROPAGATION.md), [`tests/test_se23_derivation.py`](../tests/test_se23_derivation.py) | 27 |
| Stationary detection, NHC gating, χ² gate, mount-disturbance detector | [`core/reference/inekf.py`](../core/reference/inekf.py) | 16 |
| Speed head architecture — TCN, log-variance, Gaussian NLL, calibration metric | [`models/speed_head.py`](../models/speed_head.py) | — (needs torch) |
| Onyekpe baseline architecture at published hyperparameters | [`models/baseline_rnn.py`](../models/baseline_rnn.py) | — (needs torch) |
| CI: lint + tests + protocol dry-run + a **separate** leakage-audit job | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | — |
| Document set: EVALUATION, ERROR_BUDGET, DATASETS, DECISION_LOG (33 rows), GLOSSARY | `docs/` | — |
| Delhi/NCR OSM extract sized, CSR layout designed, matcher decision reasoned | Seat P artifact | — |

The SE₂(3) work is the single most valuable thing in the repo and it is worth naming why: the
derivation was checked in CI **before** the filter that uses it existed, and doing it in that order
produced three corrections (D-029 midpoint evaluation, D-031 Van Loan magnitude, D-032 small-angle
cutoff) that would otherwise have shipped as a filter that runs, produces smooth plausible
trajectories, and is undebuggable.

### 2B. Needs redoing or correcting — nine items

| # | Item | Problem | Fix | Owner | When |
|---|---|---|---|---|---|
| R-1 | **Allan variance sourced from our own phone** | Wrong sensor. The screening numbers come from IO-VNBD, recorded on a Huawei P20 Pro / Moto G7 Power / BlackBerry Priv. Tuning `Q` from a teammate's phone on a desk models a device that produces none of the graded data — and it puts an Android task on the Gate 1 critical path. | Seed `Q` from **IO-VNBD's own >20 min stationary segments** ([DATASETS.md](DATASETS.md) §1.4). 20 min at 10 Hz gives ARW cleanly at τ = 1 s and bias instability out to τ ≈ 100–200 s — exactly the 10–180 s timescale we are graded on. Our own phone's Allan run continues in parallel for the demo and edge story, no longer blocking. | S | **Today** |
| R-2 | `FilterConfig.gyro_arw = 3e-3` rad/s/√Hz | ≈ 10.3 °/√hr, outside the 0.5–5 °/√hr phone range our own [ERROR_BUDGET.md](ERROR_BUDGET.md) §9 states. Self-flagged in [SE23_PROPAGATION.md](SE23_PROPAGATION.md) §10. Pessimistic rather than dangerous, but it is an internal inconsistency a judge can find. | Replaced by R-1's measured value. If the measurement lands near 10 °/√hr, say in the budget why that is realistic for a phone in a vibrating cabin. | S | Sprint 1 |
| R-3 | `P₀ = 1e-3·I`, flat | Wrong in both directions: far too tight on the mount block (which starts unknown), too loose on position (which starts at a GNSS fix). A wrong `P₀` makes the filter reject good measurements at the χ² gate, and that failure reads as a sensor problem, not a tuning problem. | Set per-block from [ERROR_BUDGET.md](ERROR_BUDGET.md): position from GNSS accuracy, mount yaw from the PCA initialiser's spread, biases from the Allan run. | S | Sprint 1 |
| R-4 | **CRSE convention unpinned** | `SUM_SQUARES` is a consistency argument (D-023), not a verified reading of the paper. It blocks the Gate 0 freeze and it scales every CRSE we report by √n. | Pin against the WhONet paper's own equation numbers and write them verbatim into [EVALUATION.md](EVALUATION.md) §4.2. If they differ, the paper wins. | D | **Today** |
| R-5 | **DECISION_LOG missing D-034–D-037** | The seat P artifact cites them; the log ends at D-033. The record of what we believed and when is the entire point of an append-only log, and a gap in it is worse than a missing document. | Transcribe from the seat P artifact. Draft rows are in §8 — seat P confirms wording. | P | **Today** |
| R-6 | Gate 0 requires "one command regenerates every figure" | Unsatisfiable at Gate 0: there are no figures until the filter runs. Leaving it in makes Gate 0 fail for a reason that is not about the harness. | Move to Gate 1. The `--dry-run` protocol validation stays at Gate 0. | D | **Today** |
| R-7 | README claims "79 tests" | 88 `def test_` functions exist; `pytest` is not installed on the primary machine, so neither number is currently verified locally. A hand-typed count goes stale on every commit. | Drop the number from the README, or have CI write it. Verify the suite actually runs on this machine before Gate 0 — CI green on Ubuntu is not evidence the Windows dev box works. | D | **Today** |
| R-8 | IO-VNBD accelerometer sign convention unconfirmed | SE₂(3) test 2 ("stationary 60 s → drift < 1 mm") is only a gravity-sign check once the input convention is known. Android's `TYPE_ACCELEROMETER` and a raw IMU log do not always agree. | Confirm against a stationary segment before trusting test 2. Half an hour, and it invalidates a Gate 1 result if skipped. | S | Sprint 1 |
| R-9 | Stale calendars in two places | [AGENTS.md](../AGENTS.md) sprint table (already bannered) and [SPRINT_BOARD.md](SPRINT_BOARD.md) header, which still reads "Today: Wed 26 Aug — Sprint 0, day 1". D-021 exists because stale calendars cost this project a replan already. | Both get a superseded banner pointing here. This file is now the authoritative calendar. | C | **Today** |

### 2C. Not started — the actual remaining work

Ordered by dependency. Everything above the line must happen; everything below it is explicitly deferred.

| Work | Depends on | Owner | Sprint |
|---|---|---|---|
| **Download IO-VNBD**, decide synchronised vs unsynchronised, write `data/manifest/` with per-file SHA-256 | — | D | **0 — today, critical path** |
| Allan variance from IO-VNBD stationary segments → `Q_c` | dataset | S | 0–1 |
| `InEKF.propagate()` — [SE23_PROPAGATION.md](SE23_PROPAGATION.md) §8.1–8.2, exact Γ₀/Γ₁/Γ₂, midpoint `A_RI`, Van Loan `Q_d` | derivation (done) | S | 1 |
| `update_zupt`, `update_zaru`, `update_nhc`, `update_gnss` + SE₂(3) tests 7–11 (incl. **NEES consistency**) | propagate | S | 1 |
| Raw-strapdown INS baseline and GNSS-available baseline | loader | P | 1 |
| Onyekpe INS baseline reproduced at published hyperparameters | loader, torch | M | 1 |
| Wire `eval/run.py` — load held-out sequences, run the filter per outage window, emit stamped metrics + figures | filter, loader | D | 1 |
| Speed + variance head: training loop, trained weights, calibration plot | harness, torch | M | 2 |
| Speed head fused as a pseudo-measurement with its predicted `R` | filter, head | S+M | 2 |
| Adaptive `R_NHC` (AI-IMU mechanism, ~6k params) | Gate 2 clear | M | 3 |
| `R_sv` in-filter estimation + PCA initialiser + bump-detector wiring | filter | S | 3 |
| Full evaluation sweep, all mandatory plots, drift % median **and** p95 | everything | D | 3 |
| **Replay renderer** (§4C) over harness output | harness output | A | 3 |
| `core/ffi/` interface contract written as a header/trait file — not implemented, *defined* | filter | S | 3 |
| Method write-up, deck, video | everything | C | 3 |
| — *deferred past screening, stated as deferred in the write-up* | | | |
| Online HMM map matcher over the CSR graph | — | P | Oct |
| Android foreground logger + demo app + JNI | — | A | Oct |
| Car-park mode (barometer floor + ramp detection) | — | P | Oct |
| comma2k19 pretraining | — | M | Oct |
| Delhi/NCR collection + domain-shift ablation | — | C | Sep–Oct |
| C++/Rust port of the core (D-022) | — | S | Oct |

---

## 3. The architecture, after consolidation

Unchanged from the survey and the repo. Stated here so the reconciliation in §4 has something to
reconcile *against*.

```
  IMU (accel + gyro)            ─┬─→ speed + variance head (TCN, 1–2 s window)  ─┐
  10 Hz phone / 200 Hz FOG       │                                                │ pseudo-meas
                                 ├─→ adaptive R_NHC (AI-IMU CNN, ~6k params)  ─┐  │ with predicted R
                                 │                                             │  │
                                 ├─→ stationary detector → ZUPT + ZARU  ───────┼──┤
                                 │                                             │  │
                                 └─→ ══════ propagation, always running ═══════╪══╡
                                                                               │  │
                                        NHC (no sideways, no vertical) ←── R ──┘  │
                                                                                  ▼
   GNSS ──→ χ² innovation gate ──accepted──────────────────────────────→ ┌─────────────────┐
             │                                                           │  InEKF on SE₂(3) │
             └──rejected: tunnel or multipath. No update. No mode switch─→│  R,v,p,b_g,b_a,  │
                                                                          │  R_sv  (18-dim   │
   Baro ──→ floor detection (car parks only) ────────────────────────────→│  error state)    │
                                                                          └────────┬─────────┘
                                                                                   │ 10 Hz pose
                                            HMM map matching  ←────────────────────┤ + covariance
                                            emission σ from filter covariance      │
                                                     └── heading feedback ──────────┘
```

The rejected-GNSS edge is the whole argument. In a tunnel nothing passes the gate, so nothing is
applied. There is no code path to switch, therefore no transition latency and no position jump.

**State (18-dimensional error state, right-invariant error `η = X̂X⁻¹`, D-028):**

```
δθ (3) │ δv (3) │ δp (3) │ δb_g (3) │ δb_a (3) │ ξ_sv (3)
attitude velocity position gyro bias  accel bias  mount angle
```

`ξ_sv` uses the vehicle-frame left-multiplied convention (D-030) precisely so that `ξ_sv,z` reads
directly as mount-yaw error in degrees and can be compared against the ~1° requirement in
[ERROR_BUDGET.md](ERROR_BUDGET.md) §5 without a change of basis.

**Where the 10% goes** — 1 km tunnel, 60 s at 16.7 m/s, 100 m budget:

| Term | Budget | Requirement it implies |
|---|---|---|
| Lateral — residual gyro bias | 40 m | **0.005–0.01 °/s** after ZARU. At 0.1 °/s this term alone eats 52 m. |
| Along-track — speed estimate | 30 m | **ε_v ≈ 0.5 m/s** RMS |
| Lateral — mount angle `R_sv` | 20 m | **≈ 1°**. A 5° knock costs 87 m, silently. |
| Gyro scale factor in turns | 10 m | scale-factor state + Allan-seeded `Q` |

Map matching is deliberately not in the allocation. It buys margin back; it is not a term we plan to
spend — because it does not exist in a car park.

---

## 4. Reconciling the Master Implementation Plan

The Master Plan and the repo describe two different systems. They cannot both be built in 12 days
and they should not both be built at all. The resolution is not a compromise: **the repo is the
system; the Master Plan is the presentation of it.** Everything in the Master Plan that is a
*navigation* claim is superseded; everything that is a *communication* idea is adopted and re-scoped.

### 4A. Rejected — and why, so it is not re-proposed in a week

| Master Plan item | Verdict | Reason |
|---|---|---|
| **15-state ES-EKF with "quaternion kinematics on SE(3)"** | **Replaced** by the 18-state InEKF on SE₂(3) | SE(3) carries rotation and position but not velocity — the group for INS is SE₂(3). More materially: 15 states has no room for `R_sv`, and the error budget needs mount yaw to ~1°, which a one-shot PCA alignment cannot hold. The InEKF is already derived, CI-checked, and gives yaw-consistency by construction. Rebuilding it as a naive quaternion EKF would discard 27 passing tests to obtain a filter with known false yaw observability. |
| **"Dynamic neural process noise covariance (Q_k)" attributed to AI-IMU** | **Factually wrong — do not build** | Brossard's CNN adapts the **measurement** noise `R` of the NHC pseudo-measurements — it decides how tightly to enforce "no sideways motion" at each step. It does not touch process noise. Building `Q_k` under an AI-IMU citation would implement a different, unvalidated method under a reference that does not support it, and that is the exact kind of thing an adversarial question finds. The repo's D-005 has this right; the Master Plan does not. |
| **LangGraph-style agentic supervisor + agent HUD** | **Cut** | It contributes nothing to position accuracy and adds a dependency plus an explainability surface a judge will probe. The mode logic it would "supervise" is a χ² test, which is four lines and already written. Deterministic state machines do not need an agent framework narrated over them. |
| **MapmyIndia Mappls Web SDK as primary map engine** | **Cut for screening** | An online SDK behind an API key contradicts the "100% offline" claim made two columns away in the same table. The committed path is the offline OSM CSR graph — sized at ~21 MiB for the Delhi bbox, ~32 MiB for core NCR, with a measured mmap resident set of ~16 KiB over a 180 s transit. Revisit Mappls post-screening only as a *rendering* layer, never as the matching graph. |
| **FastAPI + WebSocket backend + React/Vite/Tailwind cockpit** | **Replaced** by a static replay renderer (§4C) | Three days of build for a UI that, at a submission round with no judge in the room, is watched as a video. Worse, a live cockpit fed by its own simulator can display numbers the evaluation harness never produced — which is the one failure this project's entire protocol discipline exists to prevent. |
| **`scenarios/dataset_generator.py` — synthetic sensor replay** | **Cut** | Same reason, stated plainly: a demo must be a *renderer of harness output*, never a second simulator. If a trajectory appears on screen, the harness produced it from held-out data. |
| **"Digital twin drives through Atal Tunnel"** | **Cut** | We have no IMU recording from the Atal Tunnel. Animating a car through it would be showing synthesised sensors on a real map, which is a claim we cannot defend. Use real held-out IO-VNBD sequences with injected outages — less cinematic, actually true. |
| **RoNIN as "direct application: 1D-CNN and LSTM displacement estimation"** | **Contradicts D-017** | RoNIN's velocity regressor encodes a 0.5–2 m/s gait prior. A car at 16.7 m/s is off-distribution and it under-predicts badly. Architecture transfers; weights do not. |
| **"QGRU from the IO-VNBD paper"** | **Citation to verify or drop** | The IO-VNBD paper (*Data in Brief* 35:106885) is a dataset paper. Quaternion GRUs are not its contribution. The mandated baseline is the *Learning to Localise* INS models (IDNN / vRNN / LSTM / GRU). Do not cite a method to a paper that does not contain it. |
| **Headline targets: "RMSE < 1.0 m", ">95% drift reduction", "<2 ms edge inference"** | **Banned until the harness produces them** | None is currently backed by a measurement. The graded metric is drift as % of distance, reported as median **and** 95th percentile. Numbers enter the deck from `eval/figures/`, never from a plan document. |

### 4B. Adopted from the Master Plan

| Item | How it lands here |
|---|---|
| **4-trajectory comparison** — ground truth / raw GNSS / naive DR / ours | Already exactly the baseline set in [EVALUATION.md](EVALUATION.md) §5. This is the Master Plan's best contribution: it turns a table into a picture without inventing anything. It becomes the standard figure for every mandatory plot sequence. |
| **Visible, growing uncertainty ellipse** | Already an instrumentation requirement ([ERROR_BUDGET.md](ERROR_BUDGET.md) §7 — covariance trace). Rendering it costs nothing extra and it is the single most legible way to show a judge that the filter *knows* it is uncertain. |
| **Live sensor oscilloscope** | Kept as a replay of the actual `S-` accel/gyro channels beneath the trajectory, captioned with the stream and rate. Not a live feed, and never captioned in a way that implies 200 Hz — the phone stream is 10 Hz. |
| **Research-proofs / bibliography panel** | Cheap, and citation hygiene is already a non-negotiable. Include the sensor-grade caveats *in the panel*, not in a footnote. |
| **Audience framing** — quick-commerce, ride-hailing, ambulances, logistics, highway commuters | Good material for the deck's problem slide. Concrete Indian operators beat an abstract "GNSS-denied environments". |
| **GNSS integrity HUD** (C/N₀, sat count, HDOP) | Post-screening, and only from a real `GnssStatus` feed. A synthesised skyplot is decoration that looks like evidence. |
| **Zero-install phone probe over LAN** | Post-screening / Grand Finale, where there is a judge in the room to scan the QR code. Note for October: browser `DeviceMotion` delivers ~60 Hz *calibrated* data, so it is a demo toy and explicitly not a data source — D-013 requires uncalibrated types with the OS bias estimate kept separate. |

### 4C. The replay renderer — what replaces the cockpit

One self-contained HTML file. No build step, no server, no network, no map SDK.

- **Input:** the harness's own stamped output — `eval/figures/summary.json` plus one trajectory JSON
  per plotted sequence. The renderer contains no physics and no simulation.
- **Shows:** the four trajectories in local NED metres, the covariance ellipse growing through the
  outage and collapsing at re-acquisition, a scrubber over the outage window, the `S-` accel/gyro
  traces, and the live drift-%/yaw-error readout for the current timestep.
- **Carries the stamp:** commit SHA and seed rendered on the page. A screenshot of the demo is
  therefore self-evidencing.
- **Cost:** ~1.5 days, seat A, in Sprint 3, after the sweep produces real output.
- **The rule:** if the renderer can display it, the harness produced it. There is no second path.

This also gives the video its footage and the deck its figures, from one artefact.

---

## 5. Schedule — 12 days

Today is **Thu 27 Aug**, which is Sprint 0 **day 2 of 3**, with five blocking Sprint 0 items still
open. That is the pressure point, and it is why §6 has a *today* column at all.

| Sprint | Dates | Days | Focus | Gate |
|---|---|---|---|---|
| **0** | Thu 27 – Fri 28 Aug | 2 left | Dataset in hand, harness trustworthy, `Q` sourced | **G0** Fri 28: protocol frozen, harness reproduces to the digit on two machines |
| **1** | Sat 29 Aug – Tue 1 Sep | 4 | InEKF propagate + updates; Onyekpe baseline; raw-strapdown + GNSS-available baselines; `run.py` wired | **G1** Tue 1 Sep: physics-only within **3–5×** of GNSS-available over 60 s. **Hard stop.** |
| **2** | Wed 2 – Fri 4 Sep | 3 | Speed + variance head trained and fused with predicted `R` | **G2** Fri 4 Sep: **≥95%** of speed errors inside ±2σ |
| **3** | Sat 5 – Mon 7 Sep | 3 | Adaptive `R_NHC`; `R_sv` in-filter; full sweep; replay renderer; FFI contract; write-up, deck, video | **G3** Mon 7 Sep: submission-ready, one day early |
| **Submit** | **Tue 8 Sep** | — | Submit by **midday** | The buffer is the morning, not the deadline |

**Gate 1 is a hard stop.** If it fails, diagnose in order: **timestamps → NHC gating conditions →
process noise → ZUPT thresholds.** Do not add a network to a broken spine. At 12 days a failed Gate 1
means submitting the physics-only result honestly, which is a defensible submission; a rushed hybrid
nobody can debug is not.

**Cut order if a sprint slips:** adaptive `R_NHC` → `R_sv` in-filter estimation (fall back to the PCA
initialiser with an inflated fixed covariance) → replay renderer polish → the renderer entirely
(static matplotlib figures suffice). **Never cut:** the harness, the leakage audit, the yaw
instrument, the honest-limits section.

---

## 6. Work packages by seat

### S — filter core *(Sushant)*

**Today:** R-1 — pull the IO-VNBD stationary segments the moment the dataset lands and compute
overlapping Allan deviation per axis; ARW from the −½ slope at τ = 1 s, bias instability from the flat
minimum (×0.664). Record the measured numbers in [ERROR_BUDGET.md](ERROR_BUDGET.md) §9, replacing R-2's
placeholder. Start our own phone's multi-hour stationary log in parallel — it is no longer blocking,
but it is free once running and it is the edge-story evidence.

**Sprint 1 — the critical path of the whole project.** Write `propagate()` from
[SE23_PROPAGATION.md](SE23_PROPAGATION.md) §8: exact Γ₀/Γ₁/Γ₂ closed form (not Euler, D-029), `A_RI`
at the step midpoint, Van Loan `Q_d` (D-031). Then the update family. Reuse §9 tests 1–6 by deleting
the local helpers in `tests/test_se23_derivation.py` and re-pointing the assertions at
`core.reference.inekf` — do not invent new ones. Write tests 7–11.

**Write test 5 first** (yaw invariance of the top-left 9×9 of `A`). If it fails, something in §5.2
was transcribed wrong and every downstream number is decoration. **Write test 11 last and take it
seriously** — NEES inside the 95% χ² band over 100 Monte-Carlo runs is the test that catches an
inconsistent filter, which is the failure this entire design exists to avoid.

Also Sprint 1: R-3 (per-block `P₀`) and R-8 (confirm the accelerometer sign convention against a
stationary segment *before* trusting test 2).

**Sprint 3:** `R_sv` in-filter estimation with the PCA initialiser and bump-detector wiring; write
`core/ffi/` as an interface definition — a ~100-line header or trait, not an implementation. It costs
half a day and converts "we will port it to C++" into "here is the surface both the Android build and
the FOG edge build bind to." Measure and report the Python reference's throughput (steps/s at 10 Hz)
and name the 36×36 `expm` as the identified hotspot for the October port.

### M — learning

**Today:** finish reading the Onyekpe INS paper and list every hyperparameter it *states* versus every
one it *omits* — the INS paper's loss and optimiser are not fully surfaced, and epochs are stated
nowhere. Each omission is a choice we make, and each choice gets a DECISION_LOG row rather than
sitting silently in a config file. **No training until Gate 0.**

**Sprint 1:** reproduce the Onyekpe baseline — 1 s window (10 samples at 10 Hz), MAE, Adamax 7e-4,
batch 128, dropout 0.05, ~72-unit vanilla RNN, features scaled 0–1. Report our number against theirs
*with the gap explained*. A reproduction that lands 20% off with a stated reason is a result; one that
lands on the nose with no explanation is usually a leak.

**Sprint 2:** train the speed + variance head on `S-` channels. The Gate 2 criterion is **calibration,
not accuracy** — ≥95% of errors inside ±2σ. Produce the predicted-σ-vs-realised-error plot. A head with
excellent RMSE and 60% coverage is a head that will damage the filter, and it is the failure mode that
ordinary accuracy metrics cannot see.

**Sprint 3:** adaptive `R_NHC` — the AI-IMU mechanism, ~6,210 parameters, Adam 1e-4, adapting the
**measurement** noise of the NHC pseudo-measurements (see §4A). This is the clearest differentiator
against other entries and it is cheap. It is also the first thing cut if Gate 2 slips.

### D — data & evaluation *(critical path today)*

**Today, in this order:**

1. **Download IO-VNBD.** Everything waits on this. Use the *Synchronised V and S* folder; record the
   choice, the source URL, the download date and per-file SHA-256 in `data/manifest/`. Do not commit
   dataset bytes.
2. **R-4** — pin the CTE/CRSE equations against the WhONet paper's own equation numbers; write them
   verbatim into [EVALUATION.md](EVALUATION.md) §4.2; confirm or flip `CrseConvention`.
3. **R-7** — get `pytest` installed and the suite green *on this machine*. CI green on Ubuntu is not
   evidence that the Windows dev box works, and Gate 0's two-machine reproduction cannot be run from
   one machine.
4. **R-6** — move the figure-regeneration criterion from Gate 0 to Gate 1.
5. Break the leakage guard on purpose, once, and watch it fail. A test that has never been seen to
   fail is not known to work.

**Sprint 1:** wire `eval/run.py` — the TODO at its centre is the last piece of harness. Load held-out
sequences, run the filter across each outage window, collect `OutageMetrics`, write stamped results and
figures. Then Gate 1's numbers come out of one command.

**Sprint 3:** the full sweep — every outage length, every scenario set, drift % as median **and** 95th
percentile, the four mandatory plots (V-St6, V-St7, V-S3a, plus a roundabout), yaw error alongside
position error on every one. **Leakage audit pass #2.**

### P — maps, and the baselines

Map matching is deferred, and the design work is already delivered — so seat P moves onto the critical
path where it is needed.

**Today:** **R-5** — transcribe D-034–D-037 from the Delhi Road Graph artifact into
[DECISION_LOG.md](DECISION_LOG.md). Drafts in §8; confirm the wording matches what was actually decided.

**Sprint 1:** own the **raw-strapdown INS baseline** and the **GNSS-available baseline**. Both are
pure harness work, neither needs the InEKF, and Gate 1 is defined as a ratio between them — so they
must exist *before* Gate 1, not alongside it. The strapdown baseline is also the "naive DR" trajectory
in every 4-trajectory figure and the number behind "176 m in 60 s" becoming a measurement instead of an
arithmetic example.

**Sprint 3:** support the sweep and the figures. Map matching stays written up as *design*, with §5 of
the Delhi Road Graph doc — the covariance-driven candidate radius spanning 18 m at 10 s to 359 m at
180 s — as the argument for why we are building a matcher rather than adopting one. That argument is
worth a slide even with no matcher running.

### A — demo

Android is deferred; the Allan run has moved off the critical path (R-1). Seat A's screening
deliverable is the **replay renderer** (§4C).

**Sprints 0–2:** stay out of the critical path. Optionally build the minimal foreground-service logger
— uncalibrated sensors, real timestamps, `HIGH_SAMPLING_RATE_SENSORS` — and **measure the actual
achieved sample rate and timestamp jitter on each team device**. The nominal rate is not the real rate,
and those two numbers are worth a slide in the deployment section whether or not the app ships.

**Sprint 3:** build the renderer against real harness output. It cannot start before the sweep
produces something, and it must not be given a simulator to fall back on.

### C — submission

**Today:** **confirm the 8 Sep cut-off time and the exact deliverable format on the portal.** Everything
is sized against this and it is still unverified. Apply R-9 (superseded banners). Then open
[METHOD.md](METHOD.md) and start filling §1–2 — with 12 days there is no final week, and a section
written the week it was built is a section written from memory that is still accurate.

**Throughout:** METHOD.md §3 onward as each piece lands. The raw material already exists —
DECISION_LOG supplies the *why*, ERROR_BUDGET supplies the analysis, EVALUATION supplies the protocol.

**Sprint 3:** deck and video. The deck's problem slide uses the Master Plan's audience framing (§4B).
Every number comes from `eval/figures/`. **Citation-hygiene check before submission:** no AI-IMU or
WhONet figure quoted as ours, both WhONet sequence counts reported with the inconsistency flagged by
us, and every plot caption naming its stream (`S-` or `V-`) and rate.

---

## 7. Gates

Unchanged in criteria. Only R-6 moves an item, and the dates now match this calendar.

### Gate 0 — Fri 28 Aug · *the harness is trustworthy*

- [ ] IO-VNBD downloaded; synchronised/unsynchronised choice logged; `data/manifest/` written with SHA-256s.
- [ ] Two machines, same commit, same seed → **byte-identical** metrics output.
- [ ] CTE/CRSE equations pinned to the paper and written verbatim into EVALUATION.md.
- [x] Leakage CI test passes **and is demonstrated to fail** on a deliberate `V-` column.
- [x] Train/test split fixed in code; no sequence on both sides.
- [ ] `pytest` green on the primary dev machine, not only in CI.
- [ ] [EVALUATION.md](EVALUATION.md) marked **FROZEN**.

*(Moved to Gate 1 by R-6: "one command regenerates every figure" — there are no figures yet.)*

### Gate 1 — Tue 1 Sep · *the spine holds without learning*

- [ ] Onyekpe INS baseline reproduced; our number vs theirs, with the gap explained.
- [ ] Raw-strapdown and GNSS-available baselines both produced by the harness.
- [ ] Physics-only InEKF within **3–5×** of GNSS-available over 60 s outages.
- [ ] `Q` from the IO-VNBD Allan run in use; measured numbers recorded in ERROR_BUDGET.md §9.
- [ ] SE₂(3) tests 7–11 pass, **including NEES consistency**.
- [ ] Yaw error instrumented and plotted separately.
- [ ] One command regenerates every figure *(moved from Gate 0)*.
- [ ] Leakage audit pass #1 complete.

### Gate 2 — Fri 4 Sep · *the speed head is honest about itself*

- [ ] ≥95% of speed errors inside ±2σ of the predicted variance.
- [ ] Calibration plot (predicted σ vs realised error) in the figure set.
- [ ] Speed head fused with its predicted `R`; end-to-end drift improves.

### Gate 3 — Mon 7 Sep · *submission ready, one day early*

- [ ] Full sweep across every outage length and scenario set.
- [ ] Mandatory plots: V-St6, V-St7, V-S3a + at least one roundabout, each as a 4-trajectory figure.
- [ ] Every figure stamped with commit + seed.
- [ ] Drift % reported as median **and** 95th percentile.
- [ ] Re-acquisition behaviour measured (§EVALUATION 6), not assumed.
- [ ] Leakage audit pass #2 complete.
- [ ] Replay renderer runs off harness output; stamp visible on the page.
- [ ] `core/ffi/` interface contract committed.
- [ ] Honest-limits section written, including everything deferred in §2C.
- [ ] Citation hygiene check passed.
- [ ] Deck, video, write-up.

---

## 8. Decisions this plan makes

To be appended to [DECISION_LOG.md](DECISION_LOG.md). D-034–D-037 are **transcriptions** of choices
already made by seat P on 26 Aug in the Delhi Road Graph artifact — seat P confirms the wording; the
gap in the log is R-5.

| ID | Date | Decision | Reason | Owner |
|---|---|---|---|---|
| D-034 | 2026-08-26 | The NCR extract merges **both** Geofabrik `northern-zone` and `central-zone` before clipping. | Verified by point-in-polygon against Geofabrik's published `.poly` boundaries: Delhi/Gurugram/Faridabad/Sonipat/Alwar are northern; Noida/Greater Noida/Ghaziabad/Meerut are central. The seam is the Yamuna, so a northern-only graph loses every eastern crossing — DND Flyway, Akshardham, Kalindi Kunj. A matcher whose graph ends mid-bridge does not degrade gracefully; it snaps to the nearest thing still in the graph. | P |
| D-035 | 2026-08-26 | Candidate search uses the **Mahalanobis distance against the filter's own `P_pos`**, not a scalar radius. | The 99% radius implied by our error budget runs from 18 m at a 10 s outage to 359 m at 180 s — a 20× span across outage lengths the protocol mandates. The terms are also anisotropic: at 60 s along-track error is 1.5× the combined lateral, and the ellipse rotates with heading. A scalar σ is a circle fitted to a rotating ellipse — simultaneously too permissive across the minor axis and too strict along the major one. `d_M² = δᵀP_pos⁻¹δ` costs one 2×2 solve per candidate. | P |
| D-036 | 2026-08-26 | **Build the HMM matcher over our own CSR graph; do not adopt a library.** | Every candidate library takes GPS accuracy as one scalar — Valhalla Meili precomputes `1/(2·σ_z²)` with `σ_z` defaulting to 4.07 m; FMM's `gps_error`, GraphHopper's `measurement_error_sigma` and Barefoot's `sigma` are the same shape. That is correct for raw GPS traces and wrong for a filtered pose whose covariance we compute. Adopting one means either discarding D-015/D-035 or patching someone else's core probability model. Viterbi over the CSR is ~200 lines, and the CSR is ours regardless because its mmap behaviour is what makes matching affordable on Android. | P |
| D-037 | 2026-08-26 | `highway=service` **is** included in the drivable graph, with highway class carried in a 4-bit edge flag as an emission prior. | Measured cost is +21% (57,922 service ways against 280,884 drivable), not the assumed 2×, so the memory objection collapses. Excluding forces a car genuinely on a service lane — one runs beside every Delhi arterial — onto the arterial. Including keeps it reachable but makes it out-argue a trunk road to win. | P |
| D-038 | 2026-08-27 | **`Q_c` is seeded from IO-VNBD's own >20 min stationary segments, not from a team phone.** Our phone's Allan run continues in parallel but is not Gate-1-blocking. | The graded numbers come from IO-VNBD, recorded on a Huawei P20 Pro / Moto G7 Power / BlackBerry Priv. Tuning process noise from a different device models a sensor that produces none of the evaluated data. 20 min at 10 Hz gives ARW cleanly at τ = 1 s and bias instability out to τ ≈ 100–200 s — the exact timescale of a 10–180 s outage. It also removes Android from the Gate 1 critical path. Supersedes the Sprint 0 seat-S/seat-A item in [SPRINT_BOARD.md](SPRINT_BOARD.md). | S |
| D-039 | 2026-08-27 | The screening demo is a **static replay renderer over harness output**. No FastAPI, no React, no WebSocket, no map SDK, and **no simulator**. | A live cockpit fed by its own scenario generator can display numbers the evaluation never produced — the failure the frozen protocol exists to prevent. Constraining the demo to render `eval/figures/` output makes a screenshot self-evidencing and costs ~1.5 days instead of ~3. Supersedes the entire frontend and `scenarios/` sections of the Master Implementation Plan. | A |
| D-040 | 2026-08-27 | The adaptive-covariance network adapts **`R_NHC` (measurement noise)**, never `Q` (process noise). | Brossard's AI-IMU CNN outputs the measurement-noise covariance of the NHC pseudo-measurements — how tightly to enforce "no sideways motion" at each step. The Master Implementation Plan attributes dynamic `Q_k` adaptation to the same paper, which it does not support. Implementing `Q_k` would be an unvalidated method carried by a citation that does not back it. Reaffirms and sharpens D-005. | M |
| D-041 | 2026-08-27 | **MapmyIndia/Mappls is not a screening dependency.** The offline OSM CSR graph (D-034–D-037) is the committed map path; any Indian map SDK is a post-screening rendering layer only. | An online SDK behind an API key cannot back a "100% offline" claim. Measured footprint for the offline path is ~21 MiB (Delhi bbox) / ~32 MiB (core NCR) with ~16 KiB resident over a 180 s transit, so there is no capability argument for the dependency either. | P |
| D-042 | 2026-08-27 | **No performance figure enters the deck, write-up or demo unless `eval/run.py` produced it** under the frozen protocol, stamped with commit and seed. | The Master Implementation Plan carries "RMSE < 1.0 m", ">95% drift reduction" and "<2 ms edge inference" as targets. Unbacked headline numbers are the cheapest way to lose an adversarial question, and they migrate from plan to slide silently. Extends D-018 from figures to every quoted number. | C |
| D-043 | 2026-08-27 | `core/ffi/` ships as an **interface definition** at screening — a header/trait file, not an implementation. | D-022 defers the C++/Rust port to October, but the PS asks for an edge-deployable engine and the argument rests on the architecture. A ~100-line interface both the Android build and the 200 Hz FOG build bind to converts a promise into an artefact for half a day of work, without reopening D-022's schedule reasoning. | S |

---

## 9. Risks, after consolidation

The first four are carried forward unchanged. The last three are new or changed as a result of this plan.

1. **Yaw drift eats the budget.** → ZARU at every detected stop, bias snapshot at tunnel entry,
   magnetometer as a weak prior only (cabin ferromagnetics), map-matching heading feedback as the outer
   loop. Instrument yaw error at every step.
2. **Wheel-speed leakage.** → Column allowlist + its own CI job, audited in Sprint 1 and again before
   submission. Break it on purpose once.
3. **Gate 1 fails and networks get stacked on a broken spine.** → Hard stop. Diagnose in the fixed order.
4. **Overconfident covariance head.** → Gate 2 measures calibration, not accuracy. FP16 only; INT8
   behind an explicit covariance-head degradation test (D-012).
5. **[NEW — highest] The dataset is not downloaded and every remaining task depends on it.** Four days
   of Sprint 0 and Sprint 1 work — Allan variance, baselines, harness wiring, the sign-convention check
   — sit behind one download that has not started. → It is the first item today. If IO-VNBD is slow or
   partially unavailable, say so by tonight, not on Saturday.
6. **[NEW] Sprint 0 has two days left and five open blocking items.** → If Gate 0 cannot close on Fri 28,
   close it Sat 29 and compress Sprint 1 to three days rather than freezing an unpinned protocol. A
   protocol frozen with the CRSE convention still unverified is not frozen; it is postponed.
7. **[CHANGED] Demo scope creep back toward the cockpit.** The Master Plan is attractive precisely
   because it is the visible half of the project, and it will keep being proposed. → D-039 is the
   answer, and the cut order in §5 is explicit: the renderer is cut before the sweep, and static
   matplotlib figures are an acceptable submission.

---

## 10. What we say about the limits

Written now, not at the end, because a limitation stated by us costs a fraction of what one found by a
judge costs.

- **Tunnels and underpasses (tens of seconds to ~1–2 min): the 10% target is achievable** with learned
  speed + NHC + ZUPT/ZARU + a continuously running filter, and comfortably so with map matching.
  Without map matching, expect to miss 10% occasionally on curved tunnels and roundabouts, where
  heading error and road curvature compound.
- **Multi-level underground car parks are the genuinely hard case and the least certain claim we make.**
  No road graph exists, dwell times are long, speeds are low and turns are frequent. The fallback is
  tight NHC + barometer floor detection (one level ≈ 2.5–3 m ≈ 0.3–0.36 hPa) + ramp detection from
  sustained pitch. **Drift may exceed 10% on a long stay.**
- **What we deferred and did not build for screening:** the online HMM map matcher, the Android app and
  JNI layer, car-park mode, comma2k19 pretraining, the Delhi/NCR collection and domain-shift ablation,
  and the C++/Rust port. Each is designed, and the map layer is sized to the megabyte. Saying so is
  better than shipping six half-finished components.
- **Sensor grade is the caveat on every borrowed number.** AI-IMU's 1.10% is KITTI's automotive-grade
  IMU. WhONet's ~0.15% needs wheel speed, which PS 26168 disallows. Neither is a phone-only result. Our
  reference point is the Onyekpe INS numbers, and we say that on the slide where the comparison appears.
- **The phone stream is 10 Hz.** We cannot demonstrate a 200 Hz pipeline on IO-VNBD and no caption will
  imply that we did.

---

*Consolidated 27 Aug 2026 from the engineering survey, the Master Implementation Plan, the seat-P
Delhi Road Graph study, and the repository as it stands at commit `77d5bf0`.*
