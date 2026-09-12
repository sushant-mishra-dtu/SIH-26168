"""The two Android surfaces, held to the rules `tests/test_replay.py` holds the web page to.

There are two of them and they are not the same thing:

* ``android/`` is the foreground logger, and its ``replay/`` package renders an ``idr-trajectory/1``
  record produced by ``eval/run.py``.
* ``android-ui/`` is a second Gradle root carrying the operator UI, live over the phone's own
  sensors through a small on-device estimator that is explicitly not the evaluated filter.

Both are demo surfaces, so D-041's offline claim, D-079's "the renderer computes nothing" rule and
D-080's "no simulated fallback" rule apply to both.

**Why this is a Python test.** ``android/app/src/test`` already contains a Kotlin guard making the
same assertions about the replay package, and it is the better test -- it runs against the compiled
source. It also runs nowhere: the Android SDK is a 400 MB download from ``dl.google.com``, no
contributor's laptop is guaranteed to have it, and until ``.github/workflows/android.yml`` existed
nothing in CI ran ``:app:test`` at all. This file runs in the harness suite that every seat already
runs on every commit. It reads the sources as text, which is a weaker check than compiling them and
a much stronger one than a check that never executes.

Text matching is deliberate and so is its bluntness. Each assertion below names the decision it
enforces, so a failure is a conversation about that decision rather than a puzzle.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LOGGER_APP = REPO / "android" / "app" / "src" / "main"
UI_APP = REPO / "android-ui" / "app" / "src" / "main"
REPLAY_PKG = LOGGER_APP / "kotlin" / "org" / "idr26168" / "logger" / "replay"


def _kotlin(root: Path) -> dict[str, str]:
    """Every Kotlin source under `root`, keyed by its path relative to the repo.

    Keys are POSIX-style (`android/app/...`) on every platform: the assertions below name files
    with forward slashes, and `str(Path)` on Windows would yield backslashes and match none."""
    return {
        p.relative_to(REPO).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*.kt"))
    }


LOGGER_SOURCES = _kotlin(LOGGER_APP)
UI_SOURCES = _kotlin(UI_APP)
ALL_SOURCES = {**LOGGER_SOURCES, **UI_SOURCES}
REPLAY_SOURCES = _kotlin(REPLAY_PKG)


def test_both_modules_are_present_so_an_empty_glob_cannot_pass_this_file():
    """Every test below iterates over a dict. A rename that empties one of them would turn this
    whole file green while checking nothing, which is the failure mode of a guard test."""
    assert REPLAY_SOURCES, f"no Kotlin sources under {REPLAY_PKG}"
    assert UI_SOURCES, f"no Kotlin sources under {UI_APP}"
    assert "android/app/src/main/kotlin/org/idr26168/logger/replay/ReplayActivity.kt" in ALL_SOURCES
    assert "android-ui/app/src/main/java/com/sih/idr/demo/MainActivity.kt" in ALL_SOURCES


# ------------------------------------------------------------------------------------------
# D-041 / D-080: no network at runtime, on either surface
# ------------------------------------------------------------------------------------------

#: Hosts and SDKs that mean a runtime fetch. `osmdroid` and `ui-text-google-fonts` are both here
#: because both shipped in `android-ui` and neither looks like a network call at the call site:
#: one is a `MapView`, the other is a `FontFamily`.
NETWORK_MARKERS = (
    r"https?://",
    r"cartocdn",
    r"tile\.openstreetmap",
    r"osmdroid",
    r"com\.google\.android\.gms\.maps",
    r"googlefonts",
    r"GoogleFont",
    r"HttpURLConnection",
    r"OkHttp",
    r"Retrofit",
    r"URLConnection",
)


@pytest.mark.parametrize("path", sorted(ALL_SOURCES))
def test_no_android_source_reaches_for_the_network(path):
    """D-041 claims 100% offline; D-080 forbids the demo surface any fetch. A judging venue's wifi
    is not a dependency worth having, and "it works on my machine, which has the tiles cached" is
    how that gets discovered on the day."""
    text = ALL_SOURCES[path]
    # Prose about the rule is allowed to name what the rule forbids; code is not. Comments are
    # stripped first so the explanation of a removal cannot trip the check on the removal.
    code = _strip_comments(text)
    for marker in NETWORK_MARKERS:
        assert not re.search(marker, code, re.IGNORECASE), f"{path}: network reference {marker!r}"


def _strip_comments(kotlin: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", "", kotlin, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", without_block)


def _as_displayed(kotlin: str) -> str:
    """One line, with Kotlin's `"..." + "..."` joins closed up.

    A caption long enough to be worth asserting is long enough to be wrapped across source lines,
    and the wrap is a formatting choice that must not be able to break an assertion about what the
    user reads.
    """
    return re.sub(r'"\s*\+\s*"', "", re.sub(r"\s+", " ", kotlin))


def test_neither_manifest_asks_for_the_internet():
    """The permission is the load-bearing part: without it a reintroduced fetch fails at runtime
    instead of quietly working on the one phone that has a data plan."""
    for manifest in (LOGGER_APP / "AndroidManifest.xml", UI_APP / "AndroidManifest.xml"):
        text = manifest.read_text(encoding="utf-8")
        declared = re.findall(r'uses-permission android:name="([^"]+)"', text)
        assert "android.permission.INTERNET" not in declared, manifest
        assert "android.permission.ACCESS_NETWORK_STATE" not in declared, manifest


def test_the_ui_module_declares_no_map_sdk_or_downloaded_font_dependency():
    """Checked at the dependency rather than the call site: a Gradle coordinate is what lets the
    import compile, and it survives a source file being rewritten."""
    build = (REPO / "android-ui" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    code = _strip_comments(build)
    for coordinate in ("osmdroid", "ui-text-google-fonts", "play-services-maps", "maps-compose"):
        assert coordinate not in code, f"android-ui depends on {coordinate}"


# ------------------------------------------------------------------------------------------
# D-079 / D-080: the surface computes nothing and invents nothing
# ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(REPLAY_SOURCES))
def test_the_replay_view_never_recomputes_a_displayed_metric(path):
    """Drift-% and yaw error are computed in `eval/run.py::trajectory_record` and read from the
    record. If the view derived them it could display a number the evaluation never produced --
    and it would agree with the harness for a while, which is how that error survives review."""
    code = _strip_comments(REPLAY_SOURCES[path])
    assert not re.search(r"/\s*\w*\.?distanceM", code), f"{path}: divides by distanceM"
    assert not re.search(r"\batan2\b", code), f"{path}: derives an angle"


@pytest.mark.parametrize("path", sorted(ALL_SOURCES))
def test_no_android_surface_carries_a_random_number_generator(path):
    """D-080. A renderer has no business with a random number, and neither has a view that claims
    to be showing a recording."""
    code = _strip_comments(ALL_SOURCES[path])
    assert not re.search(r"\bRandom\b|Math\.random|kotlin\.random", code), f"{path}: RNG"


def test_the_replay_view_refuses_a_record_whose_schema_it_does_not_know():
    """Same rule as the web page: refuse the file rather than draw an older layout's fields in the
    wrong places."""
    record = REPLAY_SOURCES[
        "android/app/src/main/kotlin/org/idr26168/logger/replay/TrajectoryRecord.kt"
    ]
    assert 'REQUIRED_SCHEMA = "idr-trajectory/1"' in record
    assert "Unrecognised schema" in record
    assert "throw IllegalArgumentException" in record


def test_the_schema_string_the_view_requires_is_the_one_the_harness_writes():
    """The one assertion here that catches a drift between two files rather than a rule broken in
    one. `eval/run.py` owns the string."""
    from eval.run import TRAJECTORY_SCHEMA

    record = REPLAY_SOURCES[
        "android/app/src/main/kotlin/org/idr26168/logger/replay/TrajectoryRecord.kt"
    ]
    assert f'REQUIRED_SCHEMA = "{TRAJECTORY_SCHEMA}"' in record


def test_every_field_the_replay_view_reads_is_a_field_the_harness_writes():
    """Field-by-field, against the writer's own dict literal. A renamed key on either side shows
    up here rather than as an empty chart."""
    written = set(
        re.findall(r'^\s*"(\w+)":', _trajectory_record_source(), flags=re.MULTILINE)
    )
    record = REPLAY_SOURCES[
        "android/app/src/main/kotlin/org/idr26168/logger/replay/TrajectoryRecord.kt"
    ]
    read = set(re.findall(r'(?:optString|optInt|optDouble|optBoolean|optJSONArray|isNull)'
                          r'\(\s*"(\w+)"', record))
    assert read, "the parser reads nothing -- the regex has stopped matching, not the code"
    assert read <= written, f"read but never written: {sorted(read - written)}"


def _trajectory_record_source() -> str:
    """The body of `eval/run.py::trajectory_record`, which is where the keys are literals."""
    text = (REPO / "eval" / "run.py").read_text(encoding="utf-8")
    start = text.index("def trajectory_record(")
    end = text.index("\ndef ", start + 1)
    return text[start:end]


def test_the_operator_ui_shows_no_telemetry_it_was_not_given():
    """The specific thing that was here: a `PREVIEW_TELEMETRY` constant, rendered whenever the
    service was not running, carrying `sampleRateHz = 200f` and `timestampJitterMs = 0.8f`.

    Those two are per-device measurements this project has never made on any phone
    (`android/HANDOVER.md` §1), and 200 Hz is the FOG configuration D-081 requires captioned as
    *not demonstrated*. Rendered in the same typeface as a real reading, an invented one is
    indistinguishable from evidence in a screenshot."""
    for path, text in UI_SOURCES.items():
        code = _strip_comments(text)
        assert "PREVIEW_TELEMETRY" not in code, f"{path}: preview telemetry constant is back"
        assert not re.search(r"\bsampleRateHz\s*=\s*[0-9]", code), f"{path}: literal sample rate"
        assert not re.search(r"\btimestampJitterMs\s*=\s*[0-9]", code), f"{path}: literal jitter"


def test_the_operator_ui_states_what_produced_its_numbers():
    """D-081, and the reason it is asserted rather than trusted: the caption is the first thing
    removed when the sheet is one line too tall for a slide."""
    screen = UI_SOURCES[
        "android-ui/app/src/main/java/com/sih/idr/demo/ui/screens/NavigationScreen.kt"
    ]
    flowed = _as_displayed(screen)
    assert "not the evaluated InEKF" in flowed
    assert "200 Hz FOG configuration is not " in flowed
    assert "Not recording." in flowed


def test_the_replay_caption_names_the_stream_and_the_rate_and_disclaims_200_hz():
    """The same rule for the same reason, on the other surface. Mirrors
    `test_replay.py::test_the_sensor_caption_names_the_stream_and_the_rate_and_disclaims_200_hz`."""
    activity = REPLAY_SOURCES[
        "android/app/src/main/kotlin/org/idr26168/logger/replay/ReplayActivity.kt"
    ]
    flowed = _as_displayed(activity)
    assert "record.stream" in activity and "record.imuRateHz" in activity
    assert "200 Hz FOG configuration is not demonstrated" in flowed


def test_the_replay_view_shows_an_empty_state_rather_than_inventing_a_record():
    """The failure D-039 and D-080 exist to prevent, asserted against the code path: the empty
    state is a view that is shown, not a record that is manufactured."""
    activity = REPLAY_SOURCES[
        "android/app/src/main/kotlin/org/idr26168/logger/replay/ReplayActivity.kt"
    ]
    assert "emptyStateView" in activity
    assert "R.id.empty_state" in activity
    catches = re.findall(r"catch\s*\([^)]*\)\s*\{(.*?)\n        \}", activity, re.DOTALL)
    assert catches, "the load path has no catch -- has it stopped handling a bad file?"
    for body in catches:
        assert not re.search(r"random|generate|simulat|synth", body, re.IGNORECASE)
