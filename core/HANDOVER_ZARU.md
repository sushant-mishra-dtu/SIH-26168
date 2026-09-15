# Handover — ZARU gate: why 1,356 of 1,372 stops on S3a observe nothing, and the fix to measure

**Written:** 15 Sep 2026, after the audit of D-130 (`main` at `5ef4c55`). **Seat S (filter).**
Self-contained: everything you need is in this file, the files it names, and the commands it gives.
Companion to [`HANDOVER.md`](HANDOVER.md) (the wider filter/Gate 1 state) and to
[`../models/HANDOVER_P08.md`](../models/HANDOVER_P08.md), which a second person is working from
**at the same time** — §0 says how the two of you stay out of each other's way. Read §0 first.

Where this file disagrees with [`../docs/DECISION_LOG.md`](../docs/DECISION_LOG.md), the log wins.

> **Status, 15 Sep 2026 evening — done; D-131 is the record.** Code `dd5e3ff` (`update_zaru(gyro,
> sigma=)`, `zaru_sigma_from_window`, `eval/run.py::ZARU_SIGMA_FROM_WINDOW`), artefacts and row in
> the commit after it, both clean-stamped. The candidate that shipped is C read at the stop itself:
> R per axis from the detector window's own sample std, floored at the desk figure. A rejected
> 98.8 % on S3a became 99.1 % applied — **and the bias estimate did not move, and the quiet ratio
> is 6.14× against 6.27×, a wash.** §8's questions are answered in the row: (1) the standstill
> level is half the warm-up level on S1 and is not one number across TRAIN; (2) the widened gate
> admits the run-out and nothing else refuses it, at a measured cost ≤ 0.008 °/s; (3) `b_g` on S3a
> does not converge, because the bias block is over-confident 3–7× (0.03 °/s claimed, 0.2–0.4
> °/s walked) and ZARU's gain against it is 7e-4 per sample; (4) the remaining gap is the bias
> block's consistency, not observability — `HANDOVER.md` §11 (4) says what to measure next. The
> probes are in the 15 Sep evening session's scratchpad (`zaru_measure.py`, `zaru_objective.py`,
> `nees_means.py`); `zaru_objective.py`'s "before" arm reproduces D-130 to the digit and is the
> template for any on/off A/B of a filter change through `run_filter` + `replay_window`.
>
> **The next piece of work is briefed in [`HANDOVER_BIAS.md`](HANDOVER_BIAS.md)** (the gyro-bias
> block's consistency, row D-133 reserved). Nothing below this block needs doing; it is kept as
> the record of what was asked and what the answer turned out to be.

---

## 0. Parallel-work protocol (both handovers carry this section verbatim)

Two branches from `main`, two worktrees, two owners. Nothing is pushed by anyone.

| | ZARU (this file) | P-08 (`models/HANDOVER_P08.md`) |
|---|---|---|
| Branch | `zaru-gate` | `p08-speed-head` |
| Worktree | `C:\g1\wt_zaru` | `C:\g1\wt_p08` |
| Python | `<repo>\.venv\Scripts\python.exe` (3.13, numpy/pandas/pytest/ruff; **no torch**) | `C:\Users\MANISH KUMAR\AppData\Local\Programs\Python\Python312\python.exe` (ROCm torch 2.9.1, GPU) |
| DECISION_LOG row | **D-131** (reserved) | **D-132** (reserved) |
| Owns (may edit) | `core/reference/inekf.py`, `eval/run.py`, `eval/figures/summary.json`, `eval/figures/windows.csv`, `eval/figures/trajectory_*.json`, `tests/test_filter.py`, `tests/test_se23_derivation.py`, `tests/test_harness_wiring.py`, `tests/test_ffi_contract.py`, `core/HANDOVER.md`, this file | `models/**` (new `train_speed_head.py`, `README.md`), new `tests/test_speed_head*.py`, new `eval/figures/speed_head_*` files, `models/HANDOVER_P08.md` |
| Must not touch | anything in the P-08 column; `android-ui/`, `android/`, `graphify-out/`; `.venv` (no pip installs); `eval/figures/allan_*` | anything in the ZARU column; `android-ui/`, `android/`, `graphify-out/`; `.venv`; `eval/figures/summary.json` / `windows.csv` / `trajectory_*` |
| Shared, append-only | `docs/DECISION_LOG.md` — append your reserved row at the end; on a merge conflict keep both rows, ordered by ID | same |

Setup (run from the repo root, once):

```text
git -c core.longpaths=true worktree add C:\g1\wt_zaru -b zaru-gate main
cmd /c mklink /J "C:\g1\wt_zaru\data\IO-VNBD" "C:\Users\MANISH KUMAR\Desktop\My Projects\SIH-26168\data\IO-VNBD"
```

- **Use `mklink /J`, never `ln -s`.** Git Bash's `ln -s` on this box silently *copies* the 2.1 GB
  dataset (verified 15 Sep). `data/README.md` and `data/manifest/` are tracked and already in the
  worktree; only `IO-VNBD` needs the junction. Before removing the worktree: `rmdir C:\g1\wt_zaru\data\IO-VNBD`
  (removes the junction, not the data), then `git worktree remove C:\g1\wt_zaru`.
- Work **inside the worktree** (`cd C:\g1\wt_zaru`); `python -m ...` puts the cwd first on `sys.path`
  so `core`/`eval`/`idr` resolve from the worktree and `idr.stamp` reads *its* clean sha. The main
  checkout carries someone else's uncommitted `android-ui/` work — never `git stash` it, never stage it.
- Stage by explicit path only. Never `git add -A` / `git add .`.
- Finishing: `git rebase main` on your branch, `ruff check .` + `pytest -q` green, then fast-forward
  `main` (`git checkout main && git merge --ff-only zaru-gate`) from the **main checkout**. Whoever
  merges second rebases. Never push.
- `CHANGELOG.md` is the operator-UI (android-ui) changelog; neither of you adds a line.

---

## 1. The problem, in numbers you can re-derive

Gate 1 (physics-only InEKF within 3–5× of the GNSS-available baseline, median drift-% at 60 s) sits
at **6.27× on the quiet-mount stems** S3a + S3c (57.2% / 9.13%, 101 windows) and 19.5× on the
vibrating-mount stems, commit `7e3a8b0`, D-130. Per stem at 60 s: S3a 42.0% / 8.18% = **5.1×**,
S3c 69.5% / 10.62% = 6.5×. To reach 5× on the quiet class the filter median must fall to ≤ 45.6%.

The named root cause (D-115, confirmed D-130): the gyro bias `b_g` is wrong when every outage
window opens, because nothing observes it directly. ZARU is the only update that does
(`z = ω̃ − b̂_g`, `H = [0 0 0 −I 0 0]`, SE23_PROPAGATION.md §7.3). D-130's Fix 1 made the stop
detector fire on S3a (1,372 stops detected, ZUPT applied at each). **ZARU was then refused at its
own χ² gate 1,356 times out of 1,372** (`eval/figures/summary.json` → `aided_pass.S3a`:
`n_zaru_applied 16, n_zaru_rejected 1356`). S3c: 241 / 1,283. Vw2: 2 / 737. Vta1a: 0 / 2.

Why, read from the code and one probe (no tuning, nothing changed):

| Quantity | Value | Where |
|---|---|---|
| `FilterConfig.zaru_sigma` (the ZARU measurement σ) | `GYRO_ARW_MEASURED * sqrt(10 Hz)` = 6.894e-4 rad/s = **0.0395 °/s** | `core/reference/inekf.py:319` — the Allan run's white noise per sample on a *desk* (D-120) |
| `chi2_gate_3dof` | 11.345 (99 %, 3 dof) | `inekf.py:343` |
| Standstill per-sample gyro std, TRAIN stem S1 (truth-stopped samples) | **[1.01, 0.56, 0.85] °/s** per axis | probe `stops.py` (§5) |
| Standstill per-sample gyro std, S3a (held-out, diagnostic) | **[0.33, 1.28, 1.37] °/s** | same |
| Standstill *mean* gyro, S3a | 0.015 °/s (a floor, not a bias — D-130) | same |
| In-motion white level the filter already measures per stem and uses for `Q` | S3a 1.64 °/s, S3c 3.19, Vta1a 1.69, Vw2 3.21 per sample | `summary.json` → `aided_pass.<stem>.gyro_arw_used × sqrt(10)`; `eval/run.py::in_motion_config` |

So the ZARU innovation carries ~1 °/s of idle-vibration noise per sample and is tested against
`R = (0.04 °/s)²`: 25–35× too small in σ, 600–1200× in variance. Its χ² distance is in the hundreds,
the gate refuses, and the bias stays unobserved. `in_motion_config` raises `gyro_arw`/`accel_vrw`
to the stream's own white level (×22 on S3a) but **does not touch `zaru_sigma`**, which stays the
desk figure — an inconsistency between the process model and the ZARU measurement model, not a
tuning question. `update_zaru`'s docstring (`inekf.py` ~1344) records the gate being measured at a
2.0 % rejection rate — on the *synthetic* 60 s scenario whose noise is the Allan level. On the
real stream the rejection rate is 98.8 %.

## 2. What a legitimate fix looks like — and the trap in it

**Rules that bind (AGENTS.md, D-115, HANDOVER.md §3).** Every number is measured on TRAIN
(`eval/splits.py::TRAIN`: M, S1, S2, S4 are the ones with ≥ 5 s stops); S3a/S3c/Vta*/Vw* may be
printed as a diagnostic and never used to set a value. Nothing is tuned to the 3–5× target: measure
before and after on the same commit pair, both numbers go in D-131, a worse number ships off with
the reason. Before/after are both **clean-stamped** sweeps (§6). Fix the mechanism, not the number.

**Three candidates. Measure, then pick — do not pick first.**

- **A — derive `zaru_sigma` from the per-stem white level the filter already carries.** `R_zaru =
  (cfg.gyro_arw · √rate)²` evaluated on the *in-motion* config, i.e. the same `stream_white_level`
  measurement `in_motion_config` makes on the warm-up. No new constant; the identity
  `zaru_sigma = gyro_arw · √rate` that `test_zaru_sigma_is_derived_from_the_allan_run_not_typed`
  and `test_zaru_sigma_is_the_gyro_white_noise_the_repo_measured` pin is *kept* — it just has to
  hold after `in_motion_config` too. Check first whether the standstill std ≈ the in-motion white
  level on TRAIN (S1: 0.56–1.01 °/s at rest vs its warm-up level — measure it); if the standstill
  level is materially lower, A over-widens R and under-weights ZARU.
- **B — ZARU on the detector's window mean.** `is_stationary` already averages 20 samples; feed
  `update_zaru` the window mean with `R = σ²/N` (σ the per-sample level). Averages the vibration
  down by √20 ≈ 4.5×. Changes D-052's "raw sample" contract and the ZARU H/R derivation in
  SE23_PROPAGATION.md §7.3 — needs a paragraph there, and the 20-sample mean lags the true rate
  by 1 s, which matters at pull-away (below).
- **C — the standstill level measured on the real stream at rest, on TRAIN** (per-sample gyro
  white level over every ≥ 5 s truth stop on M/S1/S2/S4, worst axis, in the `zupt_*` comment
  style; per-run `stream_white_level` so a slow drift does not inflate it). This is what D-115
  meant by "ZARU's R is the standstill figure" (§3, `test_harness_wiring.py:732`) with the figure
  actually measured in a car instead of on a desk — the candidate that keeps the existing
  argument. Its weakness: a constant. A phone that rattles more than TRAIN at rest (S3c) is still
  partly gated out; one that rattles less is under-weighted. A per-stem variant (measure it on the
  stem's own first detected stop, the way `in_motion_config` reads the warm-up) is C without the
  constant and is worth measuring alongside.

**The trap — D-057 must keep holding.** The gate exists because at the pull-away step the 2 s
detector window still says "stopped" while the true yaw rate is already ~0.05 rad/s (2.9 °/s);
that one sample, applied ungated, was the whole of the gyro-bias block's over-confidence (χ² 1456
against 11.345; NEES 13.14 → 3.05 gated). Widen R to 1.4 °/s and a 2.9 °/s transition sample has
χ² ≈ 4 per axis — **it passes.** So whichever candidate you pick, measure on TRAIN, at the last
detector-positive sample before each true pull-away: the true yaw rate (from the `V-` course, as
`yawcheck.py` does), the innovation, and whether the widened gate admits it. The harness's state
veto (`ZUPT_VETO_MIN_SPEED_MPS = 1.0`, `ZUPT_VETO_NSIGMA = 3.0` in `eval/run.py`) refuses the
run-*in* to a stop; check what refuses the run-*out*. If nothing does, the fix needs a companion
(a shorter trailing check on the last k samples, or B's averaging plus a veto) and the row says so.

**Also measure, because it is the actual objective:** after the fix, the aided pass's `b_g` on S3a
in the last ten minutes (D-115: walks to 0.3–0.5 °/s; whole-file mean 0.01) — does it now converge?
`aided.py` (§5) prints it. And the 60 s window speed error at 60 s (D-115: −3 to −17 m/s) —
`windows_probe.py`.

## 3. Files, tests, and what pins what

| File | What is there | What changes |
|---|---|---|
| `core/reference/inekf.py` | `FilterConfig.zaru_sigma` (319), `chi2_gate_3dof` (343), `update_zaru` (~1344, docstring carries the D-057 measurement), `_apply_update(..., allow_bias=)` | the R used by ZARU; the docstring must say what σ it is now and where it was measured |
| `eval/run.py` | `in_motion_config` (362) — per-stem `gyro_arw`/`accel_vrw`; `_step_constraints` (~657) calls `is_stationary(..., gyro_bias=st.b_g)`, `update_zupt()`, `update_zaru(gyro[k])`; `ZUPT_VETO_*` (640) | A: derive `zaru_sigma` here; B: pass the window mean |
| `tests/test_filter.py:347` | `test_zaru_sigma_is_derived_from_the_allan_run_not_typed` pins `zaru_sigma == gyro_arw·√rate == 6.894e-4` | keep the identity, re-pin the value only if the default changes |
| `tests/test_se23_derivation.py:1095` | `test_zaru_sigma_is_the_gyro_white_noise_the_repo_measured`, and the five `test_11_nees_*` (bands [16.843, 19.195]; ZARU-only and full-state one-sided). **Bands and `NEES_RUNS` are never edited.** Re-run all five; a miss is reported, not widened | |
| `tests/test_harness_wiring.py:732` | `test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it` asserts `loud.zaru_sigma == cfg.zaru_sigma` — "ZARU's R is the standstill figure and stays" (D-115's deliberate choice: the in-motion level is not the standstill level) | A contradicts this assertion head-on. The honest reading is that D-115 was right that ZARU's R is the *standstill* figure and wrong about what that figure is: the Allan desk run says 0.04 °/s, the same phone at rest in a car says 0.56–1.0 °/s (S1). So C — the standstill level **measured on the real stream at rest, on TRAIN** — is the candidate that keeps D-115's argument and fixes its number; D-131 must say so and this assertion is re-pinned, not deleted |
| `tests/test_ffi_contract.py:53` | `zaru_sigma` is on the FFI config surface | name stays |
| `docs/SE23_PROPAGATION.md` §7.3, `docs/ERROR_BUDGET.md` §3.2 | ZARU derivation; what residual bias costs | B needs a §7.3 note |
| `docs/DECISION_LOG.md` D-052, D-053, D-057, D-115, D-130 | raw-sample contract; consistency; the gate; the diagnosis; the current state | append **D-131** |

## 4. Acceptance — D-131 in the D-130 format

Same table shape as D-130 (5 columns; escape any `|` inside a cell as `\|`):

1. The measurement first: TRAIN standstill gyro std per stem and axis; in-motion white level per
   stem; pull-away innovation vs gate under old and new R; then S3a/S3c as diagnostics.
2. The candidate chosen and the two rejected, with the numbers that decided it.
3. Before (`7e3a8b0` or `5ef4c55`, clean) vs after (your commit, clean), at 60 s, **quiet and
   vibrating split and pooled**, with window counts; 10 s quiet; per-stem S3a/S3c; the aided-pass
   counters `n_zaru_applied / n_zaru_rejected` for S3a, S3c, Vw2; replay divergences; skipped stems.
4. The five NEES means against their bands.
5. The verdict against 3–5× in plain words. No "nearly", "effectively", "close to". If it does not
   close, say which part of the remaining gap is which.
6. Artefacts: `eval/figures/summary.json`, `windows.csv`, `trajectory_*.json` from the clean sweep,
   stamped `commit <sha> | seed 0`, **no `-dirty`, no `nogit`**. Two commits: code
   (`fix(filter): ...`) then artefacts + row (`chore(figures): Gate 1 sweep at <sha> (D-131)`).
7. `core/HANDOVER.md` §1, §2, §8, §11 updated to the new number.

## 5. Probes that already exist — copy, fix one `sys.path` line, do not rewrite

Session scratchpads under
`C:\Users\MANISH~1\AppData\Local\Temp\claude\C--Users-MANISH-KUMAR-Desktop-My-Projects-SIH-26168\<session>\scratchpad\`:

- `0f5cc559-…` (15 Sep, the audit): `stops.py` — detector recall / rolling false-fire per stem
  **with the committed rule and the per-axis standstill std printed** (the §1 numbers);
  `diag.py` (loader: `load(stem)`, `truth_ned_per_sample`); `accel_turnon2.py` (clock-restart-safe
  loader for M/S2/S4 — three TRAIN stems restart their clock mid-file, `assert_uniform_grid` raises;
  take the monotonic prefix); `perstem.py` (Gate 1 split from `windows.csv`).
- `59b04088-…` (13 Sep): `aided.py` (whole stem through `run_filter`, prints `b_g` over time),
  `windows_probe.py` (60 s replay, speed/heading split), `yawcheck.py` (gyro yaw rate vs truth
  course rate — reuse for the pull-away yaw rate), `zuptcheck.py`.
- `ad3ced7c-…` (15 Sep, the fix session): `ab_hold.py` (replays every 60 s window of S3a+S3c from
  the same snapshots under two settings — the template for an on/off A/B of your change),
  `vta16_probe.py` (runs one stem four ways with fixes toggled).
- Reference sweeps: `%TEMP%\g1\sweep_before` (b8bc3ee), `%TEMP%\g1\sweep_after` (7e3a8b0 = committed),
  `C:\g1\sweep_audit` (7e3a8b0 re-run, byte-identical), `C:\g1\ab_hold_audit.json`.

## 6. Commands

```text
cd C:\g1\wt_zaru
"<repo>\.venv\Scripts\python.exe" -m pytest -q                       # 823 tests, ~3 min
"<repo>\.venv\Scripts\ruff.exe" check .
"<repo>\.venv\Scripts\python.exe" -m pytest tests\test_se23_derivation.py -k nees -q   # ~2.5 min
"<repo>\.venv\Scripts\python.exe" -m eval.run --data "<repo>\data\IO-VNBD" --out C:\g1\sweep_zaru   # ~7 min
                                                                     # first line of windows.csv must read
                                                                     # "# commit <sha> | seed 0 | ..." — clean
```

Commit the code first, then sweep **from that commit** (a sweep from an uncommitted tree stamps
`-dirty` and cannot be quoted), then copy `summary.json`, `windows.csv`, `trajectory_*.json` into
`eval/figures/` and commit them with the row.

## 7. Time budget and the stop rule

Measure 45 min · code + tests 45 min · NEES + full pytest 10 min · two sweeps 15 min · row 30 min
≈ **2.5–3 h**. One attempt, measured honestly, is the deliverable — not a second attempt with a
different number. If the quiet ratio does not reach 5×, D-131 says so and says why, and the
project's stop rule applies (phases.md P-07: submit physics-only honestly). Gate 1 is signed by a
human, never by this row.

## 8. Open questions this work will answer (put the answers in the row)

1. Is the standstill gyro std on TRAIN the same level as the in-motion white level, or lower?
   (Decides A vs C.)
2. With the widened gate, does the pull-away sample get in, and what refuses it if so?
3. Does `b_g` on S3a converge once ZARU runs, and does the 60 s speed collapse shrink with it?
4. Is the remaining quiet-class gap still bias observability, or now the accelerometer bias /
   9 s aiding cadence D-115 also named?
