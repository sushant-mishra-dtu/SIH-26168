"""The Onyekpe reproduction's hyperparameter audit (P-06).

Tests the *audit*, not the training, because training is blocked twice over: the nine omitted
hyperparameters have no DECISION_LOG rows yet, and the IO-VNBD files are not fetchable in this
container (D-059). The audit is what the phase requires before anything trains, and it is the
part that has to stay honest -- a silence that quietly becomes a constant in a config file is how
a reproduction stops being one.

No torch import here: `models/train_baseline_rnn.py` keeps its torch import inside `main`
precisely so this module is testable in a CI job that has no `ml` extra.
"""

from __future__ import annotations

import pytest

from models.train_baseline_rnn import HYPERPARAMETERS, audit_table, main


def test_every_omission_carries_a_decision_id_rather_than_a_bare_constant():
    """G-4 and D-009's discipline. An omitted hyperparameter is a choice *we* make, and a choice
    with no recorded reason is indistinguishable from a number someone tuned."""
    for h in HYPERPARAMETERS:
        if "OMITTED" in h.source:
            assert h.decision, f"{h.name!r} is omitted by the papers but names no decision"
            assert h.decision.startswith("D-")


def test_a_stated_hyperparameter_is_never_labelled_as_our_choice():
    """The inverse, which is the more dangerous direction: quietly relabelling a published value
    as ours would let it be changed without anyone noticing the reproduction stopped reproducing.
    """
    for h in HYPERPARAMETERS:
        if "OMITTED" not in h.source:
            assert not h.is_our_choice, f"{h.name!r} is stated by the paper but marked as ours"


def test_the_papers_disagreement_about_loss_and_optimiser_is_recorded():
    """The INS paper does not surface its loss or optimiser; those two rows come from WhONet. That
    is a real gap in the reproduction and it must be visible in the table rather than smoothed
    over by citing "the papers" collectively."""
    by_name = {h.name: h for h in HYPERPARAMETERS}
    for name in ("loss", "optimiser"):
        assert "NOT surfaced in the INS paper" in by_name[name].source


def test_the_scaler_fitting_set_is_flagged_as_a_leakage_risk():
    """Features are scaled 0-1 and the papers do not say on which set the scaler is fitted.
    Fitting it on train+test leaks the test set's range into training -- a leak the column
    allowlist cannot see, because no disallowed column is involved."""
    by_name = {h.name: h for h in HYPERPARAMETERS}
    assert "leakage risk" in by_name["scaler fitting set"].source


def test_the_audit_prints_the_table_and_trains_nothing():
    assert main(["--audit"]) == 0


def test_running_without_audit_refuses_rather_than_training_on_unresolved_choices(monkeypatch):
    """A stub that returned an untrained model's loss would produce a plausible number, which is
    worse than nothing."""
    monkeypatch.setitem(__import__("sys").modules, "torch", object())
    with pytest.raises(NotImplementedError, match="P-06 training"):
        main([])


def test_the_table_states_how_many_settings_are_ours():
    text = audit_table()
    ours = sum(h.is_our_choice for h in HYPERPARAMETERS)
    assert f"{ours} ours" in text
