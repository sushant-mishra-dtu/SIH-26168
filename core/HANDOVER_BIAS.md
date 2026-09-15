# Handover — the gyro-bias block: ZARU now runs and the bias is still wrong

**Written:** 15 Sep 2026, after D-131 landed (`main` at `1e94820`). **Seat S (filter).**
Self-contained: everything you need is in this file, the files it names, and the commands it gives.
Companion to [`HANDOVER.md`](HANDOVER.md) (the wider filter / Gate 1 state), to
[`HANDOVER_ZARU.md`](HANDOVER_ZARU.md) (the work immediately before this, now **done** — read its
status block first), and to [`../models/HANDOVER_P08.md`](../models/HANDOVER_P08.md), whose owner
may be working **at the same time** — §0 says how you stay out of each other's way.

Where this file disagrees with [`../docs/DECISION_LOG.md`](../docs/DECISION_LOG.md), the log wins.

---

## 0. Parallel-work protocol

The ZARU seat is finished and merged; `zaru-gate` is deleted locally. One branch is live beside
you. **Nothing is pushed by anyone.**

| | Bias block (this file) | P-08 (`models/HANDOVER_P08.md`) |
|---|---|---|
| Branch | `bias-block` (create it) | `p08-speed-head` |
| Worktree | `C:\g1\wt_bias` | `C:\g1\wt_p08` |
| Python | `<repo>\.venv\Scripts\python.exe` (3.13, numpy/pandas/pytest/ruff; **no torch**) | `C:\Users\MANISH KUMAR\AppData\Local\Programs\Python\Python312\python.exe` (ROCm torch 2.9.1, GPU) |
| DECISION_LOG row | **D-133** (reserve it; D-132 is P-08's) | **D-132** (reserved) |
| Owns (may edit) | `core/reference/inekf.py`, `eval/run.py`, `eval/figures/summary.json`, `eval/figures/windows.csv`, `eval/figures/trajectory_*.json`, `tests/test_filter.py`, `tests/test_se23_derivation.py`, `tests/test_harness_wiring.py`, `tests/test_ffi_contract.py`, `core/HANDOVER.md`, this file | `models/**`, new `tests/test_speed_head*.py`, new `eval/figures/speed_head_*`, `models/HANDOVER_P08.md` |
| Must not touch | anything in the P-08 column; `android-ui/`, `android/`, `graphify-out/`; `.venv` (no pip installs); **`eval/figures/allan_*`** (§2's trap 2) | anything in this column; `android-ui/`, `android/`, `graphify-out/`; `.venv`; `eval/figures/summary.json` / `windows.csv` / `trajectory_*` |
| Shared, append-only | `docs/DECISION_LOG.md` — append your reserved row at the end; on a merge conflict keep both rows, ordered by ID | same |

Setup (run from the repo root, once):

```text
git -c core.longpaths=true worktree add C:\g1\wt_bias -b bias-block main
cmd /c mklink /J "C:\g1\wt_bias\data\IO-VNBD" "C:\Users\MANISH KUMAR\Desktop\My Projects\SIH-26168\data\IO-VNBD"
```

- **Use `mklink /J`, never `ln -s`.** Git Bash's `ln -s` on this box silently *copies* the 2.1 GB
  dataset (verified 15 Sep). Only `IO-VNBD` needs the junction; `data/README.md` and
  `data/manifest/` are tracked. Before removing the worktree: `rmdir C:\g1\wt_bias\data\IO-VNBD`
  (removes the junction, not the data), then `git worktree remove C:\g1\wt_bias`.
- Work **inside the worktree** (`cd C:\g1\wt_bias`); `python -m ...` puts the cwd first on
  `sys.path`, so `core`/`eval`/`idr` resolve from the worktree and `idr.stamp` reads *its* sha.
- Stage by explicit path only. Never `git add -A` / `git add .`.
- Finishing: `git rebase main`, `ruff check .` + `pytest -q` green, then fast-forward `main`
  (`git checkout main && git merge --ff-only bias-block`) from the **main checkout**. Whoever
  merges second rebases. Never push.
- `CHANGELOG.md` is the operator-UI changelog; you do not add a line.

**Two facts about the remote, so you do not trip on them.** `main` is **2 commits ahead of
`origin/main` and unpushed** (`dd5e3ff`, `1e94820` — D-131). And `origin/zaru-gate` exists,
pushed 15 Sep 17:42, pointing at **`3526a08`** — the commit *before* any ZARU work. It is a stub
someone pushed and it contains none of D-131. Do not branch from it, do not merge it, and do not
assume it is a teammate's finished work; if its owner appears, D-131 on `main` is what happened.

---

## 1. The problem, in numbers you can re-derive

Gate 1 (physics-only InEKF within 3–5× of the GNSS-available baseline, median drift-% at 60 s) is
at **6.14× on the quiet-mount stems** S3a + S3c (56.0% / 9.13%, 101 windows), commit `dd5e3ff`,
D-131. Per stem at 60 s: S3a 42.2% / 8.2% = **5.2×**, S3c 72.3% / 10.6% = 6.8×. To reach 5× on the
quiet class the pooled filter median must fall to **≤ 45.6%**, from 56.0%.

**The chain, and where it stopped.** D-115 diagnosed the quiet-class gap as gyro-bias
observability: every 60 s window opens from an aided state whose `b_g` is wrong, and ZARU — the
only direct observation (`z = ω̃ − b̂_g`, SE23 §7.3) — never ran. D-130 made the stop detector fire
(S3a: 1,372 stops). D-131 made ZARU's χ² gate accept, by testing the innovation against the stop's
own gyro noise instead of a desk Allan figure. **It worked, and the bias did not move.**

| | D-130 (`7e3a8b0`) | D-131 (`dd5e3ff`) |
|---|---|---|
| ZARU applied / offered, S3a | 16 / 1,372 | **1,356 / 1,368** |
| S3a last-10-min \|b_g\|, per axis (°/s) | [0.061, 0.228, 0.022] | [0.059, **0.233**, 0.025] |
| S3a 60 s drift median | 42.0% | 42.2% |
| Quiet-class ratio | 6.27× | 6.14× |

**Why an applied ZARU carries no weight.** The filter holds its gyro-bias block at **σ ≈ 0.030 °/s**
per axis (√ of the `P` block, whole-file median, both quiet stems, before and after D-131). Against
`R = (1.17 °/s)²` — S3a's own standstill noise, which is the correct `R` — the Kalman gain for one
ZARU sample is about **7e-4**. Two hundred samples at a stop move a 0.23 °/s error by ~13%. The
bias is observed now; the covariance says it does not need correcting.

**And the block is over-confident, measured on TRAIN.** S1 is a TRAIN stem with genuine
standstills, so this sets values rather than merely illustrating. At each truth stop the true rate
is zero, so the mean gyro over that stop **is** the bias there; comparing the aided pass's `b_g`
entering the stop (the snapshot is taken at the stop's first sample, before that stop's own ZARUs
fire, so it is the bias the filter carried while driving) against that measured bias:

| S1, 4 truth standstills, aided pass at `dd5e3ff` (ZARU 2,145 / 2,160 applied, σ 0.72 °/s) | |
|---|---|
| \|b_g error\| median, per axis | [**0.103**, 0.040, 0.042] °/s |
| Filter's own σ for the block, median | [0.028, 0.025, 0.028] °/s |
| error / σ, median | [**4.12**, 1.77, 0.83] |
| **Bias-block NEES at those stops, median / mean** | **27.3 / 22.5**, against **3.0** expected |

That is the consistency statement the synthetic NEES test cannot make: on real data the gyro-bias
block is over-confident by about **3× in σ, 9× in NEES**.

**But it is not simply an under-modelled walk, and this is the fork in the road.** `gyro_bias_rw`
= 3.10e-5 rad/s²/√Hz allows the true bias to walk **0.0097 °/s per 30 s**. Two things move:

- **The true bias**, measured between consecutive S1 standstills (3 pairs, gaps 801 s median /
  4,252 s max, span 5,085 s): `q` = **1.0–2.1× the config value**, i.e. 0.009–0.020 °/s per 30 s.
  Its peak-to-peak over the whole drive is [0.139, 0.115, 0.283] °/s.
- **The filter's estimate of it**, on S3a: **0.028 / 0.034 / 0.026 °/s per 30 s** — 2.7–3.5× the
  config value, and roughly **2× faster than the truth actually walks**.

So the estimate is not chasing a bias that moves; it is being *pushed*. Between stops the only
things that touch `b_g` are the Doppler-velocity update and NHC, through the covariance's
cross-correlations, and at a 9 s fix cadence tilt error, heading error and gyro bias are not
separable — so those updates blame `b_g` for errors that are not the bias's. D-115 said as much
("tilt, gyro bias and accelerometer bias separate only through turns") and attributed the symptom
to the missing observation; D-131 supplied the observation and the symptom stayed.

**Read the two faults separately, because they have different fixes.** (a) `P` is too small — part
of that is a bias process noise measured on a desk, worth about ×2. (b) The estimate is being
driven by updates that cannot distinguish what they are correcting — worth the rest.

---

## 2. What a legitimate fix looks like — and three traps in it

**Rules that bind (AGENTS.md, HANDOVER.md §3).** Every number is measured on TRAIN
(`eval/splits.py::TRAIN`; M, S1, S2, S4 are the stems with ≥ 5 s stops, and **S1 is the only one
whose stops are genuinely still** — see trap 3). S3a/S3c/Vta*/Vw* may be printed as diagnostics and
never used to set a value. Nothing is tuned to the 3–5× target: measure before and after on the
same commit pair, both numbers in D-133, a worse number ships off with the reason. Both sweeps
clean-stamped. Fix the mechanism, not the number.

**Three candidates. Measure, then pick — do not pick first.**

- **A — a bias process noise read from the stream, the `in_motion_config` pattern.** `Q`'s white
  terms are already raised per stem from the warm-up's own level (D-115); the bias terms are not.
  Measure the true bias walk on TRAIN (§1's method, extended — it currently rests on 3 pairs from
  one stem), and raise `gyro_bias_rw` toward it, floored at the Allan value. **Harness-side, not
  the config default** (trap 2). Its weakness is its size: the honest measurement says ×1–2, and
  ×2 in σ closes a quarter of a 3× consistency gap. It makes `P` less wrong without touching why
  the estimate moves — and a wider bias `Q` lets the aiding updates move `b_g` *more*, which is the
  fault in (b). Measure both directions before believing either.
- **B — stop the guessing: restrict which updates may move `b_g` in the aided pass.** The machinery
  exists and is tested: `_apply_update(..., allow_bias=)` and `InEKF.hold_biases` zero the
  Kalman-gain rows for `IDX_GYRO_BIAS` / `IDX_ACCEL_BIAS` for every update except ZARU (D-130's
  Fix 3, built for outages and shipped off there). Applied to the *aided* pass and inverted, it
  says: the Doppler velocity and NHC may correct attitude and velocity, and only ZARU and the
  position fix may claim to have learnt something about the gyro bias. **This was not available
  before D-131** — denying the guessers while ZARU was refused 98.8% of the time would have
  starved the state completely. It is available now precisely because the observation runs.
  Its weakness is stems without stops: Vta1a offers 2 stops in 4,200 s, the Vta/Vw class offers
  almost none, and for them B means `b_g` is never estimated at all. Measure per stem and quote
  the split; a mechanism that helps the quiet class and wrecks the rest is reported, not shipped.
- **C — an observability-aware re-inflation.** Widen the bias block when the filter has gone a
  long time without a ZARU, the way `reinflate_mount` widens the mount block after a knock
  (`MOUNT_KNOCK_RAD`, already in the filter). Principled in the same sense: the covariance should
  say "I have not seen this state in ten minutes". Its weakness is that the threshold and the
  amount are two new numbers, and neither is measured by anything; it risks being A with extra
  parameters. Worth measuring only if A and B both fail, and then the row says where the numbers
  came from or it does not ship.

**Trap 1 — the NEES test cannot see this fault, and can be made to lie about it.**
`tests/test_se23_derivation.py::_nees_run` drives the *simulated truth* bias with
`cfg.gyro_bias_rw * sqrt(dt)` and gives the filter the same constant for `Q`. Raise the config
default and both sides move together: the test stays in band by construction while telling you
nothing about the real sensor. This is exactly why the real consistency number is the one in §1
(S1's bias-block NEES of 27.3 against 3.0), measured against truth on a TRAIN stem. Re-run all five
`test_11_nees_*` cases anyway; **bands and `NEES_RUNS` are never edited**, and a miss is reported.

**Trap 2 — the config default is pinned to the Allan artefact, and the artefact is frozen.**
`tests/test_allan.py::test_filter_config_matches_the_measured_summary` asserts
`FilterConfig.gyro_bias_rw == allan_summary.json["gyro_bias_rw_rad_s2_sqrt_hz"]` to 0.5%, and
HANDOVER.md §3 rule 7 forbids regenerating `eval/figures/allan_*` without its own row. A bias walk
measured in a moving car is **not** an Allan measurement and must not be written into that
artefact. So candidate A belongs in `eval/run.py` beside `in_motion_config`, raising the value for
the run and leaving the measured-on-a-desk default where the test can see it. That is the same
shape D-115 chose for the white terms, for the same reason.

**Trap 3 — three of the four TRAIN stems cannot measure a bias at all.** Of the ≥ 5 s truth stops,
the accelerometer-variance condition (`zupt_accel_var_thresh`, the detector's own) admits 4 of 23
on S1, 1 of 21 on M, 0 of 10 on S4 and 0 of 1 on S2: at the others the phone is being handled, not
sitting still. Drop that condition and the "bias walk" reads ×7.9 on S1, ×39.8 on S4 and **×464 on
M** — which is a measurement of someone picking up a phone, and the number you will be tempted to
use because it is bigger and makes the covariance look honest. It is not a bias walk. The honest
statement today is **×1–2 from 3 pairs on one stem**, and the first half of this work is making
that measurement less thin: more stems (the whole TRAIN split, not only the four with long stops),
shorter admissible stops, the `V-`-truth standstill rather than the detector where they differ.
If it stays thin, the row says so and candidate A ships with the uncertainty stated.

**Also measure, because it is the actual objective:** after the fix, the S1 bias-block NEES and
error/σ of §1 (does the block become consistent?); S3a's last-ten-minute `b_g` and the 60 s window
speed error at 60 s (D-115: −3 to −17 m/s; D-131: −1.55 m/s median, p10 −10.1); and the quiet-class
ratio, split and pooled.

---

## 3. Files, tests, and what pins what

| File | What is there | What changes |
|---|---|---|
| `core/reference/inekf.py` | `FilterConfig.gyro_bias_rw` (245) / `accel_bias_rw` (246), both Gauss–Markov-derived, not measured; `process_noise_psd` (938) builds `Q_c` from them; `_apply_update(..., allow_bias=)` (1192) and `hold_biases` (1128) already zero bias gain rows; `reinflate_mount` (1461) | A: nothing (the default stays, §2 trap 2). B: the `allow_bias` policy, and where it is decided. C: a re-inflation entry point beside `reinflate_mount` |
| `eval/run.py` | `in_motion_config` (363) — the pattern A follows; `_step_constraints` (677) — where ZARU, ZUPT and NHC are chosen; `run_filter` (488) — where the Doppler velocity update is applied; `HOLD_BIASES_IN_OUTAGE` (665) / `ZARU_SIGMA_FROM_WINDOW` (674) — the two "which variant produced this artefact" switches, both reported in `summary.json` | A: a bias-noise counterpart to `in_motion_config`. B: the aided pass's `allow_bias` policy plus a third switch, named and reported the same way |
| `tests/test_allan.py:456` | `test_filter_config_matches_the_measured_summary` pins all four noise defaults to `allan_summary.json` | untouched — that is the point of trap 2 |
| `tests/test_se23_derivation.py:1005` | `_nees_run` drives truth *and* `Q` from `cfg.gyro_bias_rw`; the five `test_11_nees_*` (bands [16.843, 19.195]). **Bands and `NEES_RUNS` are never edited** | re-run all five; at `dd5e3ff` they read 17.419 / 18.593 / 16.620 / 18.672 / 13.568 |
| `tests/test_filter.py:693` | `test_zaru_is_exempt_from_bias_hold`, `test_hold_biases_off_allows_normal_bias_updates` — the second asserts that **without** the hold, NHC *does* move `b_g` through cross-terms, which is the mechanism B restricts | B re-pins this: it stays true of the filter, and the harness's aided-pass policy is what changes |
| `tests/test_harness_wiring.py:719` | `test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it`; `test_step_constraints_tests_zaru_against_the_stops_own_gyro_level`; the artefact-switch assertions (425-429) | A and B each add one: the new switch travels in `summary.json` |
| `tests/test_ffi_contract.py:52` | `gyro_bias_rw` is on the FFI config surface | name stays |
| `docs/ERROR_BUDGET.md` §3.2, §9 (limits 2-3) | the residual-bias cost table (0.005–0.01 °/s is the operating row); "`gyro_bias_rw` / `accel_bias_rw` are derived, not measured" | a measured in-motion figure changes §9's limit 3 wording |
| `docs/DECISION_LOG.md` D-045, D-115, D-120, D-130, D-131 | the seeds; the diagnosis; the re-seed; the detector; the ZARU R | append **D-133** |

---

## 4. Acceptance — D-133 in the D-130 / D-131 format

Same table shape (5 columns; escape any `|` inside a cell as `\|`):

1. **The measurement first:** the TRAIN bias walk — per stem, how many stops survive the stillness
   condition, how many pairs, the gaps, `q` per axis against the config value, and the contaminated
   all-stops figure printed beside it so the difference is on the record. Then the S1 bias-block
   consistency (error, σ, error/σ, NEES) before and after.
2. The candidate chosen and the others rejected, with the numbers that decided it.
3. Before (`dd5e3ff`, clean) vs after (your commit, clean), at 60 s, **quiet and vibrating split
   and pooled**, with window counts; 10 s quiet; per-stem S3a / S3c; the aided-pass counters
   (`n_zaru_applied` / `n_zaru_rejected`, `zaru_sigma_mean_used`, `n_gnss_reanchored`); replay
   divergences; dropped windows; skipped stems.
4. The five NEES means against their bands — and one sentence saying why they are weak evidence
   here (§2 trap 1).
5. The verdict against 3–5× in plain words. No "nearly", "effectively", "close to". If it does not
   close, say which part of the remaining gap is which.
6. Artefacts: `summary.json`, `windows.csv`, `trajectory_*.json` from the clean sweep, stamped
   `commit <sha> | seed 0`, **no `-dirty`, no `nogit`**. Two commits: code (`fix(filter): ...`)
   then artefacts + row (`chore(figures): Gate 1 sweep at <sha> (D-133)`).
7. `core/HANDOVER.md` §1, §2, §8, §11 updated to the new number; this file gets a status block.

---

## 5. Probes that already exist — copy, fix one path line, do not rewrite

All under `C:\Users\MANISH~1\AppData\Local\Temp\claude\C--Users-MANISH-KUMAR-Desktop-My-Projects-SIH-26168\<session>\scratchpad\`.

- **`3b21b459-…` (15 Sep evening, D-131 — start here):**
  - `bias_walk.py` — **the probe behind §1.** Per-stem truth-stop bias, the walk between stops
    (strict and contaminated), and the aided pass's `b_g` at each stop against it with the block's
    own σ and NEES. `--no-filter` skips the aided pass. This is the measurement D-133 extends.
  - `zaru_objective.py` — before/after A/B through `run_filter` + `replay_window`, switching the
    change by monkey-patching one symbol; its "before" arm reproduces D-130 to the digit. **The
    template for any on/off A/B of a filter change**, including this one.
  - `zaru_measure.py` — TRAIN standstill / run-out / gate-acceptance measurement (D-131 §1).
  - `nees_means.py` — the five `test_11_nees_*` means, printed without pytest.
- `0f5cc559-…` (15 Sep): `stops.py` (detector recall, per-axis standstill std), `diag.py` (the
  shared loader: `load(stem)`, `truth_ned_per_sample`), `accel_turnon2.py` (clock-restart-safe
  loader — M, S2 and S4 restart their clock mid-file and `assert_uniform_grid` raises; take the
  monotonic prefix), `perstem.py` (Gate 1 split from `windows.csv`).
- `59b04088-…` (13 Sep): `aided.py`, `windows_probe.py` (60 s replay, speed/heading split),
  `yawcheck.py`, `zuptcheck.py`.
- `ad3ced7c-…` (15 Sep): `ab_hold.py` (the D-130 Fix 3 A/B), `vta16_probe.py`.
- Reference sweeps: `C:\g1\sweep_zaru` (`dd5e3ff`, = the committed `eval/figures/`),
  `C:\g1\sweep_audit` (`7e3a8b0`), `%TEMP%\g1\sweep_before` (`b8bc3ee`).

Each hard-codes a `sys.path.insert` to its own directory or to the main checkout; **fix that one
line to point at your worktree** and otherwise leave them alone.

---

## 6. Commands

```text
cd C:\g1\wt_bias
"<repo>\.venv\Scripts\python.exe" -m pytest -q                       # 832 pass, 1 skipped, ~2.5 min
"<repo>\.venv\Scripts\ruff.exe" check .
"<repo>\.venv\Scripts\python.exe" -m pytest tests\test_se23_derivation.py -k nees -q   # ~2.5 min
"<repo>\.venv\Scripts\python.exe" -m eval.run --data "<repo>\data\IO-VNBD" --out C:\g1\sweep_bias
                                                                     # ~7 min; the first line of
                                                                     # windows.csv must read
                                                                     # "# commit <sha> | seed 0" — clean
```

Commit the code first, then sweep **from that commit** (a sweep from an uncommitted tree stamps
`-dirty` and cannot be quoted), then copy `summary.json`, `windows.csv` and `trajectory_*.json`
into `eval/figures/` and commit them with the row.

---

## 7. Time budget and the stop rule

Measure 60 min (the TRAIN walk is thin and widening it is half the work) · code + tests 45 min ·
NEES + full pytest 10 min · two sweeps 15 min · row 30 min ≈ **2.5–3 h**. One attempt, measured
honestly, is the deliverable — not a second attempt with a different number. If the quiet ratio
does not reach 5×, D-133 says so and says why, and the project's stop rule applies (phases.md
P-07: submit physics-only honestly). **Gate 1 is signed by a human, never by a row.**

Note what the last two rows have cost and bought: D-130 moved the quiet class 6.40× → 6.27×, D-131
6.27× → 6.14×. Both were correct fixes to real defects and neither moved the gate. If this one
behaves the same way, the honest conclusion — that a 9 s aiding cadence on a 10 Hz phone stream
does not support 5× at 60 s, and which measurement would settle it — is worth more to the
submission than a fourth attempt.

---

## 8. Open questions this work will answer (put the answers in the row)

1. How fast does the gyro bias actually walk in a car, on TRAIN, with enough stops behind the
   number to quote it? (§1 has ×1–2 from 3 pairs on one stem; that is thin.)
2. Does making the bias block honest — by A, B or C — let the ZARU that D-131 unlocked carry
   weight, i.e. does S1's bias-block NEES fall from 27.3 toward 3.0 and S3a's last-ten-minute
   `b_g` fall from 0.23 °/s?
3. If `b_g` does converge, does the 60 s speed collapse shrink with it, and by how much? This is
   the link D-115 asserted and nothing has yet demonstrated end to end.
4. If it converges and the drift does **not** move, what is left? The candidates named and not yet
   separated are the accelerometer bias (D-130 showed the horizontal blocks absorbing tilt error —
   0.3–0.5 m/s² on Vta16, enough to diverge the pass), the 9 s aiding cadence itself, and the
   mount block. Say which, with the number that says it.
