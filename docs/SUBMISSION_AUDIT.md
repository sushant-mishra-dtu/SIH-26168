# Submission audit

**Owner:** seat C · **Run:** 1 Sep 2026 · **Submission:** Tue 8 Sep 2026
**Rule for this document:** every line carries **evidence** — a file path, a test name, or pasted
command output. "Looks fine" is not evidence, and a gap is reported as a gap rather than closed by
softening the claim that exposed it.

> **Read item 0 first.** This audit is run seven days early and against an incomplete submission,
> because the one thing it cannot audit is the thing everything else depends on.

---

## 0. The blocker, stated once

**The IO-VNBD dataset is not fetchable in the environment this work was done in, so `eval/run.py`
has never run on real bytes and there are no evaluation results.**

Evidence: every CSV in `github.com/onyekpeu/IO-VNBD` is Git-LFS-tracked (`.gitattributes`:
`*.csv filter=lfs diff=lfs merge=lfs -text`); a shallow clone yields 134-byte pointer stubs; and the
LFS batch endpoint returns `access denied by the git proxy: onyekpeu/IO-VNBD is not in this
session's authorized repository set`. Recorded as D-059.

Consequences, all of which appear again below in their own rows:

- **Gate 1 is not measured** and no number substitutes for it (D-069).
- Under **H-4**, no learned component may be added until Gate 1 closes — so P-08 (speed head
  training), P-09 (fusing it) and P-10 (adaptive `R_NHC`) have not been started.
- P-12's sweep, every mandatory figure, and the results section of the write-up are empty.
- **R-8** — the accelerometer sign convention — is unresolved, and it invalidates a Gate 1 result if
  skipped.

None of this needs further code. It needs a machine that can fetch the files.

---

## 1. Every quoted number traces to a stamped artefact (D-042)

**Partially met, and the exceptions are enumerated rather than glossed.**

[METHOD.md](METHOD.md) §0 tags every quantity in the write-up with its provenance, in four classes:

| Class | Status | Evidence |
|---|---|---|
| **[evaluated]** — from `eval/run.py` under the frozen protocol | **None exist.** §12 of METHOD.md says so in its first line and leaves the section empty. | item 0 |
| **[measured]** — from `eval/allan.py` on real IO-VNBD bytes | Stamped, clean. | `eval/figures/allan_{stamp,summary}.json` → `commit ef10dcc`, `seed 26168`, no `-dirty` suffix |
| **[verified]** — a property of our code asserted in CI | Each cites its test by name in METHOD.md. | e.g. `tests/test_baselines.py::test_ten_milli_g_of_accel_bias_costs_the_176_m_the_budget_says` |
| **[analysis]** — closed-form arithmetic from stated inputs | Each re-derivable from [ERROR_BUDGET.md](ERROR_BUDGET.md). Checked: `½·0.0098·3600 = 176.52`; `½·(0.1°/s)·16.7·3600 = 52.46`; `5°·16.7·60 = 87.44`. | ERROR_BUDGET §2, §3, §5 |

**The distinction is the finding.** D-042 was written about performance figures, and the write-up
also needs to quote sensor characterisation, code properties and closed-form analysis. Collapsing
them all into "stamped or not" would have forced either dropping the derivation or presenting a
NEES figure as though the harness produced it. The four-way tag is how that is avoided, and it means
**a reader can tell at a glance that no performance claim is being made.**

---

## 2. No artefact carries a `-dirty` stamp

**Met, for the artefacts that exist.**

```
$ for f in eval/figures/*.json; do ...; done
eval/figures/allan_stamp.json: ef10dcc
eval/figures/allan_summary.json: ef10dcc
```

Neither carries `-dirty`. `eval/figures/allan_{curve,coefficients,segments}.csv` carry the same
stamp on their first line as a `#` comment.

**Note for the run that produces results:** `eval/run.py` prints a warning to stderr and sets
`"reproducible": false` in `summary.json` when `git status --porcelain` is non-empty, and the replay
page renders `— NOT REPRODUCIBLE` beside the stamp for such a record
(`tests/test_replay.py::test_the_stamp_is_rendered_on_the_page_and_a_dirty_run_is_marked`). The
sweep must be run from a clean tree.

---

## 3. Leakage audit, pass #2

**Met.** Two allowlists, two separate audits, both pasted.

```
$ pytest tests/test_leakage.py -q
............................                                             [100%]
28 passed in 0.27s

$ python -c "<the CI job's rejection check>"
OK  rejected 'Wheel Speed FL (rad/s)'
OK  rejected 'V-wheel_speed_rr'
OK  rejected 'Steering Angle (deg)'
leakage guard verified

$ python -c "<the same, against the ground-truth allowlist>"
OK  truth path rejected 'velocity (km/h)'
OK  truth path rejected 'Heading (deg)'
OK  truth path rejected 'Wheel Speed FL (rad/s)'
```

The rejection check is a **separate CI job** (`.github/workflows/ci.yml`, `leakage-audit`), not a
line inside a longer test log, so it reads as a distinct gate in the PR checks. A guard never
observed to fire is not known to work.

**The second allowlist matters as much as the first.** `eval/loaders/truth.py` is the one sanctioned
path into the `V-` stream, and it permits latitude, longitude and time of day and nothing else — no
velocity, no heading. Its columns are selected from the header *before* the body is read, so a
banned channel is never materialised, and `TruthTrack` is deliberately not a `Sequence`, so it has
no `features()` and the type system prevents it reaching a model.

**Caveat, honestly:** pass #2 is supposed to run over the feature path an actual sweep used. No
sweep has run (item 0), so what is audited here is the guard and the loaders, not a live feature
tensor. **This row is not fully closed and must be re-run after the first real sweep.**

---

## 4. Yaw error appears on every figure that shows position error

**Met by construction; unverifiable on real figures, because there are none.**

- `OutageMetrics` has no optional fields: `yaw_rmse_rad` and `yaw_max_rad` are emitted for every
  window, so a result without yaw cannot be constructed.
- `windows.csv` carries `yaw_rmse_deg` and `yaw_max_deg` on every row
  (`tests/test_replay.py` and `tests/test_harness_wiring.py::test_artefacts_carry_the_stamp_...`
  assert the column is present).
- The replay page shows yaw error in its per-epoch readout and plots it beside drift-% on the same
  axes (`tests/test_replay.py::test_all_four_trajectories_and_the_ellipse_are_drawn` and the
  readout assertions).

**A caveat that belongs in every caption, not just here (D-063):** the truth track carries lat, lon
and time of day and *no heading channel*, so both sides of every yaw comparison are course made good
over each epoch. The filter's own attitude estimate is **not** what its yaw error is measured
against. Those differ exactly when the vehicle's velocity is not along its heading — which is what
NHC asserts does not happen.

---

## 5. Drift % is reported as median **and** p95

**Met.** `eval.metrics.core.summarise` returns `drift_pct_median`, `drift_pct_p95`,
`drift_pct_max` and `frac_under_10pct`, and there is no code path that reports a mean.
`eval.run.summarise_by_method_and_length` groups by method **and** outage length before summarising,
so a single pooled figure cannot be produced by accident.

---

## 6. Gate checkboxes

| Gate | Status | Evidence |
|---|---|---|
| **Gate 0** — the harness is trustworthy | **NOT CLOSED.** CRSE pinned (D-054); the split re-pick after D-044 and the GNSS-cadence consequences are open; [EVALUATION.md](EVALUATION.md) is still marked DRAFT. | README status block; D-044's "Open:" clause |
| **Gate 1** — physics-only within 3–5× of GNSS-available at 60 s | **NOT MEASURED.** The harness computes and reports the ratio; it has never been run on data. | item 0; D-069; `eval.run.gate1_ratio` |
| **Gate 2** — ≥95% of speed errors inside ±2σ | **NOT STARTED**, blocked by H-4 behind Gate 1. | METHOD.md §5 |
| **Gate 3** — submission ready | **NOT MET.** Items 1, 3, 4 and 7 below are open. | this document |

**Filter consistency, which blocked Gate 1 as of 31 Aug, is resolved.** Full-state NEES went 29.90
(over-confident) → 14.14 (under-confident, the safe direction), and the sub-cases are asserted
two-sided in CI: propagation 18.29, +ZUPT 18.93, +ZARU 17.03, ZUPT+ZARU 19.03, all inside
[16.84, 19.19] (`tests/test_se23_derivation.py` test 11). **D-053's diagnosis of that failure was
wrong**, and D-057 records both the correction and how the wrong one survived: it was reasoned about
rather than measured.

---

## 7. The honest-limits section covers everything deferred

**Met.** [METHOD.md](METHOD.md) §13 carries a table of seven deferred items — the HMM matcher, the
Android app and JNI, car-park mode, comma2k19 pretraining, the Delhi/NCR collection and
domain-shift ablation, the C++/Rust port, and the two untrained learned components — which is the
whole of the plan's §2C deferred list, plus the Onyekpe reproduction.

It also carries **one remaining gap rather than a deferral**: the reference offline
mount-disturbance detector's 10 Hz blind spot (D-075), noting that the on-device operator UI
solves this directly via rotation-matrix tilt rate. Two items listed earlier have since closed:
the accelerometer sign convention (R-8 / D-059 closed by D-085 with real stationary measurements)
and Gate 0 being open (closed by D-092 and D-103).

§13 leads with the car-park case as the least certain claim, states that drift may exceed 10% there,
and says plainly that the phone stream is 10 Hz and that the 200 Hz FOG pipeline is an architecture
claim backed by measured throughput headroom rather than a demonstrated pipeline.

---

## 8. Citation hygiene

**Met.** [METHOD.md](METHOD.md) §14 checks each line:

- AI-IMU's **1.10%** — KITTI, automotive-grade IMU. Never ours; we take the mechanism, not the
  number.
- WhONet's **~0.15%** — needs wheel speed, which PS 26168 disallows. A ceiling.
- **Onyekpe's INS models** are our honest reference point.
- Pedestrian ATE (RoNIN, TLIO, RIDI, IONet, IDOL, CTIN) ranks architectures and does not predict car
  performance.
- 2025–26 preprints are treated as provisional.
- **"QGRU from the IO-VNBD paper" does not exist** — IO-VNBD is a dataset paper.
- **We flag WhONet's own internal inconsistency ourselves**: 809/399/197/129 sequence counts in the
  introduction against 688/342/168/111 in the tables, and an identical 120 s CTE reported for both
  methods. We cite the tables.
- §14.1 states that **nine of the reproduction's eighteen hyperparameters are ours, not the
  papers'**, and that the INS paper does not surface its loss or optimiser.

---

## 9. The deferred list matches what is actually absent from the repo

**Met.** Checked item by item against the tree:

| Claimed deferred | Actually absent? |
|---|---|
| Online HMM matcher | `maps/` holds no matcher. ✔ |
| Android logger / demo app / JNI | `android/` is empty. ✔ |
| Car-park mode | No barometer or ramp-detection code. ✔ |
| comma2k19 pretraining | No loader, no manifest row. ✔ |
| Delhi/NCR collection | No data, no manifest row. ✔ |
| C++/Rust port | `core/filter/` and `core/constraints/` hold only `.gitkeep`; `core/ffi/` holds a header with no implementation. ✔ |
| Speed head **trained** | `models/speed_head.py` has the architecture; no weights, and `InEKF.update_speed` raises `NotImplementedError`. ✔ |
| Adaptive `R_NHC` | No such model. `update_nhc(r_nhc=...)` accepts one and nothing supplies it. ✔ |
| Onyekpe baseline **trained** | `models/train_baseline_rnn.py` raises rather than training. ✔ |

**The converse also holds**, which is the direction more often wrong: nothing claimed as built is
absent. Every row of the README's "what is built" table names either a module with tests or an
explicit not-started.

---

## 10. Portal cut-off time and deliverable format

**NOT CONFIRMED. Unchanged since 27 Aug, and it is not something this repository can establish.**

Everything is sized against a midday 8 Sep submission with the buffer being the morning. Seat C owns
confirming the portal's actual cut-off and the required deliverable format. **This is the cheapest
open item on the list and the only one that can invalidate the schedule rather than a number.**

---

## Summary

| # | Item | Status |
|---|---|---|
| 0 | Dataset reachable | **BLOCKED** |
| 1 | Numbers trace to stamped artefacts | Met, with the classes enumerated; no performance claim is made |
| 2 | No `-dirty` artefact | Met |
| 3 | Leakage audit pass #2 | Guard verified; **not yet run over a live feature path** |
| 4 | Yaw on every figure | Met by construction; no figures yet |
| 5 | Drift median and p95 | Met |
| 6 | Gates 0–3 | 0 open · 1 unmeasured · 2 not started · 3 not met |
| 7 | Honest limits complete | Met, plus three newly-found gaps |
| 8 | Citation hygiene | Met |
| 9 | Deferred list matches the tree | Met, both directions |
| 10 | Portal cut-off confirmed | **NOT CONFIRMED** |

**The submission as it stands is a defensible engineering artefact with no performance claim.** That
is a worse submission than one with a measured Gate 1 and a better one than any version of this that
quotes a number nobody can regenerate.
