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

<!-- Add new rows below. Do not edit rows above. -->
