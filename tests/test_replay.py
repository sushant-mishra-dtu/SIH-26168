"""The replay renderer (P-13) and the artefact it reads.

Two things are tested, and the second matters more than the first.

1. The record `eval/run.py` writes is exactly the record the page reads: same schema string, same
   field names, same lengths. A renderer and a writer that drift apart produce a page that draws
   an older layout's fields in the wrong places, which looks like a result.

2. **The page contains no physics, no simulation, and no network.** That is the whole point of
   D-039: a cockpit fed by its own generator can display numbers the evaluation never produced.
   Asserted mechanically, because it is the property most likely to be eroded by a well-meaning
   edit ("just show something when the file is missing").
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from eval.run import TRAJECTORY_SCHEMA, evaluate_sequence, write_artefacts
from idr.stamp import seed_everything
from tests.test_harness_wiring import synthetic_drive

PAGE = Path(__file__).resolve().parents[1] / "eval" / "replay" / "replay.html"
TEXT = PAGE.read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------
# The page is a renderer, not a system
# ------------------------------------------------------------------------------------------


def test_the_page_makes_no_network_request_of_any_kind_beyond_its_own_artefacts():
    """No CDN, no font, no map SDK, no analytics. A demo that needs the network cannot back a
    "100% offline" claim (D-041), and a judge's venue wifi is not a dependency worth having."""
    for pattern in (r"https?://", r"//cdn\.", r"<script[^>]+src=", r"<link[^>]+href="):
        assert not re.search(pattern, TEXT, re.IGNORECASE), f"external reference: {pattern}"
    # The only fetches are same-directory harness artefacts.
    for url in re.findall(r"fetch\(\s*[`\"']([^`\"')]+)", TEXT):
        assert url.startswith("summary.json") or url.startswith("trajectory_"), url


def test_the_page_is_one_self_contained_file_with_no_build_step():
    assert PAGE.suffix == ".html"
    assert list(PAGE.parent.iterdir()) == [PAGE], "the renderer is one file, not a project"
    assert "<style>" in TEXT and "<script>" in TEXT, "CSS and JS are inline"


def test_the_no_simulator_rule_is_written_into_the_file():
    """It has to survive someone editing the page a month from now without this conversation."""
    flowed = re.sub(r"\s+", " ", TEXT)
    assert "THIS PAGE CONTAINS NO PHYSICS AND NO SIMULATION." in flowed
    assert "no fallback that invents data when a file is missing" in flowed


def test_a_missing_artefact_shows_an_empty_state_and_never_manufactures_one():
    """The specific failure D-039 exists to prevent. Asserted against the code path: the fetch is
    wrapped in a catch whose body creates nothing."""
    assert 'id="empty"' in TEXT
    assert "No harness output loaded" in TEXT
    catch = re.search(r"\}\s*catch\s*\{([^}]*)\}", TEXT)
    assert catch is not None
    assert not re.search(r"random|Math\.random|generate|simulat|synth", catch.group(1), re.I)
    assert "Math.random" not in TEXT, "a renderer has no business with a random number"


def test_the_page_never_recomputes_a_displayed_metric():
    """Drift-% and yaw error come out of the artefact. If the page computed them it could display
    a number the harness never produced -- and it would be the *same* number for a while, which is
    how that error survives review."""
    assert "current.drift_pct[k]" in TEXT
    assert "current.yaw_error_deg[k]" in TEXT
    # And it never derives them: drift-% is an error over a distance and yaw error is a wrapped
    # angle difference, so neither `distance_m` in a denominator nor an atan2 may appear.
    assert not re.search(r"/\s*(?:current|r)\.distance_m", TEXT)
    assert "Math.atan2" not in TEXT
    assert "truth_ned[" not in re.sub(r"r\.truth_ned", "", TEXT), (
        "the page indexes truth only to draw it, never to difference it against an estimate"
    )


def test_the_stamp_is_rendered_on_the_page_and_a_dirty_run_is_marked():
    """A screenshot of the demo has to be self-evidencing (H-5), and an artefact from a dirty tree
    must not pass for one that can be regenerated."""
    assert 'id="stamp"' in TEXT
    assert "NOT REPRODUCIBLE" in TEXT
    assert "current.stamp" in TEXT


def test_the_sensor_caption_names_the_stream_and_the_rate_and_disclaims_200_hz():
    """We cannot demonstrate a 200 Hz pipeline on IO-VNBD and we will not appear to."""
    flowed = re.sub(r"\s+", " ", TEXT)
    assert "${current.stream} smartphone stream at ${current.imu_rate_hz} Hz" in flowed
    assert "200 Hz FOG configuration is not demonstrated on this dataset" in flowed


def test_the_page_refuses_a_record_whose_schema_it_does_not_know():
    assert f'SCHEMA = "{TRAJECTORY_SCHEMA}"' in TEXT
    assert "record.schema !== SCHEMA" in TEXT


def test_all_four_trajectories_and_the_ellipse_are_drawn():
    for field in ("truth_ned", "filter_ned", "strapdown_ned", "gnss_ned", "position_sigma_m"):
        assert field in TEXT, f"{field} is written by the harness but never drawn"
    assert "g.ellipse(" in TEXT


# ------------------------------------------------------------------------------------------
# The writer and the page agree
# ------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def artefacts(tmp_path_factory):
    """A real harness run over the synthetic drive, written to disk exactly as `main` writes it."""
    out = tmp_path_factory.mktemp("figures")
    seq, truth = synthetic_drive(seconds=200.0, name="S3a")  # a MANDATORY_PLOT_SEQUENCES stem
    stamp = seed_everything(0)
    replay: dict[str, dict] = {}
    results = evaluate_sequence(seq, truth, [60], replay=replay, stamp=stamp)
    write_artefacts(out, stamp, results, replay)
    return out, replay


def test_the_harness_writes_a_trajectory_for_each_mandatory_plot_sequence(artefacts):
    out, replay = artefacts
    assert "S3a" in replay
    written = json.loads((out / "trajectory_S3a.json").read_text(encoding="utf-8"))
    assert written["schema"] == TRAJECTORY_SCHEMA
    assert json.loads((out / "summary.json").read_text(encoding="utf-8"))["trajectories"] == ["S3a"]


def test_every_field_the_page_reads_is_a_field_the_harness_writes(artefacts):
    """The drift-and-crash case: a renamed field renders as `undefined` and the page draws
    nothing where a trajectory should be, which is easy to miss on a slide."""
    _, replay = artefacts
    record = replay["S3a"]
    read_by_page = {
        m.group(1)
        for m in re.finditer(r"\b(?:current|record|r)\.([a-z_][a-z0-9_]*)", TEXT)
    }
    known_non_fields = {"files", "text", "value", "max", "textContent", "className", "hidden"}
    for field in read_by_page - known_non_fields:
        if field in ("stamp", "schema", "sequence", "reproducible"):
            continue
        assert field in record, f"the page reads `{field}`, which the harness does not write"


def test_the_series_the_page_plots_are_the_lengths_it_assumes(artefacts):
    """`length_s + 1` epoch boundaries against `10 * length_s` IMU samples. The page indexes the
    IMU trace by scaling from the epoch index, so a mismatch draws the cursor in the wrong place.
    """
    _, replay = artefacts
    r = replay["S3a"]
    n = r["length_s"] + 1
    for field in ("epoch_s", "truth_ned", "filter_ned", "strapdown_ned",
                  "position_sigma_m", "drift_pct", "yaw_error_deg"):
        assert len(r[field]) == n, f"{field} has {len(r[field])} entries, expected {n}"
    assert len(r["accel_mps2"]) == r["length_s"] * r["imu_rate_hz"]
    assert len(r["gyro_rps"]) == len(r["accel_mps2"])


def test_the_record_carries_the_stamp_and_the_stream_and_the_rate(artefacts):
    _, replay = artefacts
    r = replay["S3a"]
    assert r["stamp"] and r["stream"] == "S-" and r["imu_rate_hz"] == 10
    assert isinstance(r["reproducible"], bool)


def test_drift_and_yaw_are_computed_by_the_harness_and_are_finite(artefacts):
    _, replay = artefacts
    r = replay["S3a"]
    assert np.isfinite(r["drift_pct"]).all()
    assert np.isfinite(r["yaw_error_deg"]).all()
    assert r["drift_pct"][0] == pytest.approx(0.0, abs=1e-9), "drift is zero at the outage boundary"


def test_a_replay_record_without_a_stamp_is_refused():
    seq, truth = synthetic_drive(seconds=200.0, name="S3a")
    with pytest.raises(ValueError, match="must carry the run's stamp"):
        evaluate_sequence(seq, truth, [60], replay={})
