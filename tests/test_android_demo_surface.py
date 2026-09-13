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
#: The whole `src/` tree, not `src/main`: the operator UI has two product flavours since D-121
#: (`osm`, `mapbox`), each with its own source set, and every rule below applies to both.
UI_APP = REPO / "android-ui" / "app" / "src"
UI_MAPBOX_FLAVOUR = UI_APP / "mapbox"
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


@pytest.mark.parametrize("path", sorted(LOGGER_SOURCES))
def test_no_logger_source_reaches_for_the_network(path):
    """D-041 claims 100% offline for the evaluation logger (android/). The harness and data
    collection stream must never make network calls or depend on network availability."""
    text = LOGGER_SOURCES[path]
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


def test_logger_manifest_asks_for_no_internet():
    """The submission logger must be strictly offline (D-041). Without the permission,
    a reintroduced fetch fails at runtime rather than silently succeeding."""
    manifest = LOGGER_APP / "AndroidManifest.xml"
    text = manifest.read_text(encoding="utf-8")
    declared = re.findall(r'uses-permission android:name="([^"]+)"', text)
    assert "android.permission.INTERNET" not in declared, manifest
    assert "android.permission.ACCESS_NETWORK_STATE" not in declared, manifest


def _ui_build_script() -> str:
    return _strip_comments(
        (REPO / "android-ui" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    )


def test_the_ui_module_declares_no_play_services_or_downloaded_font_dependency():
    """Checked at the dependency rather than the call site. Downloadable fonts were a network
    call disguised as a `FontFamily` (D-111). `play-services-maps` is a proprietary map SDK the
    project never chose. `play-services-location` is the one the Mapbox docs recommend for "better
    raw location": it would be a second location source next to the InEKF's, which is precisely
    what D-123 rule R1 forbids -- the SDK must see one feed, ours, with no gap for its own
    extrapolator to fill.

    `maps-compose` was on this list until D-122 admitted the Mapbox stack for the `mapbox`
    flavour; the flavour split below is what now keeps it out of the `osm` build."""
    code = _ui_build_script()
    for coordinate in ("ui-text-google-fonts", "play-services-maps", "play-services-location"):
        assert coordinate not in code, f"android-ui depends on {coordinate}"


def test_each_map_engine_is_confined_to_its_own_product_flavour():
    """D-121: `osm` is the flavour CI can always build (no account, no token); `mapbox` is the one
    the navigation plan is built on. A map engine added to the shared `implementation`
    configuration would leak into both -- and, for Mapbox, would make the whole module depend on a
    Maven repository that refuses anonymous downloads."""
    code = _ui_build_script()
    assert re.search(r'"osmImplementation"\("org\.osmdroid', code), "osmdroid is not osm-only"
    assert re.search(r'"mapboxImplementation"\("com\.mapbox', code), "no mapbox flavour deps"
    assert not re.search(r'(?<!["\w])implementation\("(org\.osmdroid|com\.mapbox)', code), (
        "a map engine is declared for every flavour"
    )


def test_the_mapbox_flavour_switches_the_sdks_own_dead_reckoning_off():
    """D-123 rule R2, the single most important line in the Mapbox integration. The SDK's own
    words: with sensors enabled it "ignores location updates which don't match data from
    sensors". A demo that showed Mapbox's extrapolation instead of the InEKF's would be
    indistinguishable from ours on screen, and the option that causes it is one boolean."""
    sources = _kotlin(UI_MAPBOX_FLAVOUR)
    assert sources, f"no Kotlin sources under {UI_MAPBOX_FLAVOUR}"
    joined = "\n".join(_strip_comments(text) for text in sources.values())
    assert "enableSensors(false)" in joined, "the mapbox flavour never disables SDK sensors"
    assert "enableSensors(true)" not in joined, "the mapbox flavour enables SDK sensors"
    assert "locationProviderFactory(" in joined, "the SDK is not given the InEKF location provider"


@pytest.mark.parametrize(
    "path",
    sorted(
        p.relative_to(REPO).as_posix()
        for p in (REPO / "android-ui").rglob("*")
        if p.is_file()
        and p.suffix in {".kt", ".kts", ".xml", ".properties", ".md", ".yml", ".json"}
        and "build" not in p.parts
        and ".gradle" not in p.parts
        and p.name != "local.properties"
    ),
)
def test_no_mapbox_token_is_committed_under_the_ui_module(path):
    """D-122: the secret `sk.` downloads token lives in the per-machine Gradle user home and the
    public `pk.` token in the gitignored `local.properties`, injected at build time. Neither
    belongs in the tree, for the same reason D-111 removed a Google API key placeholder: a token
    that works in rehearsal and is revoked before the venue is worse than none."""
    text = (REPO / path).read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"\b[ps]k\.[A-Za-z0-9_-]{20,}", text), f"{path}: Mapbox token literal"


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


def test_the_tunnel_machine_is_pure_kotlin_with_an_injected_clock():
    """D-126: `TunnelFsm` decides when GNSS is suppressed and when a fix counts as verified, and
    it is the one piece of the demo whose every transition is reproducible from a list of signal
    events. That holds only while it has no Android import and reads no clock of its own -- the
    moment it calls `SystemClock` it can no longer be driven by a JUnit test on a laptop, which is
    where the 33 scenarios that pin its behaviour run."""
    fsm = UI_SOURCES["android-ui/app/src/main/java/com/sih/idr/demo/backend/tunnel/TunnelFsm.kt"]
    code = _strip_comments(fsm)
    assert not re.search(r"^\s*import\s+android[x]?\.", code, re.MULTILINE), (
        "Android import in the FSM"
    )
    assert "SystemClock" not in code and "System.currentTimeMillis" not in code, (
        "the FSM reads a clock"
    )
    assert "nowMs: Long" in code, "the FSM no longer takes its time from the caller"
    test = REPO / "android-ui" / "app" / "src" / "test" / "java" / "com" / "sih" / "idr" / "demo"
    assert (test / "backend" / "tunnel" / "TunnelFsmTest.kt").exists(), "the FSM tests are gone"


def test_the_estimator_reports_forced_acceptances_as_forced():
    """D-126 deviation 3 / D-115: the fix applied after N consecutive rejections is on the record
    as `FORCED`, never as `ACCEPTED`, so the exit toast cannot say a verification happened when the
    anti-lockout rule fired instead."""
    est = UI_SOURCES[
        "android-ui/app/src/main/java/com/sih/idr/demo/backend/LocalNavigationEstimator.kt"
    ]
    code = _strip_comments(est)
    assert "FixVerdict.FORCED" in code, "no forced verdict path"
    assert "MAX_CONSECUTIVE_REJECTIONS" in code
    assert "CHI2_GATE_2DOF_99" in code, "the gate threshold is not the shared constant"
    toast = UI_SOURCES[
        "android-ui/app/src/main/java/com/sih/idr/demo/ui/components/ReconvergenceToast.kt"
    ]
    assert "reacquiredByForce" in toast, "the toast does not distinguish a forced re-acquisition"


@pytest.mark.parametrize("path", sorted(UI_SOURCES))
def test_no_operator_ui_surface_labels_a_drift_or_a_grade(path):
    """D-124, restating D-112 for every new screen: drift is error against truth as a percentage
    of distance -- the graded metric -- and a phone has no truth, so no Android surface may print
    a number under that name, nor award itself a grade for it. The on-device vocabulary is
    `est. sigma` (from the covariance) and, at a tunnel exit, `exit residual vs GNSS`.

    The D-081 caption is allowed to say what a figure is *not*; a label is not."""
    code = _strip_comments(UI_SOURCES[path])
    for literal in re.findall(r'"((?:[^"\\]|\\.)*)"', code):
        assert not re.search(r"(?i)\bdrift\s*(est|accuracy|:|%|\()|\bm\s+drift\b", literal), (
            f"{path}: drift used as a label: {literal!r}"
        )
        assert not re.search(r"\bGrade\b\s*:?", literal), (
            f"{path}: a self-awarded grade: {literal!r}"
        )


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
    # D-121: the caption also names the map engine, per flavour, so a screenshot says whether the
    # basemap under the track was OSMDroid or the Mapbox SDK.
    assert "MapStack.engineCaption" in screen
    for flavour in ("osm", "mapbox"):
        stack = UI_SOURCES[
            f"android-ui/app/src/{flavour}/java/com/sih/idr/demo/ui/components/MapStack.kt"
        ]
        assert "engineCaption" in stack, f"{flavour} flavour has no engine caption"


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
