"""P-06: the Onyekpe reproduction's data path, split rule and leakage guard.

Deliberately importable without the `ml` extra. `models.train_baseline_rnn` keeps torch inside
the functions that need it (D-072), so everything except the fitting test below runs in the CI
job that has no torch -- which is the job that matters, because the guard these tests are mostly
about is the one standing between a reproduction and a `V-` wheel-speed column.
"""

from __future__ import annotations

import numpy as np
import pytest

from eval.loaders.columns import LeakageError
from models.train_baseline_rnn import (
    DEFAULT_TARGET,
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    VALIDATION_FRACTION,
    Scaler,
    StemWindows,
    assert_features_are_clean,
    epoch_windows,
    validation_families,
    wrap_to_pi,
)
from tests.test_harness_wiring import synthetic_drive

# ------------------------------------------------------------------------------------------
# Targets, against a drive whose answer is known by construction
# ------------------------------------------------------------------------------------------


def test_epoch_windows_recovers_the_drive_it_was_given():
    """15 m/s due north for 300 s: every 1 s epoch is 15 m of travel and no change of heading.

    Hand-computed rather than asserted against the function's own output -- the target definition
    (D-099) is the one thing in this reproduction that neither paper states, so if it is wrong the
    model learns something coherent and wrong and every downstream number is quietly meaningless.
    """
    seq, truth = synthetic_drive(seconds=300.0, mps=15.0)
    w = epoch_windows(seq, truth)

    assert w.x.shape[1:] == (10, len(FEATURE_COLUMNS))
    assert w.x.shape[0] == w.y.shape[0]
    assert w.y[:, 0] == pytest.approx(15.0, abs=0.05), "distance per second is the speed"
    assert w.y[:, 1] == pytest.approx(0.0, abs=1e-6), "a straight line does not change heading"


def test_a_truth_gap_drops_epochs_rather_than_the_sequence():
    """D-089's rule, one level down. A VBOX blink must not cost a whole drive.

    Four TRAIN stems carry gaps: `Vw14a` loses 4 boundaries of 313, `Vta4` one of 178. Refusing
    the stem -- which is what `displacements_ned` does on its own, correctly, because its caller
    is the grader -- would have thrown away 99% of each of those drives.
    """
    seq, truth = synthetic_drive(seconds=300.0, mps=15.0)
    full = epoch_windows(seq, truth).x.shape[0]

    keep = np.ones(truth.t_s.size, dtype=bool)
    keep[1000:1010] = False  # a one-second hole, 100 s in
    holed = type(truth)(
        name=truth.name, t_s=truth.t_s[keep], lat=truth.lat[keep], lon=truth.lon[keep],
        source="synthetic, with a hole",
    )
    after = epoch_windows(seq, holed)

    assert after.x.shape[0] < full, "the epochs touching the hole must be dropped"
    assert after.x.shape[0] > full - 10, f"only the touching epochs: {full} -> {after.x.shape[0]}"
    assert np.isfinite(after.y).all()


# ------------------------------------------------------------------------------------------
# The scaler, and the leak it can cause without touching a disallowed column
# ------------------------------------------------------------------------------------------


def test_the_scaler_is_fitted_on_what_it_was_given_and_nothing_else():
    """D-071. Fitting on train+test leaks the held-out range into training and **no denylisted
    column is involved**, so the allowlist and the CI leakage job both stay green through it.
    The check is that unseen data is free to land outside 0-1, because that is the visible
    consequence of having fitted on the training windows alone."""
    train = np.zeros((4, 10, len(FEATURE_COLUMNS)), dtype="float32")
    train[..., 0] = np.linspace(0.0, 1.0, 4)[:, None]
    scaler = Scaler.fit(train)

    assert scaler.apply(train)[..., 0].min() == pytest.approx(0.0)
    assert scaler.apply(train)[..., 0].max() == pytest.approx(1.0)

    unseen = np.full((1, 10, len(FEATURE_COLUMNS)), 3.0, dtype="float32")
    assert scaler.apply(unseen)[..., 0].max() > 1.0, (
        "unseen data landing inside 0-1 would mean the scaler had seen it"
    )


def test_the_leakage_guard_runs_over_the_feature_columns_and_can_reject():
    """The phase wants the guard's output pasted, which is worth nothing if the guard cannot fail.

    Broken on purpose here, per the repo's own rule: a test that has never been seen to fail is
    not known to work.
    """
    report = assert_features_are_clean()
    for col in FEATURE_COLUMNS:
        assert col in report

    from eval.loaders.columns import assert_feature_safe

    with pytest.raises(LeakageError):
        assert_feature_safe([*FEATURE_COLUMNS, "wheel_speed_fl"])


# ------------------------------------------------------------------------------------------
# The split the papers do not describe
# ------------------------------------------------------------------------------------------


def _windows(name: str, n: int) -> StemWindows:
    return StemWindows(
        name=name,
        x=np.zeros((n, 10, len(FEATURE_COLUMNS)), dtype="float32"),
        y=np.zeros((n, 2), dtype="float32"),
    )


def test_the_validation_split_survives_families_two_orders_apart():
    """The real failure this rule exists for: `S1` is 43% of the windows and `Vw14` 32%.

    Both earlier rules produced a split that was deterministic and useless -- one left 2,461
    windows to train on against 9,472 to validate, the other made a single drive the entire
    early-stopping signal. Smallest-first keeps the dominant drives in training and still gives
    validation more than one family to speak for.
    """
    kept = [_windows("S1", 5172), _windows("Vw14a", 3839), _windows("Vta2", 1097)]
    kept += [_windows(f"Vw{i}", 30 + 10 * i) for i in range(3, 14)]

    fams = validation_families(kept)
    total = sum(w.x.shape[0] for w in kept)
    held = sum(w.x.shape[0] for w in kept if w.name.rstrip("abc") in fams or w.name in fams)

    assert len(fams) >= 3, "one family cannot carry an early-stopping signal"
    assert "S1" not in fams and "Vw14" not in fams, "the dominant drives belong in training"
    assert held < 0.5 * total
    assert held >= VALIDATION_FRACTION * total * 0.9


def test_a_degenerate_split_raises_rather_than_training_on_it():
    with pytest.raises(ValueError, match="degenerate"):
        validation_families([_windows("S1", 100)])


# ------------------------------------------------------------------------------------------
# Small things that are wrong in an invisible way
# ------------------------------------------------------------------------------------------


def test_heading_differences_wrap():
    """359 degrees to 1 degree is +2, not -358. Unwrapped, a single wrap puts a 6.2 rad target in
    front of a network whose other targets are ~0.05, and MAE lets it dominate the epoch."""
    assert wrap_to_pi(np.array([np.radians(2.0)])) == pytest.approx(np.radians(2.0))
    assert wrap_to_pi(np.array([np.radians(-358.0)])) == pytest.approx(np.radians(2.0))
    assert wrap_to_pi(np.array([np.pi + 0.1]))[0] == pytest.approx(-np.pi + 0.1)


def test_the_architecture_and_the_trainer_agree_on_the_window():
    """Two constants, two modules, one meaning. `train` asserts this at run time; this is the
    version that runs in the job without torch."""
    torch = pytest.importorskip("torch")  # noqa: F841
    from models.baseline_rnn import WINDOW_SAMPLES as arch
    from models.train_baseline_rnn import WINDOW_SAMPLES as trainer

    assert arch == trainer == 10


def test_the_three_target_columns_are_what_they_claim_to_be():
    """`y` is `(distance, d_heading, d_distance)` and `TARGET_COLUMNS` indexes into it.

    A silently transposed pair here trains the network on the wrong quantity and still converges,
    which is the failure mode D-099 exists to make visible rather than plausible.
    """
    seq, truth = synthetic_drive(seconds=120.0, mps=12.0)
    w = epoch_windows(seq, truth)

    assert w.y.shape[1] == 3
    assert w.y[:, 0] == pytest.approx(12.0, abs=0.05), "column 0 is travel in the second"
    assert w.y[:, 2] == pytest.approx(0.0, abs=0.05), "column 2 is the *change* in that travel"
    assert TARGET_COLUMNS["distance"] == (0, 1)
    assert TARGET_COLUMNS["delta_speed"] == (2, 1)
    assert DEFAULT_TARGET == "delta_speed"
