# Sprint Board

**Today: Wed 26 Aug 2026 — Sprint 0, day 1.**
**Screening submission: Tue 8 Sep 2026 — 13 days out.**

> **Schedule correction, 26 Aug 2026.** AGENTS.md targets Sat 20 Sep. The real portal cut-off is
> **Tue 8 Sep** — twelve days earlier, and 20 Sep is a Sunday in any case. The four-sprint plan in
> AGENTS.md put Sprints 2 and 3 entirely *after* the actual deadline. Everything below is the
> compressed replan. See DECISION_LOG D-021.

---

## Sprint calendar — compressed

| Sprint | Dates | Days | Focus | Gate |
|---|---|---|---|---|
| **0** | Wed 26 – Fri 28 Aug | 3 | Harness, metrics, leakage guard, CI | **G0:** reproduces to the digit across two machines |
| **1** | Sat 29 Aug – Tue 1 Sep | 4 | Onyekpe baseline + physics-only InEKF, Q from Allan variance | **G1:** within 3–5× of GNSS-available over 60 s. **Hard stop.** |
| **2** | Wed 2 – Fri 4 Sep | 3 | Speed+variance head fused as a pseudo-measurement | **G2:** ≥95% of speed errors inside ±2σ |
| **3** | Sat 5 – Mon 7 Sep | 3 | Adaptive R_NHC, full eval sweep, plots, write-up, deck, video | — |
| **Submit** | **Tue 8 Sep** | — | Submit by midday, not at the cut-off | **G3** |

---

## What 13 days actually buys

The original plan assumed 25 days. It does not survive the compression intact, and pretending
otherwise is how a team arrives on 7 September with six half-finished components and no numbers.

**In scope — the screening deliverable:**
harness · leakage audit · physics-only InEKF · learned speed+variance head · full evaluation sweep ·
write-up, deck, video.

**Probably in:** AI-IMU adaptive R_NHC. It is ~6k parameters, it is the mechanism with the
strongest published car result, and it is the clearest differentiator against other entries.

**Deferred to post-screening — say so in the write-up rather than shipping them half-built:**

| Deferred | Why it is survivable |
|---|---|
| Online HMM map matching | The write-up presents it as the designed outer layer with the covariance-driven emission model. A judge can follow the argument without a running matcher. |
| Android app + JNI | The core is the deliverable; the app is the demo. A recorded walkthrough of filter output covers it. |
| Car-park mode | Already the honest-limits case. Deferring it is consistent with saying it is hardest. |
| comma2k19 pretraining | First on the original cut list. IO-VNBD alone is the mandated dataset. |
| Delhi/NCR collection + domain-shift ablation | Highest-value *optional* item. Do it only if Gate 2 clears early. |
| C++/Rust core port | See below. |

### Recommended: prototype the filter in Python, port after screening

DECISION_LOG D-011 commits to one C++/Rust core feeding both Android and the FOG edge build. That
decision is still right — but *writing* it in C++/Rust inside 13 days, before Gate 1, is the
schedule risk that would sink the submission. `core/reference/` holds a Python InEKF whose
interface the compiled core mirrors exactly and whose tests it reuses.

The screening round is graded on drift %, plots and method, not on implementation language. The
edge-engine story is made by the *architecture* — one filter, one interface, swappable NN module —
and that argument is unchanged by which language the screening prototype ran in. Port in October,
when the FOG hardware and the Grand Finale timeline both justify it.

**Never cut:** the evaluation harness, the leakage audit, the yaw instrument, the honest-limits
section of the write-up.

---

## Sprint 0 — by seat · Wed 26 – Fri 28 Aug

The whole sprint builds the thing that measures us. Nothing trains this week, deliberately.

### D — Data & evaluation *(critical path — everything waits on this)*

- [x] `S-` dataloader with an explicit column allowlist; anything unlisted raises.
- [x] CI leakage test, **verified to reject** a `V-` column rather than merely passing.
- [x] CTE, CRSE, drift %, yaw error implemented, each unit-tested against a hand-computed case.
- [x] Outage injection: 10/30/60/120/180 s, non-overlapping, held-out only, 1 s cadence.
- [x] Train/test split frozen **in code**.
- [x] Figure/table stamping: commit SHA + seed, with dirty trees flagged unreproducible.
- [ ] Download IO-VNBD; record source URL, date and per-file SHA-256 in `data/manifest/`.
- [ ] Decide synchronised vs unsynchronised folder; log it.
- [ ] **Pin the exact CTE/CRSE equations against the WhONet paper's equation numbers.**
      Blocks the Gate 0 freeze. `CrseConvention` in `eval/metrics/core.py` defaults to
      `SUM_SQUARES` on a consistency argument; confirm or flip it.
- [ ] Verify byte-identical output on a second machine. **This is Gate 0.**

### S — Filter core

- [x] Repo scaffold, CI, package layout.
- [x] Constraint gating, χ² gate, stationary detection, mount-disturbance detection — tested.
- [x] Error-state layout fixed (18-vector) and the FFI-facing interface defined.
- [ ] **Start the multi-hour stationary log for Allan variance today** — it needs hours, and
      Gate 1's process noise depends on it.
- [ ] SE₂(3) propagation on paper before in code.
- [ ] Agree the `core/ffi/` interface contract with seat A.

### M — Learning

- [x] Speed head architecture (TCN, speed + log-variance, Gaussian NLL, calibration metric).
- [x] Onyekpe baseline architecture at the published hyperparameters.
- [ ] Read the Onyekpe INS paper; list every hyperparameter it actually states and every one it
      omits (epochs, and the INS paper's loss/optimizer) as choices to make and log.
- [ ] Training loop + dataloader wiring against seat D's harness. **No training until Gate 0.**

### P — Maps & geodata

- [ ] Pull a Geofabrik Delhi/NCR `.pbf`; measure the extract size filtered to drivable `highway=*`.
- [ ] Sketch the CSR layout and its memory footprint at city scale.
- [ ] Given the deferral above, timebox this to Sprint 0 and write it up as design, not code.

### A — Android

- [ ] Foreground-service logger skeleton: `*_UNCALIBRATED` accel + gyro, real timestamps,
      `HIGH_SAMPLING_RATE_SENSORS` declared.
- [ ] Measure actual achieved sample rate and timestamp jitter on each team device. Write the
      numbers down; the nominal rate is not the real rate.
- [ ] This feeds seat S's Allan-variance log — it is the highest-priority Android task.

### C — Field data & submission

- [ ] **Confirm the 8 Sep cut-off time and exact deliverable format on the portal.** Everything
      else is sized against this.
- [ ] Open [METHOD.md](METHOD.md) and start filling §1–2 now. With 13 days there is no week 4.
- [ ] Scout Delhi/NCR routes only if Gate 1 clears on time.

---

## Gate checklists

### Gate 0 — Fri 28 Aug · *the harness is trustworthy*

- [ ] Two machines, same commit, same seed → byte-identical metrics output.
- [ ] CTE/CRSE equations pinned to the paper and written verbatim into EVALUATION.md.
- [x] Leakage CI test passes **and is demonstrated to fail** on a deliberate `V-` column.
- [x] Train/test split fixed in code; no sequence on both sides.
- [ ] One command regenerates every figure.
- [ ] [EVALUATION.md](EVALUATION.md) marked **FROZEN**.

A test that has never been seen to fail is not known to work. Break it on purpose once.

### Gate 1 — Tue 1 Sep · *the spine holds without learning*

- [ ] Onyekpe INS baseline reproduced; our number vs theirs, with the gap explained.
- [ ] Physics-only InEKF within **3–5×** of the GNSS-available baseline over 60 s outages.
- [ ] Allan-variance-derived Q in use; measured numbers recorded in [ERROR_BUDGET.md](ERROR_BUDGET.md).
- [ ] Yaw error instrumented and plotted separately.
- [ ] Leakage audit pass #1 complete.

**If this fails, stop.** Diagnose in order: timestamps → NHC gating conditions → process noise →
ZUPT thresholds. Do not add a network to a broken spine. At 13 days, a failed Gate 1 means
submitting the physics-only result honestly rather than a rushed learned one — that is a defensible
submission, and a broken hybrid is not.

### Gate 2 — Fri 4 Sep · *the speed head is honest about itself*

- [ ] ≥95% of speed errors inside ±2σ of the predicted variance.
- [ ] Calibration plot (predicted σ vs realised error) in the figure set.
- [ ] Speed head fused with its predicted R; end-to-end drift improves.

A confident wrong covariance damages the filter more than a noisy mean. This gate is about the
variance output, not the speed output.

### Gate 3 — Mon 7 Sep · *submission ready, one day early*

- [ ] Full eval sweep across all outage lengths and scenario sets.
- [ ] Mandatory plots: V-St6, V-St7, V-S3a + at least one roundabout.
- [ ] Every figure stamped with commit + seed.
- [ ] Leakage audit pass #2 complete.
- [ ] Drift % reported as median **and** 95th percentile.
- [ ] Honest-limits section written — including everything deferred above.
- [ ] Citation hygiene check: no AI-IMU or WhONet number quoted as ours.
- [ ] Deck, video, write-up.

**Submit Tue 8 Sep by midday.** The buffer is the morning, not the deadline.

---

## After screening

SIH 2026 calendar: idea screening Sep–Oct, results Oct, mentoring and finalist announcement Nov,
Grand Finale Dec.

| Window | Focus |
|---|---|
| Sep–Oct | The deferred list: map matching, Android, car-park mode |
| Oct–Nov | Edge engine: port the core to C++/Rust, 200 Hz against a FOG-grade IMU, ONNX/TensorRT |
| Nov | Android hardening; thermal and battery budget over sustained drives |
| Nov–Dec | Adversarial rehearsal — where every number came from, what breaks, what would fix it |
