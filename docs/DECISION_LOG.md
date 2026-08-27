# Decision Log

**Append-only.** One row per non-obvious choice, with its reason.

Rules:

1. **Never edit or delete a past row.** If a decision changes, add a new row that supersedes it and
   mark the old one `superseded by D-0NN`. The record of what we believed and when is the point.
2. Every row needs a **reason**, not just a choice. "Because it's better" is not a reason.
3. If a decision invalidates existing results, say which ones in the row.
4. Add the row **when you make the choice**, not when you remember to. This file writes half the
   method document; that only works if it is written contemporaneously.

Owner tags: **S** filter core · **M** learning · **D** data/eval · **P** maps · **A** Android · **C** submission.

---

## Seeded from the plan of record (26 Aug 2026)

These predate the repo. They are recorded here so the method write-up has a source, and so that
anyone who wants to revisit one can see what it was trading against.

| ID | Date | Decision | Reason | Owner |
|---|---|---|---|---|
| D-001 | 2026-08-26 | One continuously-running filter; GNSS is an optional gated correction. No second system, no handoff. | "Seamless transition within milliseconds" becomes true by construction. Two-system designs show a visible position jump on every tunnel entry. | S |
| D-002 | 2026-08-26 | Invariant EKF with state on SE₂(3) + biases, rather than a naive EKF. | Group-affine dynamics make the error linearisation state-independent: consistent covariance (no false yaw observability) and a large convergence basin from a badly wrong initial attitude — exactly the arbitrary-mount case. | S |
| D-003 | 2026-08-26 | Forward speed comes from a learned head. Acceleration is **never** double-integrated. | 10 mg of accel bias is ≈176 m of error in 60 s — 176% of the budget from one term. See [ERROR_BUDGET.md](ERROR_BUDGET.md) §2. | M |
| D-004 | 2026-08-26 | NHC + ZUPT + ZARU as always-on gated pseudo-measurements. | Cars do not slide sideways or fly; stopped cars have zero velocity and zero angular rate. ZARU is the primary means of observing gyro bias, the dominant error term. | S |
| D-005 | 2026-08-26 | Learned adaptive R_NHC (AI-IMU mechanism, ~6k params) rather than a fixed R. | The constraint must relax during hard cornering and tighten on straights. This is the mechanism behind the strongest published car result (1.10% on KITTI) and it is cheap. | M |
| D-006 | 2026-08-26 | Phone→vehicle rotation R_sv lives **in the filter state**; PCA on horizontal acceleration is an initialiser only. | One-shot alignment is fragile and cannot track a mount that shifts. Under NHC, R_sv is observable through turns and accelerations. Budget requires ~1° yaw accuracy ([ERROR_BUDGET.md](ERROR_BUDGET.md) §5). | S |
| D-007 | 2026-08-26 | IO-VNBD `S-` smartphone channels only. `V-` wheel-speed columns banned, enforced by a CI test. | Wheel odometry is disallowed by PS 26168. The columns sit in the same dataset and are trivially easy to leak in by accident. | D |
| D-008 | 2026-08-26 | Metrics are CTE (Cumulative True Error) and CRSE (Cumulative Root Square Error) per Onyekpe's definitions, **plus** drift as % of distance. | The task brief mislabels CTE/CRSE as cross-track error / ATE. Drift % is what PS 26168 actually grades, and no paper in this line reports it — we must compute it ourselves. | D |
| D-009 | 2026-08-26 | The evaluation harness is frozen before any model trains. | A protocol that can move will be moved, one justified step at a time, until the numbers flatter us and mean nothing. | D |
| D-010 | 2026-08-26 | Gate 1 (physics-only InEKF within 3–5× of the GNSS-available baseline) is a **hard stop** before any network is added. | Stacking learned components on a broken spine produces a system nobody can debug and numbers nobody can defend. | S |
| D-011 | 2026-08-26 | One C++/Rust core, two frontends: JNI to Android, and the identical library as the 200 Hz FOG edge engine. | Satisfies the "edge deployable engine" requirement by construction instead of as a second project. Avoids two divergent implementations of the filter. | S |
| D-012 | 2026-08-26 | Export FP16. INT8 only behind an explicit covariance-head degradation test. | A mis-scaled covariance corrupts a Kalman filter worse than a slightly noisy mean. Quantisation error on the variance output is not visible in ordinary accuracy metrics. | M |
| D-013 | 2026-08-26 | Android: `*_UNCALIBRATED` sensor types, foreground service, real timestamps, `HIGH_SAMPLING_RATE_SENSORS`. | Calibrated types silently subtract an OS bias estimate that the filter is also estimating, and the two fight. Since Android 9 there are no background sensor events; since API 31 the rate caps at 200 Hz without the permission. | A |
| D-014 | 2026-08-26 | NavIC is a bonus, not a dependency. Rely on GPS + GLONASS + Galileo + BeiDou. | Hardware support exists on several chipsets, but 2026 work finds NavIC signals often filtered out by low-level drivers, and Android's GNSS API lacks standardised NavIC identifiers. | A |
| D-015 | 2026-08-26 | Map matching is an online HMM over an offline OSM CSR graph, with emission σ driven by the filter's own covariance. | Feeding a filtered track into a matcher tuned for raw-GPS noise wastes the covariance we already compute. Sliding-window Viterbi commits segments older than ~5–10 s. | P |
| D-016 | 2026-08-26 | Car parks are a **separate mode**: tight NHC + barometer floor detection + ramp detection. Limitation stated honestly in the submission. | No road graph exists underground, so map matching is unavailable. This is the least certain claim we make and it is better said by us than found by a judge. | P |
| D-017 | 2026-08-26 | No pedestrian-network **weights** are reused (RoNIN, IONet, RIDI, TLIO, IDOL, CTIN). Architectures and filter frameworks only. | They encode a 0.5–2 m/s gait prior. A car at 16.7 m/s is off-distribution and they under-predict badly. | M |
| D-018 | 2026-08-26 | Every plot and table is stamped with the commit SHA and seed that produced it. | A result whose provenance is unknown cannot be defended or reproduced, and will be deleted rather than debugged. | D |

---

## Sprint 0 onward

| ID | Date | Decision | Reason | Owner |
|---|---|---|---|---|
| D-019 | 2026-08-26 | Repo root is the existing project folder; `AGENTS.md` and the two source documents stay at the root beside the scaffold. | Keeps the plan of record and its sources adjacent to the code rather than one directory up from it. | S |
| D-020 | 2026-08-26 | Default branch is `main`. | Convention; CI templates assume it. | S |
| D-021 | 2026-08-26 | **Deadline is Tue 8 Sep 2026, not Sat 20 Sep.** Sprint plan compressed from 25 days to 13. | Confirmed real portal cut-off. The AGENTS.md plan put Sprints 2 and 3 entirely *after* the actual deadline; 20 Sep is also a Sunday, not a Saturday. Supersedes the calendar in AGENTS.md — that file's sprint table is now stale and [SPRINT_BOARD.md](SPRINT_BOARD.md) is authoritative. | C |
| D-022 | 2026-08-26 | Screening filter is the **Python reference** in `core/reference/`; the C++/Rust port moves to post-screening (Oct). | D-011 (one core, two frontends) is unchanged as an architecture decision — only its timing moves. Writing the InEKF in C++/Rust before Gate 1 inside 13 days is the schedule risk most likely to sink the submission. Screening is graded on drift %, plots and method, not implementation language, and the edge-engine argument rests on the architecture rather than the language. | S |
| D-023 | 2026-08-26 | CRSE defaults to `SUM_SQUARES` = √(Σeᵢ²) rather than RMS, behind a `CrseConvention` enum. | Our definition source is a secondary summary. Consistency check against WhONet's 180 s baseline (CTE 2.90 m, CRSE 13.67 m, ~180 epochs) favours SUM_SQUARES: it implies ~1.0 m typical per-epoch error, where RMS would imply 13.67 m per epoch against a 2.90 m signed sum. **Reasoned, not verified** — seat D pins it against the paper's equations before Gate 0. | D |
| D-024 | 2026-08-26 | Torch is an optional extra; the harness and its CI run without it. | The harness is the critical path. Blocking Gate 0 on a 2 GB download, on a teammate's machine or in CI, trades days for nothing. | D |
| D-025 | 2026-08-26 | Unimplemented filter methods raise `NotImplementedError` rather than returning zeros. | A stub returning `None`/zeros lets the harness produce plausible all-zero trajectories and report them as results. Failing loudly is the only safe placeholder in a numerical pipeline. | S |
| D-026 | 2026-08-26 | NHC gating thresholds set conservatively: min speed 1 m/s, max yaw rate 0.6 rad/s, max lateral accel 4 m/s². | A missed NHC application costs a little accuracy; a false one during a slip injects a confident wrong measurement the filter believes. Asymmetric cost, so bias toward not applying. Revisit at Gate 1 against measured dynamics. | S |
| D-027 | 2026-08-26 | Predicted speed variance is floored at 1e-4 and the head regresses **log**-variance. | An unclamped variance head can output ~0 and hand the filter an infinitely-trusted measurement, driving the covariance singular in one step. Log-space keeps the output unconstrained and the loss well-conditioned. | M |

| D-028 | 2026-08-26 | The filter carries the **right-invariant** error `η = X̂X⁻¹`. GNSS, which is a left-invariant observation, is applied through the adjoint rather than the covariance being carried in its convention. | The always-on measurement family — NHC, ZUPT, ZARU, learned speed — is body-frame, which pairs with the right-invariant error; GNSS is optional and χ²-gated (D-001) and absent for the 10–180 s windows we are graded on. Verified consequence: the body-frame velocity Jacobian has an **exactly zero attitude column**, so the filter cannot acquire the spurious yaw observability that makes a naive EKF inconsistent. Right-invariant attitude error is also world-frame, which is the convergence-basin claim in D-002. | S |
| D-029 | 2026-08-26 | Nominal propagation uses the exact Γ₀/Γ₁/Γ₂ closed form, not a first-order Euler step; and `A_RI` is evaluated at the step **midpoint**. | At 10 Hz and 0.6 rad/s the Γ₁ correction is ~3% of the velocity increment and is rotation-direction-dependent, so it does not average out over the 1800 steps of a 180 s outage — it is a systematic heading-correlated drift, the error class the budget has no room for. Midpoint evaluation of `A` measured ~1800× lower linearisation residual at Δt = 1 ms. Both cost a handful of flops. | S |
| D-030 | 2026-08-26 | Mount-error perturbation convention is `R̂_sv = Exp(ξ_sv) R_sv` (vehicle-frame, left multiplication). | Makes `ξ_sv,z` literally mount-yaw error in the vehicle frame, so its covariance diagonal is directly comparable to the ~1° requirement in [ERROR_BUDGET.md](ERROR_BUDGET.md) §5 without a change of basis. A right-multiplied convention would have needed a rotation applied every time the budget was checked, which is a step someone eventually skips. | S |
| D-031 | 2026-08-26 | Discrete process noise `Q_d` by Van Loan matrix-exponential, not the `Φ G Q_c Gᵀ Φᵀ Δt` approximation. | Measured 4.2% error at Δt = 0.1 s with our own `FilterConfig` noise values. It mis-allocates noise between the position and velocity blocks, and an under-sized Q makes the filter reject good measurements at the χ² gate — a failure that looks like a sensor problem, not a tuning problem. Cost is one 36×36 `expm` per step, affordable in the Python reference; the October C++ port must validate any cheaper closed form against it. | S |
| D-032 | 2026-08-26 | Small-angle cutoff for the Γ functions is **1e-3**, not the 1e-6 first written down. | The guard must sit where the closed form is still accurate, not where it divides by zero. Sweeping the exact identities `Γ₀ = I + φ^∧Γ₁` / `Γ₁ = I + φ^∧Γ₂` puts the worst residual at φ ≈ 1.2e-6 — inside the branch a 1e-6 cutoff sends to the closed form, where `φ²+2cosφ−2` keeps almost no significant figures. Found by writing the test, not by reading the formula. | S |
| D-033 | 2026-08-26 | The SE₂(3) derivation is checked in CI ([tests/test_se23_derivation.py](../tests/test_se23_derivation.py)) against numerical ground truth, before the filter that uses it exists. | A wrong matrix on paper becomes a filter that runs, produces smooth plausible trajectories, and is undebuggable — and Gate 1 is a hard stop with no retry. Three corrections (D-029 midpoint, D-031 magnitude, D-032 cutoff) came out of writing the checks rather than out of reading the algebra, which is the argument for doing it in this order. | S |

---

## Seat P — transcribed 27 Aug 2026 from the Delhi Road Graph study (26 Aug)

These four were decided on 26 Aug and cited by ID in the seat-P artifact, but never reached this
file. Transcribed here so the record is complete; seat P confirms the wording. The gap itself is
logged as R-5 in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §2B.

| ID | Date | Decision | Reason | Owner |
|---|---|---|---|---|
| D-034 | 2026-08-26 | The NCR extract merges **both** Geofabrik `northern-zone` and `central-zone` before clipping. | Verified by point-in-polygon against Geofabrik's published `.poly` boundaries: Delhi, Gurugram, Faridabad, Sonipat and Alwar are northern; Noida, Greater Noida, Ghaziabad and Meerut are central. The seam is the Yamuna, so a northern-only graph loses every eastern crossing — DND Flyway, Akshardham, Kalindi Kunj — and the whole Noida–Ghaziabad side. A matcher whose graph ends mid-bridge does not degrade gracefully; it snaps to the nearest thing still in the graph. | P |
| D-035 | 2026-08-26 | Candidate search uses the **Mahalanobis distance against the filter's own `P_pos`**, not a scalar radius. | The 99% radius implied by our error budget runs from 18 m at a 10 s outage to 359 m at 180 s — a 20× span across the outage lengths the protocol mandates. Set it for 180 s and every parallel service road and flyover deck within 360 m enters the candidate set at 10 s; set it for 10 s and the true road is absent at 180 s. The terms are also anisotropic — at 60 s along-track error is 1.5× the combined lateral, and the ellipse rotates with heading — so a scalar σ is a circle fitted to a rotating ellipse. `d_M² = δᵀ P_pos⁻¹ δ` costs one 2×2 solve per candidate and is simply the correct quantity. | P |
| D-036 | 2026-08-26 | **Build the HMM matcher over our own CSR graph; do not adopt a library.** | Every candidate library takes GPS accuracy as one scalar — Valhalla Meili precomputes `1/(2·σ_z²)` with `σ_z` defaulting to 4.07 m, and FMM's `gps_error`, GraphHopper's `measurement_error_sigma` and Barefoot's `sigma` are the same shape. That is the right model for raw GPS traces and the wrong one for a filtered pose whose covariance we compute. Adopting one means either discarding D-015/D-035 or patching someone else's core probability model. Viterbi over the CSR is ~200 lines, and the CSR is ours regardless, because its mmap behaviour is what makes matching affordable on Android. | P |
| D-037 | 2026-08-26 | `highway=service` **is** included in the drivable graph, with highway class carried in a 4-bit edge flag as an emission prior. | Measured cost is +21% (57,922 service ways against 280,884 drivable), not the assumed 2×, so the memory objection collapses. Excluding forces a car genuinely on a service lane — one runs beside every Delhi arterial — onto the arterial. Including keeps it reachable but makes it out-argue a trunk road to win. | P |

---

## Consolidation — 27 Aug 2026

Arising from [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), which supersedes the sprint calendars
in AGENTS.md and SPRINT_BOARD.md and the standalone *Master Implementation Plan — SIH26168 (ISRO)*
document in its entirety.

| ID | Date | Decision | Reason | Owner |
|---|---|---|---|---|
| D-038 | 2026-08-27 | **`Q_c` is seeded from IO-VNBD's own >20 min stationary segments, not from a team phone.** Our own phone's Allan run continues in parallel but is no longer Gate-1-blocking. | The graded numbers come from IO-VNBD, recorded on a Huawei P20 Pro / Moto G7 Power / BlackBerry Priv. Tuning process noise from a different device models a sensor that produces none of the evaluated data. 20 min at 10 Hz gives ARW cleanly at τ = 1 s and bias instability out to τ ≈ 100–200 s — the exact timescale of a 10–180 s outage. It also removes Android from the Gate 1 critical path. Supersedes the Sprint 0 seat-S and seat-A Allan items in [SPRINT_BOARD.md](SPRINT_BOARD.md). | S |
| D-039 | 2026-08-27 | The screening demo is a **static replay renderer over harness output**: no FastAPI, no React, no WebSocket, no map SDK, and **no simulator**. | A live cockpit fed by its own scenario generator can display numbers the evaluation never produced — the failure the frozen protocol exists to prevent. Constraining the demo to render `eval/figures/` output makes a screenshot self-evidencing and costs ~1.5 days instead of ~3. Supersedes the entire frontend and `scenarios/` sections of the Master Implementation Plan. | A |
| D-040 | 2026-08-27 | The adaptive-covariance network adapts **`R_NHC` (measurement noise)**, never `Q` (process noise). | Brossard's AI-IMU CNN outputs the measurement-noise covariance of the NHC pseudo-measurements — how tightly to enforce "no sideways motion" at each step. The Master Implementation Plan attributes dynamic `Q_k` adaptation to the same paper, which does not support it. Implementing `Q_k` would be an unvalidated method carried by a citation that does not back it. Reaffirms and sharpens D-005. | M |
| D-041 | 2026-08-27 | **MapmyIndia/Mappls is not a screening dependency.** The offline OSM CSR graph (D-034–D-037) is the committed map path; any Indian map SDK is a post-screening rendering layer only. | An online SDK behind an API key cannot back a "100% offline" claim. Measured footprint for the offline path is ~21 MiB (Delhi bbox) / ~32 MiB (core NCR) with ~16 KiB resident over a 180 s transit, so there is no capability argument for the dependency either. | P |
| D-042 | 2026-08-27 | **No performance figure enters the deck, write-up or demo unless `eval/run.py` produced it** under the frozen protocol, stamped with commit and seed. | The Master Implementation Plan carries "RMSE < 1.0 m", ">95% drift reduction" and "<2 ms edge inference" as targets. Unbacked headline numbers are the cheapest way to lose an adversarial question, and they migrate from plan to slide silently. Extends D-018 from figures to every quoted number. | C |
| D-043 | 2026-08-27 | `core/ffi/` ships as an **interface definition** at screening — a header/trait file, not an implementation. | D-022 defers the C++/Rust port to October, but PS 26168 asks for an edge-deployable engine and the argument rests on the architecture. A ~100-line interface that both the Android build and the 200 Hz FOG build bind to converts a promise into an artefact for half a day of work, without reopening D-022's schedule reasoning. | S |

<!-- Add new rows below. Do not edit rows above. -->
