"""The Android logger's CSV schema, checked against the loader that has to read it.

Seat A writes the file; seat D's loader decides whether it is readable. Nothing in a Gradle build
can tell them apart, so the contract is asserted here, in the suite that already runs on every
push, against the *live* `eval/loaders` -- not against a copy of what they said last week.

The reason this is worth a test rather than a comment: `io_vnbd.py::_canonicalise` runs
`assert_no_leakage` over **every** column in the file, not over the ones it means to use. So the
allowlist is a whitelist of the entire header, and one well-meant extra column in the app --
`accel_uncal_x`, `battery_pct` -- raises `LeakageError` on the whole recording. That failure would
land on a laptop after a drive, which is the most expensive place to find it.

Everything here is parsed out of the Kotlin sources rather than restated, so the test cannot agree
with a header the app no longer writes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from eval.loaders.columns import (
    ALLOWED_COLUMNS,
    GNSS_CHANNELS,
    INERTIAL_CHANNELS,
    LeakageError,
    assert_no_leakage,
    normalise,
)
from eval.loaders.io_vnbd import SAMPLE_RATE_HZ, load_sequence
from eval.loaders.truth import _S_DATE

_ANDROID = Path(__file__).resolve().parents[1] / "android" / "app" / "src" / "main" / "kotlin"
_LOGGER = _ANDROID / "org" / "idr26168" / "logger"

CHANNELS_KT = _LOGGER / "Channels.kt"
CLOCK_KT = _LOGGER / "SessionClock.kt"
SENSOR_HUB_KT = _LOGGER / "SensorHub.kt"


def _kotlin(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _header_from_kotlin() -> list[str]:
    """Pull `Channels.HEADER` out of the Kotlin source, in file order."""
    text = _kotlin(CHANNELS_KT)
    block = re.search(
        r"val HEADER: List<String> = listOf\((.*?)\n    \)", text, re.DOTALL
    )
    assert block, "Channels.HEADER is not in the shape this test knows how to read"
    return re.findall(r'"([^"]*)"', block.group(1))


def _const(path: Path, name: str) -> str:
    m = re.search(rf'const val {name} = "([^"]*)"', _kotlin(path))
    assert m, f"{name} not found in {path.name}"
    return m.group(1)


def _int_const(path: Path, name: str) -> int:
    m = re.search(rf"const val {name} = (\d+)", _kotlin(path))
    assert m, f"{name} not found in {path.name}"
    return int(m.group(1))


HEADER = _header_from_kotlin()


def test_the_app_header_was_found_and_is_the_expected_width():
    """24 columns: 1 relative clock + 15 inertial + 7 GNSS + 1 wall clock."""
    assert len(HEADER) == 24, HEADER


@pytest.mark.parametrize("column", HEADER)
def test_every_column_the_app_writes_normalises_onto_the_allowlist(column: str):
    canonical = normalise(column)
    assert canonical in ALLOWED_COLUMNS, (
        f"{column!r} normalises to {canonical!r}, which is not on the allowlist. "
        "The loader guards every column in the file, so this recording would not load at all."
    )


def test_the_header_passes_the_leakage_guard_itself():
    """The same call the loader makes, on the same strings, before any drive is recorded."""
    assert_no_leakage(HEADER, context="android logger header")


def test_the_header_carries_every_inertial_channel_and_no_column_twice():
    canonical = [normalise(c) for c in HEADER]
    assert len(canonical) == len(set(canonical)), "two headers collapse onto one canonical name"
    assert INERTIAL_CHANNELS.issubset(set(canonical)), (
        "the app drops an inertial channel IO-VNBD ships: "
        f"{sorted(INERTIAL_CHANNELS - set(canonical))}"
    )
    assert GNSS_CHANNELS.issubset(set(canonical)), (
        f"missing GNSS reference channels: {sorted(GNSS_CHANNELS - set(canonical))}"
    )


def test_the_uncalibrated_streams_stay_out_of_the_main_csv():
    """The app records uncalibrated accel and gyro -- `android/README.md` requires it, because the
    calibrated types subtract an OS bias estimate the filter is also estimating. They go to a
    sidecar. If one ever reaches the main header the file stops loading, so assert both halves:
    the app does register them, and none of them is a CSV column."""
    hub = _kotlin(SENSOR_HUB_KT)
    assert "TYPE_ACCELEROMETER_UNCALIBRATED" in hub
    assert "TYPE_GYROSCOPE_UNCALIBRATED" in hub
    for column in HEADER:
        assert "uncal" not in column.lower(), (
            f"{column!r} is in the main CSV header; uncalibrated data belongs in the sidecar"
        )


def test_the_csv_row_rate_is_the_rate_the_harness_windows_at():
    """`eval/outages/inject.py` sizes every outage from `SAMPLE_RATE_HZ`. A file at a different
    cadence loads fine and is then windowed as though it were a different length -- a 60 s outage
    on a 100 Hz file is 6 s of road."""
    assert _int_const(CHANNELS_KT, "CSV_ROW_HZ") == SAMPLE_RATE_HZ


def test_the_date_the_app_emits_parses_with_the_loader_pattern():
    """The app picks the sub-second separator that parses on both sides of D-086 (dot), rather
    than the colon the dataset ships, which only parses after that fix lands."""
    java_pattern = _const(CLOCK_KT, "DATE_PATTERN")
    sample = java_pattern
    for token, value in (
        ("yyyy", "2026"), ("MM", "09"), ("dd", "03"),
        ("HH", "14"), ("mm", "05"), ("ss", "07"), ("SSS", "123"),
    ):
        sample = sample.replace(token, value)

    m = _S_DATE.search(sample)
    assert m, (
        f"the app writes {sample!r} into the date column and eval/loaders/truth.py cannot read it"
    )
    assert (m.group("h"), m.group("m"), m.group("s")) == ("14", "05", "07")
    assert m.group("ms") == "123", "the milliseconds are being dropped on the loader side"


def test_a_file_written_with_this_header_loads_through_the_real_loader(tmp_path: Path):
    """End to end, against `load_sequence` itself. Everything above checks a part; this checks
    that the parts together produce something the harness accepts."""
    rows = [
        # t_ms, accel xyz, gravity xyz, gyro xyz, mag xyz, orient ypr, gps..., date
        "0.0,0.012,-0.043,9.802,0.001,-0.002,9.806,0.0011,-0.0004,0.0002,"
        "12.30,-4.10,-38.20,91.400,1.200,-0.300,"
        "28.54500000,77.19100000,216.400,0.000,4.100,0.000,17,2026-09-03 14:05:07.100",
        "100.0,0.031,-0.051,9.799,0.001,-0.002,9.806,0.0009,-0.0006,0.0001,"
        "12.31,-4.09,-38.22,91.500,1.210,-0.310,"
        "28.54500000,77.19100000,216.400,0.000,4.100,0.000,17,2026-09-03 14:05:07.200",
        "200.0,0.028,-0.049,9.801,0.001,-0.002,9.806,0.0010,-0.0005,0.0002,"
        "12.29,-4.11,-38.19,91.600,1.220,-0.320,"
        "28.54509000,77.19112000,216.600,12.400,4.000,88.100,18,2026-09-03 14:05:07.300",
    ]
    path = tmp_path / "S-IDR-TEST.csv"
    path.write_text("\n".join([",".join(HEADER), *rows]) + "\n", encoding="latin-1")

    seq = load_sequence(path)

    assert seq.n_samples == 3
    assert INERTIAL_CHANNELS.issubset(set(seq.imu.columns))
    # Two distinct positions in three rows: the loader takes fixes as position changes, never
    # forward-fills, and must not count the repeated row as a second fix.
    assert len(seq.gnss) == 2


def test_a_header_with_an_invented_column_is_refused(tmp_path: Path):
    """The failure mode this whole file exists to prevent, asserted rather than described."""
    header = [*HEADER, "BATTERY (pct)"]
    path = tmp_path / "S-IDR-BAD.csv"
    path.write_text(",".join(header) + "\n", encoding="latin-1")
    with pytest.raises(LeakageError):
        load_sequence(path)


def test_the_speed_column_is_km_per_hour_and_the_app_converts(tmp_path: Path):
    """`gps_speed_kmh` is km/h; `Location.getSpeed()` is m/s. The conversion belongs on the
    caller's side of the wall, where it is visible -- the same rule `core/ffi/idr_core.h` states
    for every unit crossing that boundary."""
    text = _kotlin(CHANNELS_KT)
    assert re.search(r"fun kmh\([^)]*\)[^=]*=\s*.*3\.6", text), (
        "Channels.kmh no longer applies the m/s -> km/h factor"
    )
    assert any(normalise(c) == "gps_speed_kmh" for c in HEADER)


def test_the_written_file_round_trips_through_the_loader_encoding(tmp_path: Path):
    """The loader reads latin-1 because the shipped IO-VNBD headers carry raw 0xB0/0xB5 bytes.
    Ours are ASCII on purpose, so the two encodings agree -- assert that, because a degree sign
    added later would be silently mangled rather than rejected."""
    for column in HEADER:
        assert column.isascii(), f"{column!r} is not ASCII; it will not survive the round trip"
    path = tmp_path / "S-IDR-ENC.csv"
    path.write_text(",".join(HEADER) + "\n", encoding="latin-1")
    assert pd.read_csv(path, encoding="latin-1", nrows=0).columns.tolist() == HEADER
