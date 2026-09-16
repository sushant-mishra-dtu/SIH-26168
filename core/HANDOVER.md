# Handover — Filter & Gate 1: where the number stands and what is left

**Written:** 15 Sep 2026, while the three D-115 fixes were being implemented (see §6); audited after they
landed; **updated the same evening after D-131** (`dd5e3ff` ZARU R fix, the artefact commit after it —
see [`HANDOVER_ZARU.md`](HANDOVER_ZARU.md) for that work). Before D-131 `main` was at `3526a08`
(`7e3a8b0` fixes, `d3c2464` D-130 artefacts, `eae873f` audit fix, the handovers, then the android-ui
commit). **Seats S (filter) and D (harness).** Companion to [`../android/HANDOVER.md`](../android/HANDOVER.md),
which covers the phone; nothing here is on that path and nothing there is on this one.

Read with [`../phases.md`](../phases.md) §1's loop in mind: restate, plan, edit small, verify with a
command, report. Where this file disagrees with [`../docs/DECISION_LOG.md`](../docs/DECISION_LOG.md),
the log wins and the disagreement is a bug here.

---

## 1. What you are actually picking up

Verifiable, not remembered:

| Claim | How to check |
|---|---|
| The Python reference filter is the specification — no C++/Rust port exists (D-022) | `wc -l core/reference/inekf.py` → 1,427 lines; `core/ffi/idr_core.h` is a header with nothing behind it |
| The harness runs end to end and produces the Gate 1 number | `.venv\Scripts\python -m eval.run --dry-run` plans 12 held-out stems × 5 lengths; a real run takes ~6–7 min |
| **834 tests pass, 1 skipped** at `403a24a` (832 at `dd5e3ff`, plus two for D-133) | `.venv\Scripts\python -m pytest -q` (`--collect-only -q` prints the count) |
| **The committed number is still D-131's, re-stamped at `403a24a` by D-133**: `eval/figures/summary.json` at `commit 403a24a \| seed 0`, clean — 6.14× quiet / 19.72× vibrating / 11.55× pooled at 60 s, on 101 / 113 / 214 windows, window for window what `dd5e3ff` produced (D-133's mechanism ships off; on, at `4389558`, it read 6.20× / 19.81× / 11.82× on 101 / 127 / 228) | `python -c "import json;print(json.load(open('eval/figures/summary.json'))['gate1'])"`; the artefact also says `zaru_sigma_from_window: true` and `gyro_bias_direct_only: false` |
| D-115's 6.2× was measured on a dirty tree into a scratch dir and **never committed** | DECISION_LOG D-115, last sentence; the outputs are in a session scratchpad (§10) |
| IO-VNBD is local: 288 synchronised CSVs, 825 MB | `.venv\Scripts\python -m eval.fetch --sync-only` → `already-present=288 failed=0` (SHA-verifies every file, downloads nothing) |
| `.venv` is Py 3.13.5 with numpy 2.5.3 / pandas / pytest 9.1.1 / ruff; **no torch, no matplotlib** | `.venv\Scripts\python -c "import torch"` fails; `pip install -e ".[plot]"` adds matplotlib |
| The `android-ui/` work that used to sit uncommitted in the tree is on `main` since `3526a08`; a sweep from a clean main checkout now stamps clean, but the worktree recipe (§7) is still the safe one while anyone else's WIP is in the tree | `git status --short` empty → the stamp is clean; anything listed → `-dirty` |
| The NEES consistency test (test 11) is green, five cases, ZARU-only asserted one-sided | `pytest tests/test_se23_derivation.py -k nees -q`; ERROR_BUDGET §10.2 has the table |
| Strapdown and GNSS-available baselines are wired; the Onyekpe INS RNN is **not** | `eval/run.py` `METHODS = ("filter","strapdown","gnss_available")`; `models/train_baseline_rnn.py` needs torch and a training run |

---

## 2. The number, in the order it was measured

Gate 1 (IMPLEMENTATION_PLAN §7): physics-only InEKF within **3–5×** of the GNSS-available
zero-order-hold baseline on **median drift-% at 60 s**, with the update count beside it. A human
closes it; the harness only reports it.

| When | Ratio | Windows | Tree | What changed |
|---|---|---|---|---|
| D-110, 6 Sep | **19.4×** (136.8% / 7.0%) | 3 | `9fdd261-dirty` — superseded by D-130 in `d3c2464` | First sweep that ran to completion. Every window of a length masked in one pass, so the filter entered window *n* unaided since window 1. NIS/dof 2,000–12,000: the χ² gate refused every fix and the state ran away. |
| D-115, 13 Sep | **11.8×** pooled (78.6% / 6.7%) | 205 | `0e43e08-dirty`, scratch only | Doppler velocity update ungated; per-stem `Q` from the stream's own white level; `P0` re-expressed right-invariant; one aided pass with per-window snapshot/replay; 3-strikes re-anchor on the position gate. |
| D-115, split | **6.2×** quiet-mount (S3a+S3c, 56.7% / 9.1%); **22×** vibrating-mount (ten Vta/Vw stems, 86.8% / 3.9%); **1.95×** at 10 s on the quiet pair | 101 / 104 | same | The split is the number to quote, never the pool (§9). |
| D-130, 15 Sep | **6.27×** quiet (57.2% / 9.13%); **19.5×** vibrating (84.2% / 4.31%); 12.3× pooled; **1.84×** at 10 s on the quiet pair | 101 / 125 / 226 | `7e3a8b0`, clean — committed in `d3c2464` | Fixes 1–3 below + `gate1.by_mount_class`; Fix 3 shipped **off** after its A/B; Vta16 now skipped (aided pass diverges under the wider accel-bias prior — D-130 has the probe). |
| D-131, 15 Sep | **6.14×** quiet (56.0% / 9.13%); **19.72×** vibrating (84.0% / 4.26%); 11.55× pooled; **1.81×** at 10 s on the quiet pair | 101 / 113 / 214 | `dd5e3ff`, clean — committed with the row | ZARU's R read from the stop detector's own window instead of the Allan desk figure (`zaru_sigma_from_window`, `update_zaru(sigma=)`). S3a now applies 1,356 of 1,368 ZARUs (16 of 1,372 before) and its bias estimate **does not move**; S3a 42.0 → 42.2%, S3c 69.5 → 72.3% at 60 s; Vw2 loses 12 of 80 windows to replay divergence. A wash on the quoted class, shipped on because the R is the measured one; `ZARU_SIGMA_FROM_WINDOW` flips it. |
| D-133, 15 Sep | **6.14×** quiet / **19.72×** vibrating / 11.55× pooled, **unchanged** (the mechanism ships off); with it on, `4389558`: **6.20×** quiet (56.6% / 9.13%), **19.81×** vibrating (86.1% / 4.35%), 11.82× pooled, **1.77×** at 10 s on the quiet pair | 101 / 113 / 214 (on: 101 / 127 / 228) | `403a24a`, clean — committed with the row; reproduces `dd5e3ff` window for window | `InEKF.gyro_bias_direct_only`: only ZARU may move `b_g` (the position fix, Doppler velocity, NHC and ZUPT lose their gyro-bias gain rows; `Q` untouched). TRAIN S1 bias-block NEES 27.3 → 2.1 against 3.0; S3a's bias converges (0.23 → 0.006 °/s on y). Both quiet per-stem medians fall (S3a 42.2 → 40.6, S3c 72.3 → 71.0), replay divergences 51 → 19, Vw2 keeps 14 more windows — and the pooled quiet median is 0.58 points worse (paired +0.09, bootstrap CI [−5.0, +4.7]): shipped **off** by §3 rule 4, `GYRO_BIAS_DIRECT_ONLY` flips it. The TRAIN bias walk is ×0.5–2.3 of `gyro_bias_rw` from three pairs on one stem; raising `Q` (×2) made the estimate move faster, rejected. **The remaining quiet-class gap is not the gyro bias.** |

**The gap that is the filter's — re-read after D-131.** D-115 named it bias observability: on S3a
every 60 s window opens from an aided state whose gyro-bias estimate has walked to 0.2–0.4 °/s,
and ZARU, the only direct observation, never ran. D-130 made the detector fire (1,372 stops) and
D-131 made the gate accept (1,356 applied). **The bias still walks.** Its last-ten-minute |b_g| on
S3a is 0.23 °/s on the y axis before and after, at 6.9 σ of the filter's own bias block, which sits
at 0.03 °/s throughout (`gyro_bias_rw` is the desk Allan run's 22 °/hr) while the estimate steps
0.03–0.04 °/s every 30 s — three to four times what that process noise allows. Against a 0.03 °/s
block a ZARU at S3a's 1.17 °/s per-sample noise has a gain of 7e-4 per sample: 200 samples at a
stop move a 0.23 °/s error by 13%. The Doppler velocity and NHC updates push the bias between stops
through the cross-correlations, and a correctly weighted observation at the next stop cannot undo
it. **So the remaining quiet-class gap is the gyro-bias block's consistency, not its
observability.** D-133 measured that walk and made the block consistent — see the next
paragraph. Inside the window the tilt error still collapses the speed by 3–17 m/s.

**Re-read after D-133: the gap is not the gyro bias.** The bias walks in a car at ×0.5–2.3 of
`gyro_bias_rw` (S1, three pairs; no other TRAIN stem has two still stops), so the block was not
under-modelled — it was being *pushed*: the Doppler velocity, NHC and position updates, unable to
separate tilt, heading and gyro bias at a 9 s cadence, moved `b_g` through the cross-correlations
three times faster than it walks, and the block's NEES against the truth-standstill bias on S1
was 27.3 against 3.0. `InEKF.gyro_bias_direct_only` lets only ZARU move `b_g`: NEES 2.1, the
estimate steps at the model, and S3a's last-ten-minute |b_g| falls from 0.23 to 0.006 °/s on y.
**And the 60 s drift does not move** — S3a 42.2 → 40.6 %, S3c 72.3 → 71.0 %, pooled quiet median
56.0 → 56.6 % (paired +0.09 points, CI [−5.0, +4.7]); the 60 s speed error at 60 s is still
−9 to −10 m/s in the worst decile with the bias right at entry. Shipped off by §3 rule 4 (the
quoted number is worse by 0.06×), one constant from on. What is left, with the number that
says it: the *accelerometer*-bias attribution. The one variant that moved TRAIN S1's drift
(62.9 → 48.4 % median, p90 548 → 110, 60 s speed error +11.8 → +2.1 m/s) also denied the
Doppler and NHC updates the accel-bias rows; on the quiet pair it was −1.2 / +1.0 paired with one
S3c window at +455 — D-130's Vta16 story (horizontal accel-bias blocks absorbing tilt error) on a
quiet mount. §11 (5) is the brief for it. The 9 s cadence and the mount block are not separated.

**The gap that is not the filter's.** On the ten Vta/Vw stems 95% of the yaw-axis gyro variance is
vibration folded into 0–5 Hz by 10 Hz sampling with no anti-alias filter (gyro–truth course-rate
correlation 0.22–0.27 raw vs 0.95 on S3a). Heading random-walks 20–45° in 60 s. No filter
recovers a heading from that stream, and the write-up says so (§9).

---

## 3. Hard constraints — each one silently ruins the work if ignored

1. **`S-` channels only.** `V-` wheel-speed and steering columns ship in the same download and are
   disallowed by PS 26168. The loader allowlist raises on them; CI's `leakage-audit` job asserts the
   guard *fires* on a deliberate `V-` column. `eval/loaders/truth.py` is the one exception and reads
   `V-` lat/lon/time only.
2. **Held-out stems are read for diagnostics, never for numbers.** Every threshold and prior in
   `FilterConfig` is measured on TRAIN (`eval/splits.py`); S3a/S3c/Vta*/Vw* are graded. Printing
   S3a's stop statistics to check a rule is fine; setting `zupt_*` from them is leakage of a
   different kind and D-115's whole argument collapses.
3. **Stamps.** `idr/stamp.py` writes `commit <sha> | seed <n>` into every artefact and suffixes
   `-dirty` when `git status --porcelain` is non-empty, `nogit` when the cwd is not a checkout.
   Neither may be quoted. See §7 for how to get a clean stamp with someone else's WIP in the tree.
4. **Never tune to the gate.** The ratio is reported, not produced. A fix is measured before and
   after on the same commit pair, both numbers go in the DECISION_LOG row, and a worse number ships
   as "off" with the reason — Fix 3 below is explicitly built that way.
5. **ZUPT and ZARU fire together** at every detected stop; a stop where only one runs is a bug
   (`InEKF` docstring). **Gating is the caller's job**: `is_stationary` and `nhc_is_valid` read the
   raw stream and the harness decides; the filter never inspects its own inputs.
6. **The Doppler velocity update is not gated**, and neither is ZUPT (D-057, D-115): a refused
   velocity is the first step of every runaway this harness has recorded. Do not add a gate "for
   safety".
7. **Do not regenerate the Allan seeds** (`eval/figures/allan_*`) without a DECISION_LOG row. They
   were re-seeded once (D-120) and every `FilterConfig` default traces to them.
8. **`S-A4.csv` is malformed** (column shift at field 6) and every `S-` stem ships twice under
   different checksums; the manifest says which copy is graded (EVALUATION §1.1).
9. **Changing `OUTAGE_LENGTHS_S`, the split, or the CRSE convention needs a DECISION_LOG row** —
   the harness prints that reminder for a reason.

---

## 4. How the harness makes the number (read before touching `eval/run.py`)

`eval/run.py` — 1,884 lines, one pass per sequence:

1. **Load** the `S-` stream (`eval/loaders/io_vnbd.py`) and the paired 10 Hz `V-` truth
   (`truth.py`). Fixes are 9.0 s apart on 69 of 72 stems (`cadence.py`); `Vta1a` is 1 Hz.
2. **Align** during the 30 s `WARMUP_S`: level on a moving window (`_level_sigma`), yaw from the
   receiver's Doppler course above `course_min_speed_mps`, mount yaw by PCA (`pca_mount_yaw`,
   `MountInit`), per-stem `Q` from the warm-up's own white level (`in_motion_config`,
   `stream_white_level`), `P0` mapped right-invariant (`right_invariant_from_plain`).
3. **One GNSS-aided pass** (`run_filter`): propagate every sample; at each fix `update_gnss_velocity`
   (ungated) then `update_gnss` (χ² 3-dof, applied anyway on the third consecutive rejection —
   `GNSS_REJECTIONS_BEFORE_REANCHOR`, counted as `n_gnss_reanchored`); at every sample
   `_step_constraints`: ZUPT+ZARU if `is_stationary` and the state veto (`ZUPT_VETO_*`) agrees, else
   NHC if `nhc_is_valid` in the vehicle frame. `FilterDivergedError` at |v| > 150 m/s skips the stem.
   The filter is `deepcopy`'d at the first sample of every window (`Snapshot`).
4. **Replay every window** from its snapshot (`replay_window`): same `_step_constraints`, GNSS never
   called, through `end_idx` inclusive. A diverged replay drops that window, not the stem.
5. **Score** each of `filter` / `strapdown` (initialised from truth, D-064) / `gnss_available`
   (ZOH from the last fix) through the same `eval/metrics` path: drift-%, CTE, CRSE, yaw RMSE/max.
6. **Write** `summary.json` (stamp, `by_method[method][length]`, `gate1`, `dropped_windows`,
   `skipped`, `aided_pass` with the per-stem update counts), `windows.csv` (one row per window per
   method, `aligned` flag), `trajectory_<stem>.json` for the plot set.

Where the counts are: `aided_pass[stem]` for the aided pass (`n_zaru_applied`,
`n_gnss_reanchored`, alignment source; `zupt_vetoed` is counted in `_step_constraints`), `windows.csv` columns for the replays. `n_filter_windows_unaligned`
travels with every number (D-089).

---

## 5. What D-115 already changed in the filter (so you do not redo it)

| Thing | Where | State |
|---|---|---|
| Doppler velocity update, 2-dof, ungated | `InEKF.update_gnss_velocity`, `FilterConfig.gnss_speed_sigma_mps = 0.5` | landed |
| Course-over-ground as the heading source, `atan(0.5/speed)` model | `course_cross_track_sigma_mps`, `course_min_speed_mps = 3.0` | landed |
| Gyro turn-on prior 0.2 °/s in `P0` (was the 42 °/hr instability → every ZARU rejected) | `gyro_bias_turn_on` | landed |
| Mount random walk 1e-3 rad/√s (was zero → NHC collapsed the block) | `mount_rw` | landed |
| Stop detector 2 s / 0.02 (m/s²)² / 0.01 rad/s (was 0.5 s / 0.05 / 0.02 → fired at 20 m/s) | `zupt_*` | landed — **and this is what Fix 1 replaces the gyro half of** |
| Per-stem `Q` floored at the Allan values | `eval/run.py::in_motion_config` | landed |
| Right-invariant `P0` | `right_invariant_from_plain` | landed |
| `update_speed` for the P-09 speed head | `InEKF.update_speed` | exists, unused until a head is trained |

---

## 6. Work in flight — the three fixes D-115 named, plus the split

Owner of the implementation: **Antigravity**, from the six prompts in the session plan (Claude's
`~/.claude/plans/repo-check-kar-liya-staged-pudding.md`); Claude verifies each step and writes
D-130. If you are reading this without either, the spec below is complete enough to do it by hand.

### 6.1 Fix 1 — a stop detector ZARU can fire from

`core/reference/inekf.py::is_stationary(accel_window, gyro_window, cfg, *, gyro_bias=None)`.
Keep the accel-variance condition (`zupt_accel_var_thresh = 0.02`; D-115 measured stopped median
0.0075 vs rolling p10 0.09 on S3a — a 12× separation). Replace the raw-norm gyro condition with the
bias-corrected `|mean(gyro) − gyro_bias| < zupt_gyro_norm_thresh`, and only if the TRAIN probe shows
it is needed to keep rolling false-fires at ~0%, add a bias-immune `zupt_gyro_var_thresh` on the
window's per-axis gyro variance. `eval/run.py::_step_constraints` passes `gyro_bias=st.b_g`. The
state veto and `update_zaru`'s own gate stay.

*Measure first* on M, S1, S2, S4 (TRAIN stems with ≥5 s truth stops), 2 s window, stopped <0.3 m/s
vs rolling >2 m/s: accel var, gyro per-axis var, |mean gyro − standstill mean|; recall and
share-of-fires-while-rolling per candidate rule. Then S3a/S3c as the diagnostic. The probe also
settles whether S3a's 1.55 °/s is a constant bias (large per-axis mean, small variance) or a
noise floor.

*Accept when:* tests pin the rule; `eval/allan.py`'s segment selection is bit-identical under the
default `gyro_bias=None` (do not touch `allan_segments.csv`); an aided pass on S3a reports
`n_zaru_applied > 0` (D-115: 0) and `b_g` stops walking in the last ten minutes.

### 6.2 Fix 2 — a measured accelerometer turn-on prior

`FilterConfig.accel_bias_turn_on` (m/s²) replaces `ACCEL_BIAS_INSTABILITY_MEASURED` (0.25 mg) as
`sigma_ba` in `initial_covariance` — the instability is how far an *estimated* bias wanders, not
where an unestimated one starts, the same argument that moved the gyro block in D-115. Measured as
`mean(|f|) − g` over every ≥5 s TRAIN standstill (the same 638 s): the one offset component
independent of levelling. The horizontal components are confounded with a levelling derived from
the same sensor; the comment says so. Keep the instability constant — it is still the floor the
block converges to.

*Accept when:* the `P0` block test is updated; all five `test_11_nees_*` cases are in band or the
exact miss is recorded (bands are not widened, `NEES_RUNS` is not changed); the `P0` docstring
table row reads the new figure.

### 6.3 Fix 3 — bias snapshot at outage entry

ERROR_BUDGET §3.2 and the tunnel doc §1.1.B call for it. `InEKF.hold_biases: bool = False`; when
set, `propagate` zeros the `b_g`/`b_a` rows and columns of `Q_c` before Van Loan and `_apply_update`
zeros the Kalman-gain rows for `IDX_GYRO_BIAS` / `IDX_ACCEL_BIAS` — except `update_zaru`, which
observes `b_g` directly and keeps its gain row. `replay_window` sets it on the copied snapshot;
the aided pass never does. `summary.json` carries `biases_held_in_outage` so the artefact says
which variant produced it.

*Accept when:* with the hold and NHC+ZUPT only, `b_g`, `b_a` and their `P` blocks are bit-identical
over a 60 s synthetic window; with ZARU, `b_g` moves and `b_a` does not; **an A/B from the same S3a
+ S3c aided snapshots, hold on vs off, median and p90 drift at 60 s, both numbers in D-130**, and the
committed default is the one the A/B supports — if off wins, off ships and the row says so.

### 6.4 The split in the artefact

`eval/splits.py::QUIET_MOUNT = ("S3a", "S3c")` (docstring: D-115's in-motion white level 1.7–1.9
°/s vs 4–20 °/s); the vibrating class is *derived* as `LONG_OUTAGE − QUIET_MOUNT`.
`summary.json["gate1"]["by_mount_class"]["quiet" | "vibrating"]` with the same fields as the pooled
block, which stays unchanged.

### 6.5 Then

Code commit (Python paths only), sweep from a clean worktree (§7), copy the artefacts into
`eval/figures/`, D-130 row with before/after/split/A/B/measured values and the plain verdict,
`CHANGELOG.md`, artefact commit. Nothing is pushed without the human.

---

## 7. Environment — the commands that work on this box

```text
# always the venv, never the system python (3.13.5 there too, but no pytest)
.venv\Scripts\python.exe -m pytest -q                      # 823 tests (829 with the android-ui WIP), ~3 min
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m eval.fetch --sync-only          # SHA-verify the 288 files, ~2 min
.venv\Scripts\python.exe -m eval.run --dry-run              # plan only, exit 2 by design
.venv\Scripts\python.exe -m eval.run --out <dir>            # full sweep, ~6-7 min, stamps -dirty here
```

**A clean stamp with someone else's WIP in the tree** — verified 15 Sep:

```text
git -c core.longpaths=true worktree add C:\g1\wt <sha>      # SHORT path; a worktree under the deep
cd C:\g1\wt                                                 # scratchpad path dies "Filename too long"
"<repo>\.venv\Scripts\python.exe" -m eval.run --data "<repo>\data\IO-VNBD" --out C:\g1\sweep
                                                            # python -m puts the cwd first on sys.path,
                                                            # so eval/core/idr resolve from the worktree
                                                            # and idr.stamp reads its clean sha
cd <repo> && git worktree remove C:\g1\wt
```

`git archive | tar -x` does **not** give a stamped run — no `.git`, so the stamp reads `nogit`.
Do not `git stash` the android-ui files to get a clean tree; they are not yours.

Other traps, from the memory notes: the Bash tool collapses `\\` to `\` inside heredocs, so write
Python through a file, not a heredoc; Gradle needs `JAVA_TOOL_OPTIONS=-Djdk.net.unixdomain.tmpdir=…`
(irrelevant here, relevant the moment you touch `android-ui/`).

---

## 8. After D-130 — the Gate 1 checklist, mapped

IMPLEMENTATION_PLAN §7, Gate 1, in the order to do them:

| Item | Status 15 Sep | What closes it |
|---|---|---|
| Physics-only InEKF within 3–5× of GNSS-available at 60 s, update count beside it | **6.14× quiet / 19.72× vibrating (D-131's number, re-stamped at `403a24a` by D-133)** — not in band; ZARU applied at 97–99% of detected stops; the bias block can be made consistent (D-133, `gyro_bias_direct_only`, shipped off) and the number does not move | the accelerometer-bias attribution (§2, §11 (5)), then a human reads `summary.json` against §7 and signs or does not |
| `Q` from the IO-VNBD Allan run | done (D-045, D-120), per-stem floored in motion (D-115); `gyro_bias_rw` measured in a car on TRAIN at ×0.5–2.3 of the desk figure (D-133: three pairs on one stem; the dataset cannot do better) — the block's over-confidence was mis-attribution by the aiding updates, not the walk | nothing further on `gyro_bias_rw`; `accel_bias_rw` and the horizontal accel-bias blocks are the unmeasured ones |
| SE₂(3) tests 7–11 incl. NEES | green, five cases, means unchanged at `403a24a` (17.419 / 18.593 / 16.620 / 18.672 / 13.568; ERROR_BUDGET §10.2) | re-check after any change to `P0` or `Q` |
| Raw-strapdown and GNSS-available baselines | done, in every sweep | — |
| Onyekpe INS baseline reproduced, gap explained | **not started**: `models/baseline_rnn.py` + `train_baseline_rnn.py` exist, no checkpoint, no torch here, no GPU | someone with a GPU trains it; then a `--with-rnn` fourth entry in `METHODS` |
| Yaw error instrumented and plotted separately | instrumented (`yaw_rmse_deg`, `yaw_max_deg` in every window row); **no plot — no matplotlib installed, no `eval/plots.py`** | `pip install -e ".[plot]"`, an `eval/plots.py` that reads `summary.json` + `windows.csv` and calls `idr.stamp.stamp_figure` |
| One command regenerates every figure | `eval.run` regenerates every *number*; there are no figures yet | same `eval/plots.py`, called from `eval.run` or one line after it |
| Leakage audit pass #1 | the CI job runs on every push and is demonstrated to fail; **no signed "pass #1" record** | a DECISION_LOG row that quotes the job's output on the D-130 commit and the allowlist diff since D-044 |

Then, in this order: P-08 speed + variance head (architecture, NLL and calibration metric are
written in `models/speed_head.py`; **blocked on the human signing Gate 1**, then needs torch and a
GPU — Gate 2 is calibration ≥95% inside ±2σ, not RMSE); P-09 fuse it through `update_speed` with
`R` = the head's own variance; P-11 mount block in-filter with the PCA initialiser (`pca_mount_yaw`
exists; `MountInit.spread_rad` already feeds `P0`); the October port (D-022) — `van_loan` is 50% of
`propagate` and any cheaper closed form must be validated against it (README §throughput).

---

## 9. What the write-up may say — and may not

- **Quote the ratio split, never pooled.** "On the two recordings whose IMU stream can support dead
  reckoning the physics-only filter is *N*× the GNSS-available baseline at 60 s and *M*× at 10 s,
  limited by bias observability at a 9 s aiding cadence; on the other ten the 10 Hz phone stream
  puts heading beyond 20° at 60 s and no filter closes that" — D-115's own sentence, with D-130's
  numbers.
- IO-VNBD's 10 Hz stream on the vibrating-mount stems **is not an IMU for this purpose**; that is
  the stated reason our own logger records at 100 Hz (D-106) and why the domain-shift ablation
  needs the Delhi collection.
- The update count: ~7 fixes in a 60 s aided stretch at 9 s cadence, not 60 (EVALUATION §5).
- Nothing about "proven" until the human signs the gate. "Measured, at *x*, on *n* windows,
  commit *sha*" is the form.
- The 19.4× in D-110 was measured under a mask that left the filter unaided across consecutive
  windows; it is a different protocol and is not comparable to anything after D-115.

---

## 10. Scratch probes — where the measurements behind D-110/D-115 live

Not in the repo. Per-session scratchpads under
`C:\Users\MANISH~1\AppData\Local\Temp\claude\C--Users-MANISH-KUMAR-Desktop-My-Projects-SIH-26168\<session>\scratchpad\`:

- `59b04088-…` (13 Sep): `diag.py` (shared loader), `qmeasure.py` (in-motion white level, heading /
  tilt random walk vs truth), `yawcheck.py`, `dopp.py` (Doppler accuracy), `stops.py` /
  `zuptcheck.py` (stop-detector false fires vs truth speed — **the starting point for Fix 1's probe**),
  `fixerr.py`, `aided.py` (whole sequence through `run_filter`), `windows_probe.py` (60 s replay,
  speed/heading split — **the starting point for Fix 3's A/B**), `perstem.py` (per-stem Gate 1 split
  from `windows.csv`), and `sweep1/2/3` outputs — `sweep2` is what D-115 quotes.
- `cddbe986-…` (13 Sep): the D-120 Allan re-seed probes and per-block NEES scripts.

Each hard-codes `sys.path.insert(0, <its own scratchpad>)`; fix that line, do not rewrite them.

---

## 11. Questions nobody has answered yet

1. Is S3a's 1.55 °/s standstill gyro a real turn-on bias — 7.7σ of the 0.2 °/s prior measured on
   M/S1/S2/S4 — or a mean-of-norms noise floor? **Answered in D-130: a floor.** The norm of S3a's
   standstill *mean* gyro is 0.015 °/s (per-axis std 0.3–1.4 °/s), so the gyro turn-on prior stands
   and the honest-limits sentence about a held-out handset is not needed for this one.
2. Which of the two copies of every `S-` stem is graded (EVALUATION §1.1) — the manifest carries
   both checksums; the run uses whatever is on disk.
3. Does anyone own the Onyekpe reproduction? It is the one Gate 1 line item with no code path and
   no machine.
4. **Answered in D-131, and it opens the next one — [`HANDOVER_BIAS.md`](HANDOVER_BIAS.md) is the
   brief for it, self-contained.** Was the quiet-class gap ZARU observability?
   No: with ZARU applied at 1,356 of 1,368 stops on S3a the bias estimate is where it was
   (0.23 °/s on y in the last ten minutes, 6.9 σ of a bias block that sits at 0.03 °/s), because
   the block is over-confident and the other updates move the bias 3–4× faster than
   `gyro_bias_rw` allows. **Open:** what does the gyro bias actually do in a car, measured on
   TRAIN — the in-motion analogue of D-120's desk Allan run for the bias term (the walk of the
   aided-pass estimate against the truth-standstill bias, per stem, on M/S1/S2/S4), and whether
   a `gyro_bias_rw` read from it, floored at the desk value the way `in_motion_config` floors
   the white terms, lets ZARU's now-correct R carry weight. Measure before setting anything;
   D-115's downward sweep of `gyro_bias_rw` (×0.1) moved nothing, and nobody has swept it up.
   **First measurements are already in `HANDOVER_BIAS.md` §1** and they complicate the question:
   on TRAIN stem S1 the filter's bias-block NEES against the truth-standstill bias is **27.3
   against 3.0 expected** (error/σ 4.1 on the worst axis), so the block is over-confident — but
   the *true* bias walks at only ×1–2 of `gyro_bias_rw` while the *estimate* moves ×3, so most of
   the estimate's motion is the Doppler and NHC updates blaming `b_g` for tilt and heading error,
   not an under-modelled walk. Raising the process noise alone will not close that.
   **Answered in D-133.** The walk, widened to the whole TRAIN split, stays ×0.5–2.3 from S1's
   three pairs (no other stem has two still stops; the stop mean's own noise is the size of the
   walk). Raising `Q` ×2 made the estimate move *faster* (rejected). Letting only ZARU move `b_g`
   (`InEKF.gyro_bias_direct_only`) makes the block consistent (S1 NEES 27.3 → 2.1) and converges
   S3a's bias (0.23 → 0.006 °/s) — and the 60 s drift does not move (paired +0.09 points on the
   101 quiet windows). Shipped off by §3 rule 4; `GYRO_BIAS_DIRECT_ONLY` flips it.
5. **Open — the accelerometer bias, the next candidate with a number behind it.** With `b_g`
   right at entry the 60 s speed still collapses by 9–10 m/s in the worst decile on S3a, so the
   tilt error is not the gyro's. D-133's wider mask (Doppler and NHC denied the *accel*-bias rows
   too, ZUPT keeping `b_a`) was the only variant that moved TRAIN S1's drift — 62.9 → 48.4 %
   median, p90 548 → 110, 60 s speed error +11.8 → +2.1 m/s — and on the quiet pair read −1.2 /
   +1.0 paired with one S3c window at +455, the Vta16 mechanism (D-130) on a quiet mount. The
   measurement to make first, the way D-133's `bias_walk2.py` did for `b_g`: `b_a` at TRAIN
   standstills (vertical, the only component a standstill separates from levelling) against the
   aided pass's estimate and its block, and the horizontal blocks' walk during the drive; then
   whether a mask, a per-axis prior, or `accel_bias_rw` is what the measurement supports. Rule 4
   applies: measure before and after, both sweeps in the row, a worse number ships off.
