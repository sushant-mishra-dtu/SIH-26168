"""Training entry point for the Onyekpe INS baseline reproduction (P-06).

    python -m models.train_baseline_rnn --data data --seed 0

**Read `HYPERPARAMETERS` before running this.** The published papers state some of the settings
below and are silent on others, and every silence is a choice *we* are making. The table
distinguishes the two explicitly, and each omission carries a DECISION_LOG id rather than sitting
as a bare constant in a config file -- a reproduction whose gaps are invisible is not a
reproduction, it is a model with a citation attached.

Requires the `ml` extra (`pip install -e ".[ml]"`). torch is deliberately absent from CI: the
harness is the critical path and must never block on a 2 GB download.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import numpy as np

from eval.outages.inject import OUTAGE_LENGTHS_S

# --------------------------------------------------------------------------------------------
# What the papers state, and what they do not
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Hyperparameter:
    name: str
    value: str
    source: str
    #: "" where the paper states it; a DECISION_LOG id where we had to choose.
    decision: str = ""

    @property
    def is_our_choice(self) -> bool:
        return bool(self.decision)


#: Every setting the reproduction depends on. `--audit` prints it, and the phase requires it to be
#: read before anything trains. Sources: docs/DATASETS.md section 3, itself transcribed from
#: Onyekpe et al., "Learning to Localise Automated Vehicles in Challenging Environments" and the
#: WhONet paper (arXiv 2104.02581).
HYPERPARAMETERS: tuple[Hyperparameter, ...] = (
    Hyperparameter("window", "1 s = 10 samples at 10 Hz", "stated (INS paper)"),
    Hyperparameter("model", "vanilla RNN, 1 hidden layer, 72 units", "stated (INS paper)"),
    Hyperparameter("dropout", "0.05", "stated (INS paper)"),
    Hyperparameter("batch size", "128", "stated (INS paper)"),
    Hyperparameter("learning rate", "7e-4", "stated (INS paper)"),
    Hyperparameter("optimiser", "Adamax", "stated (WhONet paper), NOT surfaced in the INS paper"),
    Hyperparameter("loss", "MAE", "stated (WhONet paper), NOT surfaced in the INS paper"),
    Hyperparameter("input scaling", "features scaled 0-1", "stated (INS paper)"),
    Hyperparameter("framework", "Keras/TF; we reimplement in PyTorch", "stated"),
    # ---- silences, resolved by D-098. Each value below is ours, not the papers'. ----
    Hyperparameter("epochs", "200 cap, early-stopped", "OMITTED by both papers", decision="D-098"),
    Hyperparameter(
        "early stopping / patience", "20 on val MAE, best restored", "OMITTED", decision="D-098"
    ),
    Hyperparameter(
        "train/validation split", "4 of 17 TRAIN families, by rule", "OMITTED", decision="D-098"
    ),
    Hyperparameter(
        "weight initialisation", "PyTorch default, seeded", "OMITTED", decision="D-098"
    ),
    Hyperparameter("gradient clipping", "none", "OMITTED", decision="D-098"),
    Hyperparameter(
        "scaler fitting set", "TRAIN windows only, ranges saved", "OMITTED -- a leakage risk",
        decision="D-071",
    ),
    Hyperparameter("LR schedule", "constant 7e-4", "OMITTED", decision="D-098"),
    Hyperparameter(
        "shuffling / window stride", "shuffled; stride = window (10)", "OMITTED", decision="D-098"
    ),
    Hyperparameter(
        "GNSS input noise sigma", "n/a -- no GNSS channel in the INS input",
        "stated as present, magnitude OMITTED", decision="D-098",
    ),
    # ---- and the one the papers do not raise at all ----
    Hyperparameter(
        "regression target", "(d-speed, d-heading) per 1 s epoch",
        "OMITTED -- neither paper says what its INS network regresses", decision="D-099",
    ),
)


def audit_table() -> str:
    """The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in the report."""
    width = max(len(h.name) for h in HYPERPARAMETERS)
    lines = [
        "Onyekpe INS baseline -- what the papers state and what we are choosing",
        "",
        f"{'setting'.ljust(width)}  {'value'.ljust(34)}  source",
        f"{'-' * width}  {'-' * 34}  {'-' * 46}",
    ]
    for h in HYPERPARAMETERS:
        marker = f"  [{h.decision}]" if h.is_our_choice else ""
        lines.append(f"{h.name.ljust(width)}  {h.value.ljust(34)}  {h.source}{marker}")
    stated = sum(not h.is_our_choice for h in HYPERPARAMETERS)
    ours = sum(h.is_our_choice for h in HYPERPARAMETERS)
    lines += [
        "",
        f"{stated} stated, {ours} ours. Every one of the {ours} is a way this reproduction can "
        "differ from",
        "the published number for a reason that is not the method. Report the gap; do not close "
        "it by",
        "search. A reproduction that lands 20% off with a stated reason is a result; one that "
        "lands",
        "exactly on the published number with no explanation is usually a leak.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------
# The nine choices, as constants. Each carries the DECISION_LOG id that argues for it.
# --------------------------------------------------------------------------------------------

#: 1 s at 10 Hz. Mirrors `models.baseline_rnn.WINDOW_SAMPLES` rather than importing it: that
#: module imports torch at module scope, and D-072 keeps *this* file importable in the CI job that
#: has no `ml` extra. `main` asserts the two agree once torch is in hand.
WINDOW_SAMPLES = 10

MAX_EPOCHS = 200  # D-098: a cap, not a target -- early stopping decides
PATIENCE = 20  # D-098
VALIDATION_FRACTION = 0.15  # D-098: share of TRAIN *windows* held back for early stopping
GRAD_CLIP: float | None = None  # D-098: none, matching the papers' silence rather than adding one

#: Channels fed to the network, in this order. All six are `S-` inertial columns; the leakage
#: guard is run over exactly this list in `assert_features_are_clean`, and the run prints it.
FEATURE_COLUMNS = ("gyro_yaw", "gyro_pitch", "gyro_roll", "accel_x", "accel_y", "accel_z")

#: Which two of `StemWindows.y`'s three columns are fitted, per `--target` (D-099).
#:
#: `delta_speed` is the default and the physically defensible one. **A 1 s window of accelerometer
#: and gyro does not contain absolute speed** -- an accelerometer integrates to a *change* in
#: speed, and the measurement is unambiguous: over the TRAIN stems, per-epoch travel has a
#: standard deviation of 5-8 m while the epoch-to-epoch change in it has a standard deviation of
#: 0.67-0.77 m. A network asked for the first can do no better than the conditional mean, and that
#: is exactly what one does: `distance` trains to a validation MAE of 3.54 m against the 3.89 m
#: that predicting the training mean scores without looking at the input at all.
#:
#: Integrating from the entry speed is the same concession `initial_state_from_truth` makes for
#: the strapdown baseline (D-064): GNSS is available at outage entry, so a real system has it.
TARGET_COLUMNS = {"distance": (0, 1), "delta_speed": (2, 1)}
DEFAULT_TARGET = "delta_speed"


def validation_families(windows: list[StemWindows]) -> tuple[str, ...]:
    """The held-back families, by a stated rule rather than by choice (D-098).

    Whole **families**, not stems: `Vw14a/b/c` are one drive minutes apart, so splitting them
    across train and validation would make the early-stopping signal a memory test. This is
    `assert_no_family_straddles_the_split`'s argument applied one level down, to the split inside
    TRAIN that the papers do not describe at all.

    Families are taken **smallest first** until validation holds `VALIDATION_FRACTION` of the
    windows. Two earlier rules were tried and both failed on the same fact -- IO-VNBD's families
    differ by two orders of magnitude in length, and two drives (`S1` 43%, `Vw14` 32%) are most of
    the data:

        every 4th family, sorted   -> 2,461 train windows against 9,472 validation
        sorted until 20% reached   -> validation is `S1` alone, one drive deciding early stopping

    Smallest-first gives a validation set of eleven families across three drivers at ~15% of the
    windows, and leaves both dominant drives in training. All three rules are deterministic; that
    was never the difficulty. The sizes are printed by every run, and a rule that produces a
    lopsided split is visible there before a model is fitted rather than after.
    """
    from eval.splits import stem_family

    per_family: dict[str, int] = {}
    for w in windows:
        per_family[stem_family(w.name)] = per_family.get(stem_family(w.name), 0) + w.x.shape[0]
    target = VALIDATION_FRACTION * sum(per_family.values())
    chosen: list[str] = []
    held = 0
    for fam in sorted(per_family, key=lambda f: (per_family[f], f)):
        if held >= target:
            break
        chosen.append(fam)
        held += per_family[fam]
    if len(chosen) < 3 or held == sum(per_family.values()):
        raise ValueError(f"degenerate validation split: {chosen} holding {held} windows")
    return tuple(sorted(chosen))


def assert_features_are_clean() -> str:
    """Run the repo's own leakage guard over the exact columns the model is fed. Returns a report.

    The phase requires this pasted rather than asserted: the guard is what stands between a
    reproduction and a `V-` wheel-speed column, and a guard nobody watched run is a guard nobody
    knows fired. `assert_feature_safe` raises `LeakageError` on anything that matches the denylist
    or is off the allowlist, so reaching the return statement *is* the result.
    """
    from eval.loaders.columns import DENY_PATTERN, assert_feature_safe

    assert_feature_safe(list(FEATURE_COLUMNS))
    checked = "\n".join(f"    {c:<12} allowed, no denylist match" for c in FEATURE_COLUMNS)
    return (
        f"leakage guard over the {len(FEATURE_COLUMNS)} columns actually fed to the model:\n"
        f"{checked}\n"
        f"    denylist = {DENY_PATTERN.pattern}\n"
        "    assert_feature_safe() returned without raising -- no `V-` column reaches the input."
    )


# --------------------------------------------------------------------------------------------
# Windows and targets
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StemWindows:
    """One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3).

    The three target columns are `(distance, d_heading, d_distance)`. Two of them are fitted, and
    which two is `--target` (D-099): `distance` regresses the second's travel directly,
    `delta_speed` regresses the *change* in it and integrates from the speed at outage entry.
    Both are carried so the comparison costs one training run rather than two data loads.
    """

    name: str
    x: np.ndarray
    y: np.ndarray


def epoch_windows(seq, truth) -> StemWindows:
    """`(x, y)` for one paired sequence: 1 s IMU windows and what the vehicle actually did.

    The target is `(distance, delta-heading)` over the same second (D-099). Neither paper states
    what its INS network regresses; this is the pair that reconstructs a trajectory by dead
    reckoning, which is what the published CTE/CRSE numbers score, so it is the choice that makes
    our number comparable to theirs at all.

    Truth is the paired `V-` VBOX track, permitted as ground truth by EVALUATION.md section 1.2
    and read through `TruthTrack`, which has no `features()` and no inertial channel. A target is
    not an input: the network never sees `V-`, it is only told what the answer was.
    """
    from eval.loaders.truth import MAX_EPOCH_OFFSET_S
    from eval.run import assert_uniform_grid, imu_stream, truth_clock_offset_s

    gyro, accel, t_rel_s = imu_stream(seq)
    assert_uniform_grid(seq.name, t_rel_s)  # raises on the stems that restart their clock (D-013)
    t_abs_s = t_rel_s + truth_clock_offset_s(seq)

    n_epochs = t_rel_s.size // WINDOW_SAMPLES
    if n_epochs < 4:
        raise ValueError(f"{seq.name}: {n_epochs} whole epochs is too few to window")
    bounds = t_abs_s[: n_epochs * WINDOW_SAMPLES : WINDOW_SAMPLES]

    # A truth gap drops the *epochs* that touch it, not the sequence -- D-089's rule, applied to
    # training windows. Vw14a loses 4 boundaries of 313 and Vta4 one of 178; refusing the stem
    # over that would throw away 99% of a drive because the VBOX blinked. The offsets are
    # computed here rather than by calling `displacements_ned`, which raises by design because
    # its caller is the *grader*, where a silently-skipped epoch would be a missing measurement.
    nearest = np.searchsorted(truth.t_s, bounds).clip(1, truth.t_s.size - 1)
    offset = np.minimum(
        np.abs(bounds - truth.t_s[nearest - 1]), np.abs(bounds - truth.t_s[nearest])
    )
    covered = offset <= MAX_EPOCH_OFFSET_S
    if covered.sum() < 4:
        raise ValueError(f"{seq.name}: only {covered.sum()} of {n_epochs} boundaries carry truth")

    ned = np.full((n_epochs, 2), np.nan)
    ned[covered] = truth.ned_at(bounds[covered])

    disp = ned[1:] - ned[:-1]  # (n_epochs - 1, 2); nan wherever either boundary is missing
    distance = np.linalg.norm(disp, axis=1)
    heading = np.arctan2(disp[:, 1], disp[:, 0])
    d_heading = wrap_to_pi(heading[1:] - heading[:-1])  # (n_epochs - 2,), for epochs 1..n-2

    # Epoch k is usable when its own displacement and the one before it are both real: the target
    # is a *change* in heading, so it needs two consecutive covered epochs, not one.
    usable = np.isfinite(distance[1:]) & np.isfinite(d_heading)
    idx = np.flatnonzero(usable) + 1  # back to epoch numbering

    channels = np.concatenate([gyro, accel], axis=1)
    x = np.stack([channels[k * WINDOW_SAMPLES : (k + 1) * WINDOW_SAMPLES] for k in idx])
    # d_distance[k] = distance[k] - distance[k-1]: the change in a second's travel, which is
    # what an accelerometer integrates to. `idx` starts at 1, so `idx - 1` is always real.
    y = np.stack([distance[idx], d_heading[idx - 1], distance[idx] - distance[idx - 1]], axis=1)
    if x.shape[0] != y.shape[0]:
        raise AssertionError(f"{seq.name}: {x.shape[0]} windows against {y.shape[0]} targets")
    return StemWindows(seq.name, x.astype("float32"), y.astype("float32"))


def wrap_to_pi(a):
    """Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358."""
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi


@dataclass
class Scaler:
    """0-1 feature scaling, fitted on the training windows **only** (D-071).

    The published text says "features scaled 0-1" and does not say on what. Fitting on train+test
    leaks the held-out set's dynamic range into training while involving no disallowed column at
    all, so the allowlist and the CI leakage job both stay green through it. The fitted ranges are
    saved beside the weights so the choice is checkable after the fact rather than asserted.
    """

    lo: np.ndarray
    hi: np.ndarray

    @classmethod
    def fit(cls, x) -> Scaler:
        flat = x.reshape(-1, x.shape[-1])
        lo, hi = flat.min(axis=0), flat.max(axis=0)
        span = np.where(hi - lo > 0, hi - lo, 1.0)
        return cls(lo=lo, hi=lo + span)

    def apply(self, x):
        return ((x - self.lo) / (self.hi - self.lo)).astype("float32")


def load_windows(data_dir: str, stems: tuple[str, ...]) -> tuple[list, list[tuple[str, str]]]:
    """Windows for every stem that can supply them, and the reason each of the others could not.

    Skipping is reported, never silent: three TRAIN stems (`M`, `S2`, `S4`) restart their clock
    mid-recording (D-013) and `assert_uniform_grid` refuses them, which is correct and which also
    removes real training data. A reproduction that quietly trained on 16 of 19 sequences and
    reported the gap as method difference would be wrong in a way nobody could see.
    """
    from eval.loaders.io_vnbd import load_sequence
    from eval.loaders.truth import load_truth, manifest_path_for, paired_truth_path

    kept, skipped = [], []
    for stem in stems:
        try:
            seq = load_sequence(
                manifest_path_for(stem, "S-", data_dir, strict_checksum=False), stem
            )
            truth = load_truth(paired_truth_path(stem, data_dir), stem)
            kept.append(epoch_windows(seq, truth))
        except Exception as exc:  # noqa: BLE001 - the reason is the deliverable here
            skipped.append((stem, f"{type(exc).__name__}: {exc}"))
    return kept, skipped


# --------------------------------------------------------------------------------------------
# Training
# --------------------------------------------------------------------------------------------


def train(
    kept, *, seed: int, target: str = DEFAULT_TARGET, max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
):
    """Fit the baseline. Returns `(model, scaler, history, split_sizes)`.

    Published settings are taken from `models.baseline_rnn` -- Adamax at 7e-4, MAE, batch 128,
    dropout 0.05, 72 hidden units -- so that changing one changes it in the architecture module
    and not in two places that can drift apart.
    """
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    from eval.splits import stem_family
    from models.baseline_rnn import BATCH_SIZE, OnyekpeBaseline, loss_fn, make_optimizer
    from models.baseline_rnn import WINDOW_SAMPLES as ARCH_WINDOW

    if ARCH_WINDOW != WINDOW_SAMPLES:
        raise AssertionError(
            f"window mismatch: architecture {ARCH_WINDOW}, trainer {WINDOW_SAMPLES}"
        )

    torch.manual_seed(seed)  # D-098: PyTorch's default init, seeded so the run is reproducible
    val_fams = validation_families(kept)
    tr = [w for w in kept if stem_family(w.name) not in val_fams]
    va = [w for w in kept if stem_family(w.name) in val_fams]
    if not tr or not va:
        raise ValueError(f"empty split: {len(tr)} train stems, {len(va)} validation stems")

    cols = list(TARGET_COLUMNS[target])
    x_tr = np.concatenate([w.x for w in tr])
    y_tr = np.concatenate([w.y for w in tr])[:, cols]
    scaler = Scaler.fit(x_tr)  # D-071: TRAIN only, never the validation or held-out windows
    x_va = np.concatenate([w.x for w in va])
    y_va = np.concatenate([w.y for w in va])[:, cols]

    loader = DataLoader(
        TensorDataset(torch.from_numpy(scaler.apply(x_tr)), torch.from_numpy(y_tr)),
        batch_size=BATCH_SIZE,
        shuffle=True,  # D-098
    )
    xv = torch.from_numpy(scaler.apply(x_va))
    yv = torch.from_numpy(y_va)

    model = OnyekpeBaseline()
    opt = make_optimizer(model)
    criterion = loss_fn()
    best, best_state, best_epoch, history = float("inf"), None, -1, []

    for epoch in range(max_epochs):
        model.train()
        for xb, yb in loader:
            opt.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            if GRAD_CLIP is not None:  # D-098: None. Present so the choice is visible, not absent.
                torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            opt.step()
        model.eval()
        with torch.no_grad():
            val = float(criterion(model(xv), yv))
        history.append(val)
        if val < best - 1e-9:
            best, best_epoch = val, epoch
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        elif epoch - best_epoch >= patience:  # D-098: stop, and restore the best weights
            break

    model.load_state_dict(best_state)
    model.eval()
    sizes = {
        "train_stems": [w.name for w in tr],
        "val_stems": [w.name for w in va],
        "train_windows": int(x_tr.shape[0]),
        "val_windows": int(x_va.shape[0]),
        "best_epoch": best_epoch,
        "epochs_run": len(history),
        "best_val_mae": best,
        "target": target,
    }
    return model, scaler, history, sizes


# --------------------------------------------------------------------------------------------
# Held-out evaluation, through the frozen metrics
# --------------------------------------------------------------------------------------------


def evaluate(
    model, scaler, data_dir: str, lengths: tuple[int, ...], *, target: str = DEFAULT_TARGET
) -> tuple[dict, list]:
    """Score the trained baseline over the frozen outage sweep. Returns `(by_length, dropped)`.

    Every number comes from `eval.baselines.score` -> `eval.metrics.core.evaluate_outage`: the
    same path the strapdown and GNSS-available baselines are scored through, which is what makes
    the three comparable at all.

    The heading seed is truth's course over ground in the second **before** the outage opens.
    That is the same concession `initial_state_from_truth` makes for the strapdown baseline
    (D-064): at outage entry GNSS is still available, so a real system has this heading. A network
    that predicts only *changes* in heading needs somewhere to start, and starting it at zero
    would measure the seed rather than the model.
    """
    import torch

    from eval.baselines import (
        BaselineTrajectory,
        course_over_ground,
        initial_state_from_truth,
        naive_strapdown,
        score,
    )
    from eval.loaders.io_vnbd import load_sequence
    from eval.loaders.truth import (
        align_to_sequence,
        load_truth,
        manifest_path_for,
        paired_truth_path,
    )
    from eval.outages.inject import generate_sweep
    from eval.run import assert_uniform_grid, imu_stream, truth_clock_offset_s
    from eval.splits import test_sequences

    by_length: dict[int, list] = {n: [] for n in lengths}
    strapdown: dict[int, list] = {n: [] for n in lengths}
    dropped: list[tuple[str, str]] = []

    for stem in test_sequences():
        try:
            seq = load_sequence(
                manifest_path_for(stem, "S-", data_dir, strict_checksum=False), stem
            )
            truth = load_truth(paired_truth_path(stem, data_dir), stem)
            report = align_to_sequence(seq, truth)
            if not report.is_usable:
                raise ValueError(f"truth pairing unusable: {report.residual_median_m:.1f} m median")
            gyro, accel, t_rel_s = imu_stream(seq)
            assert_uniform_grid(seq.name, t_rel_s)
            t_abs_s = t_rel_s + truth_clock_offset_s(seq)
        except Exception as exc:  # noqa: BLE001
            dropped.append((stem, f"sequence: {type(exc).__name__}: {exc}"))
            continue

        channels = np.concatenate([gyro, accel], axis=1)
        sweep = generate_sweep({stem: channels.shape[0]}, tuple(lengths))
        for length_s, windows in sweep.items():
            for outage in windows:
                n = outage.n_epochs
                start = outage.start_idx
                x = channels[start : start + n * WINDOW_SAMPLES]
                if x.shape[0] < n * WINDOW_SAMPLES:
                    dropped.append((stem, f"{length_s}s window {start}: stream ends mid-window"))
                    continue
                t0 = float(t_abs_s[start])
                try:
                    # The second before the outage: heading, and -- for `delta_speed` -- the entry
                    # speed the network integrates from. Both are what a real system holds at
                    # outage entry, where GNSS is still available (D-064).
                    seed = truth.displacements_ned(np.array([t0 - 1.0, t0]))
                    h0 = float(course_over_ground(seed)[-1])
                    v0 = float(np.linalg.norm(seed[-1]))
                except Exception as exc:  # noqa: BLE001
                    dropped.append((stem, f"{length_s}s window {start}: seed: {exc}"))
                    continue

                with torch.no_grad():
                    pred = model(
                        torch.from_numpy(
                            scaler.apply(x.reshape(n, WINDOW_SAMPLES, len(FEATURE_COLUMNS)))
                        )
                    ).numpy()
                if target == "delta_speed":
                    distance = v0 + np.cumsum(pred[:, 0])
                else:
                    distance = pred[:, 0]
                distance = np.clip(distance, 0.0, None)  # a second of travel is never negative
                heading = h0 + np.cumsum(pred[:, 1])
                disp = np.stack([distance * np.cos(heading), distance * np.sin(heading)], axis=1)
                traj = BaselineTrajectory(
                    displacements_ned=disp,
                    yaw_rad=course_over_ground(disp, initial_yaw_rad=h0),
                )
                try:
                    scored = score(traj, truth, outage, t0_s=t0)
                except Exception as exc:  # noqa: BLE001 - D-089: drop the window, not the stem
                    dropped.append((stem, f"{length_s}s window {start}: truth: {exc}"))
                    continue

                # The same window through the raw strapdown (P-05), because the INS paper reports
                # its result as an improvement *over raw INS* rather than as an absolute error.
                # Scored by the same `score`, from the same truth, over the same epochs.
                try:
                    r0, v0_ned = initial_state_from_truth(truth, t0)
                    sd_traj = naive_strapdown(
                        gyro[start : start + n * WINDOW_SAMPLES],
                        accel[start : start + n * WINDOW_SAMPLES],
                        1.0 / WINDOW_SAMPLES,
                        initial_rotation=r0,
                        initial_velocity_ned=v0_ned,
                        epoch_stride=WINDOW_SAMPLES,
                    )
                    sd_scored = score(sd_traj, truth, outage, t0_s=t0)
                except Exception as exc:  # noqa: BLE001
                    dropped.append((stem, f"{length_s}s window {start}: strapdown: {exc}"))
                    continue

                by_length[length_s].append(scored)
                strapdown[length_s].append(sd_scored)
    return {"model": by_length, "strapdown": strapdown}, dropped


def _median(rows: list, field: str) -> float:
    """Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md), and one
    window over a roundabout should not set the headline for a whole outage length."""
    return float(np.median([getattr(r, field) for r in rows]))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="train-baseline-rnn",
        description="Reproduce the Onyekpe INS baseline at its published hyperparameters",
    )
    # `data`, not `data/IO-VNBD`: the manifest's own paths open with `IO-VNBD/`, so that is
    # what `manifest_path_for` joins onto the root. (`eval/run.py` defaults to `data/IO-VNBD`
    # while calling `paired_truth_path(name, args.data)`, which cannot resolve -- flagged for
    # seat D in phases.md section 11 rather than changed here, since `eval/` is out of scope.)
    p.add_argument("--data", default="data")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epochs", type=int, default=MAX_EPOCHS, help="cap; early stopping decides")
    p.add_argument(
        "--target", choices=sorted(TARGET_COLUMNS), default=DEFAULT_TARGET,
        help="what the network regresses; see TARGET_COLUMNS and D-099",
    )
    p.add_argument(
        "--audit",
        action="store_true",
        help="print the stated-vs-omitted hyperparameter table and exit, training nothing",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(audit_table())
    if args.audit:
        return 0

    try:
        import torch  # noqa: F401
    except ImportError:
        print(
            '\ntorch is not installed. This baseline needs the `ml` extra: pip install -e ".[ml]"'
            "\nIt is deliberately absent from CI -- the harness is the critical path and must not "
            "block on a 2 GB download.",
            file=sys.stderr,
        )
        return 4

    from eval.splits import TRAIN

    print("\n" + assert_features_are_clean())

    print(f"\nloading TRAIN windows from {args.data} ...")
    kept, skipped = load_windows(args.data, TRAIN)
    n_win = sum(w.x.shape[0] for w in kept)
    print(f"  {len(kept)}/{len(TRAIN)} stems usable, {n_win} windows of 1 s")
    for stem, why in skipped:
        print(f"  EXCLUDED {stem}: {why.splitlines()[0][:96]}")
    if not kept:
        print("no training data", file=sys.stderr)
        return 5

    model, scaler, history, sizes = train(
        kept, seed=args.seed, target=args.target, max_epochs=args.epochs
    )
    print(
        f"\ntrained on `{sizes['target']}`: {sizes['epochs_run']} epochs run, "
        f"best at {sizes['best_epoch']} "
        f"(val MAE {sizes['best_val_mae']:.4f}), {model.n_parameters()} parameters"
    )
    print(f"  train {sizes['train_windows']} windows over {len(sizes['train_stems'])} stems")
    print(f"  val   {sizes['val_windows']} windows over {sizes['val_stems']}")

    print("\nscoring the frozen outage sweep on held-out sequences ...")
    scored, dropped = evaluate(model, scaler, args.data, OUTAGE_LENGTHS_S, target=args.target)
    print(
        f"\n{'outage':>7}  {'n':>5}  {'CRSE m':>10}  {'raw INS':>10}  {'improve':>8}  "
        f"{'CTE m':>10}  {'drift %':>8}  {'yaw deg':>8}"
    )
    for length_s in OUTAGE_LENGTHS_S:
        rows, sd = scored["model"][length_s], scored["strapdown"][length_s]
        if not rows:
            print(f"{length_s:>6}s  {0:>5}      (no window survived truth coverage)")
            continue
        crse, crse_sd = _median(rows, "crse_m"), _median(sd, "crse_m")
        gain = 100.0 * (1.0 - crse / crse_sd) if crse_sd > 0 else float("nan")
        print(
            f"{length_s:>6}s  {len(rows):>5}  {crse:>10.2f}  {crse_sd:>10.2f}  {gain:>7.1f}%  "
            f"{_median(rows, 'cte_m'):>10.2f}  {_median(rows, 'drift_pct'):>8.2f}  "
            f"{np.degrees(_median(rows, 'yaw_rmse_rad')):>8.2f}"
        )
    print(f"\n{len(dropped)} window(s)/stem(s) dropped:")
    for name, why in dropped[:12]:
        print(f"  {name}: {why[:96]}")
    if len(dropped) > 12:
        print(f"  ... and {len(dropped) - 12} more")

    print(PUBLISHED_COMPARISON)
    return 0


#: Medians against the published table. Ours are `S-` phone IMU on our own frozen split; theirs
#: are the IO-VNBD paper's, on wheel odometry for WhONet and on their own physics model. The
#: comparison is between different sensors on different splits and is reported as such.
PUBLISHED_COMPARISON = """
Published, for context (docs/DATASETS.md section 3 -- NOT our sensor, NOT our split):

     outage   physics CTE/CRSE   WhONet CTE/CRSE
        30 s   0.84 / 2.31 m      0.23 / 0.67 m
        60 s   1.02 / 4.56 m      0.30 / 1.31 m
       120 s   1.78 / 9.11 m      1.78 / 2.62 m
       180 s   2.90 / 13.67 m     0.49 / 3.93 m

WhONet's input is wheel speed, which PS 26168 disallows, and both columns come from the paper's
own split rather than ours. Neither is a phone-only number and neither may be quoted as ours
(H-7). The gap this reproduction reports is against the *physics* column, and the reasons it is
not a like-for-like comparison are in the run above: a different split, three TRAIN stems dropped
for clock restarts, and ten hyperparameters the papers do not state (`--audit`).
"""

if __name__ == "__main__":
    raise SystemExit(main())
