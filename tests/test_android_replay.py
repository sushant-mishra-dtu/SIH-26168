"""Tests for the Android trajectory replay viewer (HANDOVER.md section 3a).

Mirrors `tests/test_replay.py` for the Android codebase, ensuring that the Android
view obeys the identical non-negotiable architectural constraints:
1. Contains NO physics, NO simulation, and NO network (D-039, D-041, D-079, D-080).
2. Reads the exact `idr-trajectory/1` record that `eval/run.py` writes.
3. Does not re-derive drift-% or yaw error (no distance division, no atan2).
4. Captions stream and rate, and disclaims 200 Hz FOG configuration (D-081).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from eval.run import TRAJECTORY_SCHEMA

_ROOT = Path(__file__).resolve().parents[1]
_REPLAY_DIR = _ROOT / "android" / "app" / "src" / "main" / "kotlin" / "org" / "idr26168" / "logger" / "replay"
_LAYOUT = _ROOT / "android" / "app" / "src" / "main" / "res" / "layout" / "activity_replay.xml"

_RECORD_KT = _REPLAY_DIR / "TrajectoryRecord.kt"
_PARSER_KT = _REPLAY_DIR / "TrajectoryParser.kt"
_MAP_VIEW_KT = _REPLAY_DIR / "TrajectoryMapView.kt"
_SERIES_VIEW_KT = _REPLAY_DIR / "TrajectorySeriesView.kt"
_IMU_VIEW_KT = _REPLAY_DIR / "TrajectoryImuView.kt"
_ACTIVITY_KT = _REPLAY_DIR / "ReplayActivity.kt"

ALL_KT_FILES = [_RECORD_KT, _PARSER_KT, _MAP_VIEW_KT, _SERIES_VIEW_KT, _IMU_VIEW_KT, _ACTIVITY_KT]


def test_all_android_replay_source_files_exist():
    for f in ALL_KT_FILES:
        assert f.exists(), f"Missing required file: {f.name}"
    assert _LAYOUT.exists(), "Missing layout file: activity_replay.xml"


def test_android_replay_makes_no_network_requests():
    """No network: no HTTP clients, no URLs, no tile fetchers (D-041, D-080)."""
    disallowed = [
        r"https?://",
        r"HttpURLConnection",
        r"okhttp",
        r"HttpClient",
        r"Retrofit",
        r"Volley",
    ]
    for path in ALL_KT_FILES:
        text = path.read_text(encoding="utf-8")
        for pattern in disallowed:
            assert not re.search(pattern, text, re.IGNORECASE), f"Disallowed network pattern '{pattern}' in {path.name}"


def test_android_replay_computes_no_physics():
    """Drift-% and yaw error must come from the record, never derived (D-079)."""
    for path in ALL_KT_FILES:
        text = path.read_text(encoding="utf-8")
        # Assert no division by distance
        assert not re.search(r"/\s*(?:current|r\.)?distance[mM]", text), (
            f"{path.name} divides by distance; drift-% must be read from the record"
        )
        # Assert no atan2
        assert "atan2" not in text, f"{path.name} computes atan2; yaw error must be read from record"


def test_android_replay_contains_no_simulation_or_random_fallback():
    """A missing file shows empty state; no synthetic fallback or Math.random (D-080)."""
    for path in ALL_KT_FILES:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bRandom\b|Math\.random", text), (
            f"{path.name} references random number generation (D-080 violation)"
        )


def test_android_replay_refuses_unknown_schema():
    """Record schema must be pinned to idr-trajectory/1 and refuse other versions."""
    text = _RECORD_KT.read_text(encoding="utf-8") + "\n" + _PARSER_KT.read_text(encoding="utf-8")
    assert f'"{TRAJECTORY_SCHEMA}"' in text
    assert "not an idr-trajectory/1 record" in text


def test_android_replay_captions_stream_and_disclaims_200_hz():
    """Caption discipline (D-081): 200 Hz FOG disclaimed, smartphone stream identified."""
    activity_text = _ACTIVITY_KT.read_text(encoding="utf-8")
    layout_text = _LAYOUT.read_text(encoding="utf-8")
    combined = activity_text + "\n" + layout_text
    assert "200 Hz FOG configuration is not demonstrated on this dataset" in combined
    assert "smartphone stream at" in combined


def test_all_four_tracks_and_ellipse_drawn_in_map_view():
    map_text = _MAP_VIEW_KT.read_text(encoding="utf-8")
    for field in ("truthNed", "filterNed", "strapdownNed", "gnssNed", "positionSigmaM"):
        assert field in map_text, f"{field} must be rendered by TrajectoryMapView"
    assert "drawOval" in map_text or "drawArc" in map_text, "1-sigma ellipse must be drawn"
