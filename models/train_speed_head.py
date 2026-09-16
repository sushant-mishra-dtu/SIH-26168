"""Train and evaluate the standalone P-08 speed + variance head.

The head sees only the nine S- inertial channels in :data:`FEATURE_COLUMNS`.  Its labels are
derived from the paired V- track's latitude/longitude positions through ``TruthTrack``; no V-
velocity, wheel-speed, or heading channel has a path into the feature tensor.

P-08 deliberately stops at a calibrated model.  It does not call ``InEKF.update_speed`` or
otherwise add a learned measurement to the filter while Gate 1 remains unsigned.  That is P-09.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


# Every number below which is not already part of ``models.speed_head`` is reported as a P-08
# decision in D-132.  Keeping this audit next to the trainer prevents an unrecorded constant from
# becoming a quiet hyperparameter search.
@dataclass(frozen=True)
class Hyperparameter:
    """One training setting and whether it was stated or chosen for P-08."""

    name: str
    value: str
    source: str
    decision: str = ""

    @property
    def is_our_choice(self) -> bool:
        return bool(self.decision)


HYPERPARAMETERS: tuple[Hyperparameter, ...] = (
    Hyperparameter(
        "input channels",
        "accel xyz, gravity xyz, gyro xyz (body frame)",
        "models.speed_head.N_INPUT_CHANNELS",
    ),
    Hyperparameter(
        "window", "20 samples / about 2 s at 10 Hz", "models.speed_head.WINDOW_SAMPLES"
    ),
    Hyperparameter(
        "architecture", "causal TCN (32, 64, 64), dropout 0.1", "models.speed_head"
    ),
    Hyperparameter(
        "variance parameterisation", "exp(log variance), floor 1e-4", "models.speed_head"
    ),
    Hyperparameter("loss", "heteroscedastic Gaussian NLL", "models.speed_head.gaussian_nll"),
    Hyperparameter(
        "calibration criterion", ">=95% within +/-2 sigma", "phases.md P-08 / Gate 2"
    ),
    Hyperparameter(
        "window stride", "10 samples / 1 s", "OMITTED -- matches P-06 cadence", decision="D-132"
    ),
    Hyperparameter(
        "optimizer", "Adamax", "OMITTED -- P-06's stated car-IMU optimizer", decision="D-132"
    ),
    Hyperparameter(
        "learning rate", "7e-4", "OMITTED -- P-06's stated car-IMU rate", decision="D-132"
    ),
    Hyperparameter(
        "batch size", "128", "OMITTED -- P-06's stated car-IMU batch", decision="D-132"
    ),
    Hyperparameter(
        "epoch cap / patience", "200 / 20, restore best validation NLL", "OMITTED", decision="D-132"
    ),
    Hyperparameter(
        "validation split", "whole TRAIN families, smallest first to 15%", "D-098", decision="D-098"
    ),
    Hyperparameter(
        "scaler fitting set", "training windows only", "D-071", decision="D-071"
    ),
    Hyperparameter(
        "reliability bins", "10 equal-count bins", "OMITTED", decision="D-132"
    ),
)


# The exact order fed to the tensor.  It is both an input contract and the list passed to the
# repo-wide feature guard before a run starts.
FEATURE_COLUMNS = (
    "accel_x",
    "accel_y",
    "accel_z",
    "gravity_x",
    "gravity_y",
    "gravity_z",
    "gyro_yaw",
    "gyro_pitch",
    "gyro_roll",
)
ACCEL_COLUMNS = FEATURE_COLUMNS[:3]
GRAVITY_COLUMNS = FEATURE_COLUMNS[3:6]

WINDOW_SAMPLES = 20
WINDOW_STRIDE_SAMPLES = 10
BATCH_SIZE = 128
LEARNING_RATE = 7e-4
MAX_EPOCHS = 200
PATIENCE = 20
VALIDATION_FRACTION = 0.15
RELIABILITY_BINS = 10
TARGETS = ("absolute_speed", "delta_speed")


def audit_table() -> str:
    """Return the stated-versus-chosen P-08 training settings."""
    width = max(len(h.name) for h in HYPERPARAMETERS)
    lines = [
        "P-08 speed + variance head -- stated inputs and explicit choices",
        "",
        f"{'setting'.ljust(width)}  {'value'.ljust(48)}  source",
        f"{'-' * width}  {'-' * 48}  {'-' * 46}",
    ]
    for h in HYPERPARAMETERS:
        marker = f"  [{h.decision}]" if h.is_our_choice else ""
        lines.append(f"{h.name.ljust(width)}  {h.value.ljust(48)}  {h.source}{marker}")
    stated = sum(not h.is_our_choice for h in HYPERPARAMETERS)
    ours = sum(h.is_our_choice for h in HYPERPARAMETERS)
    lines.extend(
        [
            "",
            f"{stated} stated, {ours} ours. Each chosen setting is named in D-132 before any ",
            "calibration result is quoted.",
        ]
    )
    return "\n".join(lines)


def assert_features_are_clean() -> str:
    """Run the guard over exactly the columns about to enter the model tensor."""
    from eval.loaders.columns import DENY_PATTERN, assert_feature_safe

    assert_feature_safe(FEATURE_COLUMNS)
    checked = "\n".join(
        f"    {column:<14} allowed, no denylist match" for column in FEATURE_COLUMNS
    )
    return (
        f"leakage guard over the {len(FEATURE_COLUMNS)} columns actually fed to the model:\n"
        f"{checked}\n"
        f"    denylist = {DENY_PATTERN.pattern}\n"
        "    assert_feature_safe() returned without raising -- no `V-` column reaches the input."
    )


@dataclass(frozen=True)
class SpeedWindows:
    """One stem's feature windows and truth-derived targets.

    ``absolute_speed_mps`` is each 20-sample window's path speed.  ``delta_speed_mps`` is the
    difference between the latter and former one-second halves of that same window.  It is an
    increment over the model's own causal context, so it never crosses a truth gap or reaches into
    a preceding window.
    """

    name: str
    x: np.ndarray  # (n, WINDOW_SAMPLES, 9)
    absolute_speed_mps: np.ndarray  # (n,)
    delta_speed_mps: np.ndarray  # (n,); nan where there is no adjacent predecessor

    def for_target(self, target: str) -> tuple[np.ndarray, np.ndarray]:
        if target == "absolute_speed":
            y = self.absolute_speed_mps
        elif target == "delta_speed":
            y = self.delta_speed_mps
        else:
            raise ValueError(f"unknown target {target!r}; expected one of {TARGETS}")
        keep = np.isfinite(y)
        return self.x[keep], y[keep].astype("float32")


@dataclass(frozen=True)
class Scaler:
    """Per-channel 0--1 scaler fitted only from the training windows (D-071)."""

    lo: np.ndarray
    hi: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> Scaler:
        flat = np.asarray(x, dtype=float).reshape(-1, x.shape[-1])
        lo, hi = flat.min(axis=0), flat.max(axis=0)
        span = np.where(hi - lo > 0.0, hi - lo, 1.0)
        return cls(lo=lo.astype("float32"), hi=(lo + span).astype("float32"))

    def apply(self, x: np.ndarray) -> np.ndarray:
        return ((x - self.lo) / (self.hi - self.lo)).astype("float32")


def monotonic_prefix_length(t_rel_s: np.ndarray) -> int:
    """Length through the first 10 Hz monotonic prefix of a sequence.

    ``M``, ``S2`` and ``S4`` restart their logger clock.  The usable recording is the prefix
    before that restart, not the whole stem discarded by ``assert_uniform_grid``.  Non-10 Hz
    samples are still rejected by that assertion after this prefix is selected.
    """
    t = np.asarray(t_rel_s, dtype=float)
    reset = np.flatnonzero(np.diff(t) <= 0.0)
    return int(reset[0] + 1) if reset.size else int(t.size)


def _truth_clock_offset_for_prefix(seq, prefix_samples: int) -> float:
    """Place a reset-clock prefix on the truth clock using only its own fixes."""
    from eval.loaders.truth import seconds_of_day_utc

    gnss = seq.gnss
    needed = {"date", "time_since_start_ms", "sample_idx"}
    missing = needed - set(gnss.columns)
    if missing:
        raise ValueError(
            f"{seq.name}: GNSS fixes lack {sorted(missing)} needed for truth alignment"
        )
    tod = seconds_of_day_utc(gnss["date"].tolist())
    rel = gnss["time_since_start_ms"].to_numpy(dtype=float) / 1000.0
    in_prefix = gnss["sample_idx"].to_numpy(dtype=int) < prefix_samples
    usable = in_prefix & np.isfinite(tod) & np.isfinite(rel)
    if not usable.any():
        raise ValueError(f"{seq.name}: no dated GNSS fix in the monotonic prefix")
    return float(np.median(tod[usable] - rel[usable]))


def _window_speed_mps(ned: np.ndarray, times_s: np.ndarray) -> float:
    """Path speed from truth positions at the actual samples in one input window."""
    pos = np.asarray(ned, dtype=float)
    times = np.asarray(times_s, dtype=float)
    if pos.ndim != 2 or pos.shape[1] != 2 or pos.shape[0] != times.size:
        raise ValueError(f"positions {pos.shape} do not match {times.shape} timestamps")
    duration = float(times[-1] - times[0])
    if not duration > 0.0:
        raise ValueError(f"non-positive truth window duration {duration}")
    path_m = float(np.linalg.norm(np.diff(pos, axis=0), axis=1).sum())
    return path_m / duration


def build_windows(seq, truth) -> SpeedWindows:
    """Build causal two-second S- windows and their position-differenced speed labels.

    A truth gap drops only the affected window (D-089).  No acceleration is integrated: it is an
    input feature only, while every target comes from ``TruthTrack.ned_at``.
    """
    from eval.run import assert_uniform_grid, imu_stream

    gyro, accel, t_rel_s = imu_stream(seq)
    prefix = monotonic_prefix_length(t_rel_s)
    gyro, accel, t_rel_s = gyro[:prefix], accel[:prefix], t_rel_s[:prefix]
    assert_uniform_grid(seq.name, t_rel_s)

    gravity = seq.imu.loc[: prefix - 1, list(GRAVITY_COLUMNS)].to_numpy(dtype=float)
    if gravity.shape != accel.shape:
        raise ValueError(
            f"{seq.name}: gravity shape {gravity.shape} differs from accel {accel.shape}"
        )
    if not np.isfinite(gravity).all():
        raise ValueError(f"{seq.name}: non-finite gravity samples in model feature tensor")

    # ``imu_stream`` supplies the D-101 gyro triad.  Acceleration and gravity stay in their raw
    # device axes, which are the body-frame axes of their own Android sensor vectors.
    channels = np.concatenate([accel, gravity, gyro], axis=1).astype("float32")
    if channels.shape[1] != len(FEATURE_COLUMNS):
        raise AssertionError(f"expected {len(FEATURE_COLUMNS)} channels, got {channels.shape[1]}")
    t_abs_s = t_rel_s + _truth_clock_offset_for_prefix(seq, prefix)

    starts = range(0, channels.shape[0] - WINDOW_SAMPLES + 1, WINDOW_STRIDE_SAMPLES)
    kept_x: list[np.ndarray] = []
    speeds: list[float] = []
    deltas: list[float] = []
    for start in starts:
        stop = start + WINDOW_SAMPLES
        times = t_abs_s[start:stop]
        try:
            ned = truth.ned_at(times)
            speed = _window_speed_mps(ned, times)
            split = WINDOW_SAMPLES // 2
            delta = _window_speed_mps(ned[split:], times[split:]) - _window_speed_mps(
                ned[:split], times[:split]
            )
        except Exception:  # D-089: truth coverage excludes a window, never a whole stem
            continue
        kept_x.append(channels[start:stop])
        speeds.append(speed)
        deltas.append(delta)

    if len(kept_x) < 2:
        raise ValueError(f"{seq.name}: fewer than two windows survive truth coverage")
    x = np.stack(kept_x).astype("float32")
    absolute = np.asarray(speeds, dtype="float32")

    delta = np.asarray(deltas, dtype="float32")
    return SpeedWindows(seq.name, x, absolute, delta)


def validation_families(windows: list[SpeedWindows]) -> tuple[str, ...]:
    """Hold back complete TRAIN families using P-06's deterministic D-098 rule."""
    from eval.splits import stem_family

    per_family: dict[str, int] = {}
    for window in windows:
        family = stem_family(window.name)
        per_family[family] = per_family.get(family, 0) + window.x.shape[0]
    target_count = VALIDATION_FRACTION * sum(per_family.values())
    held, chosen = 0, []
    for family in sorted(per_family, key=lambda name: (per_family[name], name)):
        if held >= target_count:
            break
        chosen.append(family)
        held += per_family[family]
    if len(chosen) < 3 or held == sum(per_family.values()):
        raise ValueError(f"degenerate validation split: {chosen} holding {held} windows")
    return tuple(sorted(chosen))


def load_windows(
    data_dir: str | Path, stems: tuple[str, ...]
) -> tuple[list[SpeedWindows], list[tuple[str, str]]]:
    """Load the named stems, recording exclusions rather than silently changing the split."""
    from eval.loaders.io_vnbd import load_sequence
    from eval.loaders.truth import (
        align_to_sequence,
        load_truth,
        manifest_path_for,
        paired_truth_path,
    )

    kept: list[SpeedWindows] = []
    skipped: list[tuple[str, str]] = []
    for stem in stems:
        try:
            source = manifest_path_for(stem, "S-", data_dir, strict_checksum=False)
            seq = load_sequence(source, stem)
            truth = load_truth(paired_truth_path(stem, data_dir), stem)
            alignment = align_to_sequence(seq, truth)
            if not alignment.is_usable:
                raise ValueError(
                    f"truth pairing unusable: {alignment.residual_median_m:.1f} m median"
                )
            kept.append(build_windows(seq, truth))
        except Exception as exc:  # noqa: BLE001 - the named omission is a deliverable
            skipped.append((stem, f"{type(exc).__name__}: {exc}"))
    return kept, skipped


def _stack(windows: list[SpeedWindows], target: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Concatenate a group of stems after selecting its target and valid delta labels."""
    groups = [(window.name, *window.for_target(target)) for window in windows]
    if not groups or not any(x.shape[0] for _, x, _ in groups):
        raise ValueError(f"no {target} windows")
    x = np.concatenate([item[1] for item in groups])
    y = np.concatenate([item[2] for item in groups])
    names = [name for name, features, _ in groups for _ in range(features.shape[0])]
    return x, y, names


def calibration_summary(
    pred: np.ndarray, variance: np.ndarray, target: np.ndarray
) -> dict[str, float | int]:
    """Coverage-first calibration and sharpness statistics, independent of torch."""
    p, var, y = (np.asarray(values, dtype=float).reshape(-1) for values in (pred, variance, target))
    if not (p.shape == var.shape == y.shape) or p.size == 0:
        raise ValueError(f"prediction {p.shape}, variance {var.shape}, target {y.shape}")
    if not np.isfinite(p).all() or not np.isfinite(var).all() or not np.isfinite(y).all():
        raise ValueError("calibration inputs must be finite")
    if np.any(var <= 0.0):
        raise ValueError("predicted variance must be positive")
    error = p - y
    sigma = np.sqrt(var)
    return {
        "n": int(p.size),
        "coverage_1sigma": float(np.mean(np.abs(error) <= sigma)),
        "coverage_2sigma": float(np.mean(np.abs(error) <= 2.0 * sigma)),
        "coverage_3sigma": float(np.mean(np.abs(error) <= 3.0 * sigma)),
        "rmse_mps": float(np.sqrt(np.mean(error**2))),
        "mae_mps": float(np.mean(np.abs(error))),
        "mean_sigma_mps": float(np.mean(sigma)),
    }


def per_stem_summary(
    pred: np.ndarray, variance: np.ndarray, target: np.ndarray, names: list[str]
) -> dict[str, dict[str, float | int]]:
    """Apply :func:`calibration_summary` per held-out stem."""
    if len(names) != np.asarray(pred).size:
        raise ValueError(f"{len(names)} names for {np.asarray(pred).size} predictions")
    result: dict[str, dict[str, float | int]] = {}
    for name in sorted(set(names)):
        mask = np.asarray([item == name for item in names])
        result[name] = calibration_summary(
            np.asarray(pred)[mask], np.asarray(variance)[mask], np.asarray(target)[mask]
        )
    return result


def _evaluate_arrays(model, x: np.ndarray, *, device: str) -> tuple[np.ndarray, np.ndarray]:
    """Run a fitted torch model and bring its two outputs back to NumPy."""
    import torch

    model.eval()
    with torch.no_grad():
        pred, variance = model(torch.from_numpy(x.transpose(0, 2, 1)).to(device))
    return pred.detach().cpu().numpy(), variance.detach().cpu().numpy()


def train(
    windows: list[SpeedWindows],
    *,
    seed: int,
    target: str,
    max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
) -> tuple[object, Scaler, dict[str, object]]:
    """Fit a target-specific head and retain the weights with the lowest validation NLL."""
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    from eval.splits import stem_family
    from models.speed_head import N_INPUT_CHANNELS, SpeedHead, gaussian_nll
    from models.speed_head import WINDOW_SAMPLES as ARCH_WINDOW

    if ARCH_WINDOW != WINDOW_SAMPLES or N_INPUT_CHANNELS != len(FEATURE_COLUMNS):
        raise AssertionError(
            f"head contract ({N_INPUT_CHANNELS}, {ARCH_WINDOW}) differs from trainer "
            f"({len(FEATURE_COLUMNS)}, {WINDOW_SAMPLES})"
        )
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}")
    torch.manual_seed(seed)
    val_families = validation_families(windows)
    train_windows = [item for item in windows if stem_family(item.name) not in val_families]
    val_windows = [item for item in windows if stem_family(item.name) in val_families]
    x_train, y_train, _ = _stack(train_windows, target)
    x_val, y_val, _ = _stack(val_windows, target)
    scaler = Scaler.fit(x_train)
    x_train, x_val = scaler.apply(x_train), scaler.apply(x_val)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SpeedHead().to(device)
    optimizer = torch.optim.Adamax(model.parameters(), lr=LEARNING_RATE)
    loader = DataLoader(
        TensorDataset(
            torch.from_numpy(x_train.transpose(0, 2, 1)), torch.from_numpy(y_train)
        ),
        batch_size=BATCH_SIZE,
        shuffle=True,
    )
    x_val_t = torch.from_numpy(x_val.transpose(0, 2, 1)).to(device)
    y_val_t = torch.from_numpy(y_val).to(device)
    best_nll, best_epoch, best_state, history = float("inf"), -1, None, []
    for epoch in range(max_epochs):
        model.train()
        for x_batch, y_batch in loader:
            optimizer.zero_grad()
            pred, variance = model(x_batch.to(device))
            loss = gaussian_nll(pred, variance, y_batch.to(device))
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            pred, variance = model(x_val_t)
            val_nll = float(gaussian_nll(pred, variance, y_val_t))
        history.append(val_nll)
        if val_nll < best_nll - 1e-9:
            best_nll, best_epoch = val_nll, epoch
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
        elif epoch - best_epoch >= patience:
            break
    if best_state is None:
        raise AssertionError("training produced no model state")
    model.load_state_dict(best_state)
    val_pred, val_variance = _evaluate_arrays(model, x_val, device=device)
    constant = float(np.mean(y_train))
    details: dict[str, object] = {
        "target": target,
        "device": device,
        "validation_families": list(val_families),
        "train_stems": [item.name for item in train_windows],
        "validation_stems": [item.name for item in val_windows],
        "train_windows": int(x_train.shape[0]),
        "validation_windows": int(x_val.shape[0]),
        "best_epoch": best_epoch,
        "epochs_run": len(history),
        "best_validation_nll": best_nll,
        "validation": calibration_summary(val_pred, val_variance, y_val),
        "validation_constant_mean_rmse_mps": float(np.sqrt(np.mean((y_val - constant) ** 2))),
    }
    return model, scaler, details


def _choose_target(windows: list[SpeedWindows], *, seed: int, max_epochs: int, patience: int):
    """Train absolute speed first; use its held-back comparison to decide P-08's target."""
    model, scaler, details = train(
        windows, seed=seed, target="absolute_speed", max_epochs=max_epochs, patience=patience
    )
    head_rmse = float(details["validation"]["rmse_mps"])
    mean_rmse = float(details["validation_constant_mean_rmse_mps"])
    decision = {
        "absolute_speed_validation_rmse_mps": head_rmse,
        "absolute_speed_constant_mean_rmse_mps": mean_rmse,
    }
    if head_rmse < mean_rmse:
        decision["selected_target"] = "absolute_speed"
        return model, scaler, details, decision
    model, scaler, details = train(
        windows, seed=seed, target="delta_speed", max_epochs=max_epochs, patience=patience
    )
    decision["selected_target"] = "delta_speed"
    return model, scaler, details, decision


def plot_calibration(
    pred: np.ndarray,
    variance: np.ndarray,
    target: np.ndarray,
    *,
    stamp,
    path: str | Path,
) -> None:
    """Write the stamped sharpness/reliability figure required by P-08."""
    import matplotlib.pyplot as plt

    sigma = np.sqrt(np.asarray(variance, dtype=float))
    abs_error = np.abs(np.asarray(pred, dtype=float) - np.asarray(target, dtype=float))
    order = np.argsort(sigma)
    chunks = [
        chunk for chunk in np.array_split(order, min(RELIABILITY_BINS, order.size)) if chunk.size
    ]
    predicted = [float(np.mean(sigma[chunk])) for chunk in chunks]
    realised = [float(np.sqrt(np.mean(abs_error[chunk] ** 2))) for chunk in chunks]
    extent = max(predicted + realised + [1e-6])

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), constrained_layout=True)
    axes[0].scatter(sigma, abs_error, s=12, alpha=0.55, edgecolors="none")
    axes[0].plot([0.0, extent], [0.0, extent], "k--", linewidth=1, label="ideal RMSE = sigma")
    axes[0].set(xlabel="predicted sigma (m/s)", ylabel="realised absolute error (m/s)")
    axes[0].legend(loc="upper left")
    axes[1].plot(predicted, realised, "o-", label="equal-count sigma bins")
    axes[1].plot([0.0, extent], [0.0, extent], "k--", linewidth=1, label="ideal")
    axes[1].set(xlabel="mean predicted sigma (m/s)", ylabel="bin RMSE (m/s)")
    axes[1].legend(loc="upper left")
    fig.suptitle("P-08 speed-head calibration on held-out sequences")
    from idr.stamp import stamp_figure

    stamp_figure(fig, stamp)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _export_fp16(model, scaler: Scaler, *, target: str, path: str | Path) -> str:
    """Save FP16 weights plus the train-only scaler.  INT8 and filter fusion are out of scope."""
    import torch

    state = {
        key: value.detach().cpu().half() if value.is_floating_point() else value.detach().cpu()
        for key, value in model.state_dict().items()
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "format": "speed_head_fp16_state_dict",
            "target": target,
            "feature_columns": list(FEATURE_COLUMNS),
            "window_samples": WINDOW_SAMPLES,
            "scaler": {"lo": scaler.lo, "hi": scaler.hi},
            "state_dict": state,
        },
        output,
    )
    return str(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="train-speed-head", description="Train and calibrate P-08's standalone speed head"
    )
    parser.add_argument("--data", default="data")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--epochs", type=int, default=MAX_EPOCHS, help="cap; early stopping decides"
    )
    parser.add_argument("--target", choices=(*TARGETS, "auto"), default="auto")
    parser.add_argument(
        "--audit", action="store_true", help="print settings and exit without reading data"
    )
    parser.add_argument("--output-dir", default="eval/figures")
    parser.add_argument("--checkpoint", default="checkpoints/speed_head_fp16.pt")
    parser.add_argument(
        "--overwrite", action="store_true", help="replace existing P-08 figure/summary artefacts"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(audit_table())
    if args.audit:
        return 0
    try:
        import torch  # noqa: F401
    except ImportError:
        print(
            "\ntorch is not installed. P-08 needs the `ml` extra in its GPU interpreter.\n"
            "It remains deliberately absent from the CI environment.",
            file=sys.stderr,
        )
        return 4

    from eval.splits import TRAIN, test_sequences
    from idr.stamp import seed_everything

    stamp = seed_everything(args.seed)
    if not stamp.is_reproducible():
        print(
            f"refusing to create a quoted P-08 artefact from {stamp.commit}; "
            "commit or clean the tree first",
            file=sys.stderr,
        )
        return 6
    print("\n" + assert_features_are_clean())
    print(f"\nloading {len(TRAIN)} TRAIN stems from {args.data} ...")
    train_windows, train_skipped = load_windows(args.data, TRAIN)
    if not train_windows:
        print("no TRAIN stem produced speed windows", file=sys.stderr)
        return 5
    print(f"  {len(train_windows)}/{len(TRAIN)} stems usable")
    for stem, reason in train_skipped:
        print(f"  EXCLUDED {stem}: {reason.splitlines()[0][:96]}")

    if args.target == "auto":
        model, scaler, training, selection = _choose_target(
            train_windows, seed=args.seed, max_epochs=args.epochs, patience=PATIENCE
        )
    else:
        model, scaler, training = train(
            train_windows,
            seed=args.seed,
            target=args.target,
            max_epochs=args.epochs,
            patience=PATIENCE,
        )
        selection = {"selected_target": args.target}
    target = str(selection["selected_target"])
    print(
        f"\ntrained `{target}` on {training['device']}: {training['epochs_run']} epochs, "
        f"best validation NLL {training['best_validation_nll']:.5f}"
    )
    print(f"  target decision: {json.dumps(selection, sort_keys=True)}")

    held_out = test_sequences()
    print(f"\nloading {len(held_out)} held-out stems ...")
    test_windows, test_skipped = load_windows(args.data, held_out)
    x_test, y_test, names = _stack(test_windows, target)
    pred, variance = _evaluate_arrays(
        model, scaler.apply(x_test), device=str(training["device"])
    )
    summary = calibration_summary(pred, variance, y_test)
    by_stem = per_stem_summary(pred, variance, y_test, names)
    print(
        f"  coverage: {summary['coverage_2sigma']:.3%} within +/-2 sigma; "
        f"RMSE: {summary['rmse_mps']:.3f} m/s; mean sigma: {summary['mean_sigma_mps']:.3f} m/s"
    )

    output_dir = Path(args.output_dir)
    figure_path = output_dir / "speed_head_calibration.png"
    summary_path = output_dir / "speed_head_summary.json"
    existing = [path for path in (figure_path, summary_path) if path.exists()]
    if existing and not args.overwrite:
        print(
            f"refusing to overwrite existing artefact(s): {existing}; pass --overwrite",
            file=sys.stderr,
        )
        return 7
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_calibration(pred, variance, y_test, stamp=stamp, path=figure_path)
    checkpoint = _export_fp16(model, scaler, target=target, path=args.checkpoint)
    report = {
        "stamp": asdict(stamp),
        "scope": (
            "P-08 standalone training/calibration only; not fused into InEKF while Gate 1 is "
            "unsigned."
        ),
        "target_selection": selection,
        "target": target,
        "feature_columns": list(FEATURE_COLUMNS),
        "leakage_guard": assert_features_are_clean(),
        "hyperparameters": [asdict(item) for item in HYPERPARAMETERS],
        "training": training,
        "held_out": summary,
        "per_stem": by_stem,
        "train_excluded": train_skipped,
        "held_out_excluded": test_skipped,
        "checkpoint": checkpoint,
        "figure": str(figure_path),
    }
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"  wrote {figure_path}, {summary_path}, and FP16 checkpoint {checkpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
