# Handover — P-08: the speed + variance head, trained and calibrated (code, then a GPU run)

**Written:** 15 Sep 2026, after the audit of D-130 (`main` at `5ef4c55`). **Seat M.**
Self-contained. Companion to [`../core/HANDOVER.md`](../core/HANDOVER.md) (filter / Gate 1 state)
and to [`../core/HANDOVER_ZARU.md`](../core/HANDOVER_ZARU.md), which a second person is working
from **at the same time** — §0 says how the two of you stay out of each other's way. Read §0 first.

Where this file disagrees with [`../docs/DECISION_LOG.md`](../docs/DECISION_LOG.md) or
[`../phases.md`](../phases.md), those win.

---

## 0. Parallel-work protocol (both handovers carry this section verbatim)

Two branches from `main`, two worktrees, two owners. Nothing is pushed by anyone.

| | ZARU (`core/HANDOVER_ZARU.md`) | P-08 (this file) |
|---|---|---|
| Branch | `zaru-gate` | `p08-speed-head` |
| Worktree | `C:\g1\wt_zaru` | `C:\g1\wt_p08` |
| Python | `<repo>\.venv\Scripts\python.exe` (3.13, numpy/pandas/pytest/ruff; **no torch**) | `C:\Users\MANISH KUMAR\AppData\Local\Programs\Python\Python312\python.exe` (ROCm torch 2.9.1, GPU) |
| DECISION_LOG row | **D-131** (reserved) | **D-132** (reserved) |
| Owns (may edit) | `core/reference/inekf.py`, `eval/run.py`, `eval/figures/summary.json`, `eval/figures/windows.csv`, `eval/figures/trajectory_*.json`, `tests/test_filter.py`, `tests/test_se23_derivation.py`, `tests/test_harness_wiring.py`, `tests/test_ffi_contract.py`, `core/HANDOVER.md`, `core/HANDOVER_ZARU.md` | `models/**` (new `train_speed_head.py`, `README.md`), new `tests/test_speed_head*.py`, new `eval/figures/speed_head_*` files, this file |
| Must not touch | anything in the P-08 column; `android-ui/`, `android/`, `graphify-out/`; `.venv` (no pip installs); `eval/figures/allan_*` | anything in the ZARU column; `android-ui/`, `android/`, `graphify-out/`; `.venv`; `eval/figures/summary.json` / `windows.csv` / `trajectory_*`; **`core/reference/inekf.py` — fusing the head (`update_speed`) is P-09, not this** |
| Shared, append-only | `docs/DECISION_LOG.md` — append your reserved row at the end; on a merge conflict keep both rows, ordered by ID | same |

Setup (run from the repo root, once):

```text
git -c core.longpaths=true worktree add C:\g1\wt_p08 -b p08-speed-head main
cmd /c mklink /J "C:\g1\wt_p08\data\IO-VNBD" "C:\Users\MANISH KUMAR\Desktop\My Projects\SIH-26168\data\IO-VNBD"
```

- **Use `mklink /J`, never `ln -s`.** Git Bash's `ln -s` on this box silently *copies* the 2.1 GB
  dataset (verified 15 Sep). `data/README.md` and `data/manifest/` are tracked and already in the
  worktree; only `IO-VNBD` needs the junction. Before removing the worktree: `rmdir C:\g1\wt_p08\data\IO-VNBD`
  (removes the junction, not the data), then `git worktree remove C:\g1\wt_p08`.
- Work **inside the worktree** (`cd C:\g1\wt_p08`); `python -m ...` puts the cwd first on `sys.path`
  so `models`/`eval`/`idr` resolve from the worktree and `idr.stamp` reads *its* clean sha. The main
  checkout carries someone else's uncommitted `android-ui/` work — never `git stash` it, never stage it.
- Stage by explicit path only. Never `git add -A` / `git add .`. `*.pt`/`*.pth`/`*.onnx`/`*.tflite`
  and `checkpoints/`, `runs/` are git-ignored — checkpoints are not committed; the figure and the row are.
- Finishing: `git rebase main` on your branch, `ruff check .` + `pytest -q` green **in the 3.13 venv**
  (the CI environment: no torch — your tests must skip or refuse cleanly there, §5), then fast-forward
  `main` (`git checkout main && git merge --ff-only p08-speed-head`) from the **main checkout**.
  Whoever merges second rebases. Never push.
- `CHANGELOG.md` is the operator-UI (android-ui) changelog; neither of you adds a line.

---

## 1. What P-08 is, and the one rule that scopes it

phases.md P-08 (verbatim, the parts that bind):

> Train the speed + variance head on S- channels only. The architecture, the log-variance
> parameterisation, the Gaussian NLL and the calibration metric are already written in
> `models/speed_head.py`. **THE GATE 2 CRITERION IS CALIBRATION, NOT ACCURACY:** at least 95% of
> speed errors inside ±2 sigma of the predicted variance. Produce the predicted-sigma-vs-realised-error
> plot, stamped. Report coverage first, RMSE second. S- channels only, verified through the leakage
> guard on the ACTUAL feature tensor. Never double-integrate acceleration to obtain the speed target
> (H-2). Do not reuse pedestrian weights (D-017). Export FP16 only (D-012).

**Exit criteria:** ≥ 95 % coverage within ±2σ on held-out; calibration plot stamped and in the
figure set; leakage-guard output pasted in the row.

**The scoping rule.** phases.md marks P-08 "Blocked until Gate 1 is signed off by the human" and
H-4 says no learned component is *added* to the filter before then. Gate 1 is **not** signed
(D-130: 6.27× quiet / 19.5× vibrating against 3–5×; the ZARU work in the other handover is the
next attempt). What this handover therefore covers, decided 15 Sep:

- **Write the training script and its tests. Train on the GPU. Measure calibration. Write D-132.**
  None of that adds anything to the filter; it is the thing that has to exist before P-09 can be
  argued at all.
- **Do not fuse.** `InEKF.update_speed` exists and stays unused. P-09 (fusing the head as a
  pseudo-measurement with its predicted `R`) waits for a signed Gate 1 or for a DECISION_LOG row
  that says, in plain words, that it is being done with Gate 1 unsigned and why.
- D-132 states this scoping in its first sentence, so nobody reads a trained head as a cleared gate.

## 2. What already exists — read before writing anything

| File | What it is | State |
|---|---|---|
| `models/speed_head.py` (111 lines) | `SpeedHead`: causal dilated TCN, channels (32, 64, 64), input `(batch, 9, 20)` = 2 s at 10 Hz of **accel xyz, gravity xyz, gyro xyz** in the body frame; outputs `(speed_mps, variance)`, variance = `exp(log_var)` clamped at `MIN_VARIANCE = 1e-4`. `gaussian_nll` (heteroscedastic). `calibration_fraction(pred, var, target, n_sigma=2.0)` — the Gate 2 metric. Docstring cites D-003 (never double-integrate), D-017 (no pedestrian weights) | written; **no test exists** (`grep speed_head tests/` is empty; phases.md's "and tested" is not true today); never trained |
| `models/train_baseline_rnn.py` (678 lines) | The Onyekpe INS RNN reproduction script — **the template.** `Hyperparameter` audit table (every value cites its row or says OMITTED); `assert_features_are_clean()` runs `eval.loaders.columns.assert_feature_safe` over `FEATURE_COLUMNS` and returns the report to paste; `epoch_windows(seq, truth)` builds per-second windows with the target from the paired `V-` truth track (lat/lon differenced — the only permitted use of `V-`); `validation_families()` holds whole TRAIN *families* out for early stopping (D-098; a family straddling a split is leakage); `Scaler.fit` on TRAIN only (D-071); `load_windows` reports the three TRAIN stems that restart their clock (M, S2, S4) rather than silently dropping them; torch imported inside `main` so the harness never blocks on it; refuses with a non-zero exit when torch is absent (`tests/test_baseline_audit.py`) | the pattern to mirror, function for function |
| `models/baseline_rnn.py` | the RNN itself | leave alone |
| `models/README.md` | contract: every network outputs an uncertainty; never double-integrate; no pedestrian weights; no network before Gate 1 clears; FP16 export; body-frame input with attitude encoding (AirIO), window 1–2 s | update its Status section at the end |
| `eval/loaders/columns.py` | `ALLOWED_COLUMNS` (inertial ∪ time ∪ GNSS), `DENY_PATTERN`, `assert_feature_safe`, `assert_no_leakage` | the guard; call it on the exact channel list you feed the tensor |
| `eval/loaders/truth.py` | `load_truth`, `paired_truth_path`, `align_to_sequence`; **rejects any velocity column at the header** — the speed target is differenced lat/lon, nothing else | |
| `eval/run.py` | `imu_stream(seq)`, `assert_uniform_grid`, `truth_clock_offset_s`, `_level_sigma` / the warm-up levelling, `in_motion_config` | reuse the loader path; do not edit this file (ZARU owns it) |
| `eval/splits.py` | `TRAIN` (19 stems), `test_sequences()`, `stem_family`, `assert_no_family_straddles_the_split`, `QUIET_MOUNT` | |
| `idr/stamp.py` | `Stamp`, `Stamp.caption()`, `stamp_figure(fig, stamp)` (needs matplotlib) | every artefact carries `commit <sha> \| seed <n>`; `-dirty` / `nogit` may not be quoted |
| `tests/test_leakage.py`, `tests/test_baseline_audit.py` | how the guard and the no-torch contract are tested | mirror for the new script |

## 3. The design decisions the script has to make — with the evidence already on file

1. **What the head predicts.** phases.md says "forward speed". `train_baseline_rnn.py`'s D-099
   comment records the measurement that a **1 s IMU window does not contain absolute speed**: over
   TRAIN, per-epoch travel has σ 5–8 m while its epoch-to-epoch *change* has σ 0.67–0.77 m; a net
   trained on absolute distance did no better than predicting the training mean (3.54 m vs 3.89 m
   MAE). A 2 s window will face the same objection. Before committing to absolute speed, measure
   on TRAIN validation whether the head beats the constant-mean baseline; if it does not, the
   defensible target is **Δspeed over the window** (the D-064 concession: speed at outage entry is
   known from GNSS, a real system has it), fused later as an increment. Whichever you choose, the
   variance head is trained on that quantity and D-132 says which and why.
2. **Calibration can be gamed, so report sharpness beside coverage.** A head that predicts
   σ = 10 m/s everywhere has 100 % coverage and is useless to the filter. Gate 2 says coverage
   first; the row must also carry mean predicted σ, RMSE, and the coverage at ±1σ (expected ≈ 68 %)
   and ±3σ (≈ 99.7 %) — a calibrated head hits all three, an inflated one over-covers all of them.
   A reliability diagram (predicted σ bins vs realised RMSE in each) is the plot phases.md asks for.
3. **The gravity channels.** `N_INPUT_CHANNELS = 9` includes gravity in the body frame, which
   needs an attitude. Options: (a) the warm-up levelling the harness already computes
   (`eval/run.py::_level_sigma` and the alignment block) — consistent with what the filter would
   supply at deployment; (b) a causal low-pass of the accelerometer — simple, self-contained, lags
   in turns. Pick one, say which, keep it causal (the TCN is causal for a reason: no future window
   at deployment). Never a truth-derived attitude — that is a `V-` quantity in disguise.
4. **Split for early stopping.** Whole TRAIN families held out (`validation_families`, D-098),
   never single stems from a family. The held-out set for the Gate 2 number is
   `eval.splits.test_sequences()`, touched **once**, at the end, with the frozen weights.
5. **Windows and stride.** 20 samples (2 s); stride to decide (1 s matches `train_baseline_rnn`).
   Windows that touch a truth gap are dropped, not the stem (D-089's rule as `epoch_windows` applies
   it). The three clock-restart stems (M, S2, S4): use the monotonic prefix rather than dropping
   them — `assert_uniform_grid` raises on the restart; take samples before it
   (`C:\Users\MANISH~1\AppData\Local\Temp\claude\...\0f5cc559-…\scratchpad\accel_turnon2.py` has a
   working loader that does this).
6. **Normalisation.** Fitted on TRAIN windows only (D-071), ranges saved with the checkpoint.
7. **Seed and stamp.** `idr.stamp.seed_everything`-style determinism (see how `eval.run` seeds);
   the checkpoint's metadata and the figure carry the stamp. A run from a dirty tree is a scratch
   run and is not quoted.

## 4. Environment — what actually runs on this box (verified 15 Sep)

```text
# the GPU interpreter — NOT the repo venv
"C:\Users\MANISH KUMAR\AppData\Local\Programs\Python\Python312\python.exe" -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
#   -> 2.9.1+rocmsdk20260116 True AMD Radeon RX 7700 XT      (ROCm/HIP 7.2; torch.cuda.* is the API on ROCm too)
```

That interpreter has torch and numpy but **no pandas, no matplotlib, no pytest** and does not have
the repo installed. Add what the loaders need into *that* interpreter, not `.venv`:

```text
"C:\Users\MANISH KUMAR\AppData\Local\Programs\Python\Python312\python.exe" -m pip install pandas matplotlib pytest
```

Run scripts from the worktree root so `models`/`eval`/`idr` import from cwd (`python -m models.train_speed_head ...`).
Check the repo's `pyproject.toml` `ml` extra (`torch>=2.0`) and `plot` extra before adding anything
else, and record every package you added in D-132. The 3.13 `.venv` stays torch-free on purpose
("the harness is the critical path and must never be blocked on a torch install", pyproject.toml).

Sanity before a long run: a 30-second smoke fit on two TRAIN stems, `torch.cuda.is_available()`
printed at start, and the device the model actually landed on printed with it. ROCm on Windows is
new enough that a silent CPU fallback is the failure to look for.

## 5. Deliverables

1. `models/train_speed_head.py` — mirrors `train_baseline_rnn.py`: `Hyperparameter` audit table
   (every value cites a row or is OMITTED with a reason), `assert_features_are_clean()`,
   `build_windows` (target from differenced truth), `validation_families`, `Scaler`, `train`
   (NLL, early stopping on validation NLL or coverage — say which), `evaluate` (coverage at
   ±1/2/3σ, mean σ, RMSE, per-stem table on held-out), `plot` (reliability diagram +
   predicted-σ-vs-|error| scatter, `stamp_figure`), `export` (FP16 `state_dict` and, if it works
   on ROCm, an ONNX/`.pte` — otherwise say so), torch imported inside `main`, non-zero exit without it.
2. `tests/test_speed_head.py` — runs **without torch** where it can (shape contract via
   `pytest.importorskip("torch")` for the model tests; the window builder, the target derivation,
   the guard call and the calibration bookkeeping tested with numpy). Plus one test in the style of
   `test_baseline_audit.py` that the script refuses without torch. `pytest -q` in the 3.13 venv
   must stay green: **829 → 829 + yours**, nothing skipped silently.
3. `eval/figures/speed_head_calibration.png` and `eval/figures/speed_head_summary.json` (stamp,
   split, window counts, coverage at 1/2/3σ, mean σ, RMSE, per-stem rows, the leakage-guard report
   text, hyperparameters). New file names only — `summary.json`/`windows.csv` belong to the sweep.
4. `models/README.md` Status section updated.
5. **D-132** in `docs/DECISION_LOG.md`, D-130's table format (escape in-cell `|` as `\|`):
   first sentence = the scoping (trained and calibrated, **not fused**, Gate 1 unsigned); what the
   head predicts and why (decision 1 with its measurement); the guard output; the split and counts;
   coverage-first results with sharpness; what was exported; what was not done. No "nearly",
   "effectively", "close to".
6. Commits: `feat(models): speed + variance head training script` (code + tests), then
   `chore(figures): speed head calibration at <sha> (D-132)` (figure + summary + row + README).
   Checkpoints are not committed; say where the `.pt` lives.

## 6. Time budget

Script + tests ≈ 2.5 h · smoke run 15 min · full run: unknown until the first epoch time is seen
(19 TRAIN stems at 10 Hz is small — expect minutes, not hours, on the 7700 XT) · evaluation + plot
30 min · row 30 min. If ROCm misbehaves, the CPU path is viable for this data size; say which ran.

## 7. Questions this work will answer (put the answers in D-132)

1. Does a 2 s body-frame window carry absolute speed on TRAIN, or only Δspeed (decision 1)?
2. Is the variance head calibrated *and* sharp, or calibrated by inflation?
3. Which stems are worst, and is the pattern the mount class (`QUIET_MOUNT` vs the rest) that
   D-115 found for the gyro?
4. Does the ROCm wheel train on the GPU on this box, and how long is an epoch?
