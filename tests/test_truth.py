"""Ground truth from the paired `V-` VBOX GPS, and the cadence measurement behind it.

Two things are under test here, and they pull in opposite directions. The truth loader has to
reach into a stream that PS 26168 disallows, so most of this file is about the ways it must stay
narrow: the allowlist, the absence of a feature path, and the refusal to interpolate. The rest
checks that the thing it replaces -- 1 s ground truth off a 9 s smartphone GPS -- now fails loudly
instead of quietly returning a number.

No test here needs the dataset. The fixtures are synthetic files carrying the headers IO-VNBD
actually ships.
"""

from __future__ import annotations

import csv

import numpy as np
import pytest

from eval.cadence import measure_cadence, summarise
from eval.loaders.columns import LeakageError, assert_feature_safe
from eval.loaders.io_vnbd import load_sequence
from eval.loaders.truth import (
    DEFAULT_MANIFEST,
    MAX_EPOCH_OFFSET_S,
    TRUTH_COLUMNS,
    TRUTH_RATE_HZ,
    AlignmentReport,
    TruthPairingError,
    TruthTrack,
    align_to_sequence,
    assert_truth_only,
    divergent_copies,
    load_truth,
    manifest_path_for,
    normalise_truth_header,
    paired_truth_path,
    seconds_of_day,
    unwrap_time_of_day,
)

DT = 1.0 / TRUTH_RATE_HZ

# The real "V-" wheel columns, spelled as they ship (see tests/test_allan.py).
SHIPPED_V_BANNED = [
    " Wheel Speed Front Left (rad/sec)",
    " Steering Angle (degrees)",
    " Engine Speed (rev/min)",
    " Brake Pressure (psi)",
]


def _v_csv(path, *, n=600, t0=43_200.0, lat0=52.4, lon0=-1.5, dt=DT, banned=True):
    """A synthetic `V-` file: 10 Hz GPS, plus the banned columns that ship beside it."""
    t = t0 + np.arange(n) * dt
    # ~16 m/s due north, so a one-second misalignment is ~16 m of residual.
    lat = lat0 + np.arange(n) * (16.0 * dt) / 111_320.0
    cols = {
        " Time Since Start of Day (seconds)": t,
        " GPS Latitude (degrees)": lat,
        " GPS Longitude (degrees)": np.full(n, lon0),
    }
    if banned:
        for name in SHIPPED_V_BANNED:
            cols[name] = np.zeros(n)
    header = ",".join(cols)
    rows = [",".join(f"{cols[c][i]:.9f}" for c in cols) for i in range(n)]
    path.write_text("\n".join([header, *rows]), encoding="latin-1")
    return path


def _s_csv(path, *, n=600, t0=43_200.0, fix_every_s=9.0, dt=DT, lat0=52.4, lon0=-1.5):
    """A synthetic `S-` file whose GPS holds its last position between fixes.

    The satellite count ticks on every row while the position does not, which is exactly the shape
    that made the old fix counting deduplicate to 3.5x too many "fixes".
    """
    lat = lat0 + np.arange(n) * (16.0 * dt) / 111_320.0
    stride = max(1, int(round(fix_every_s / dt)))
    header = [
        "GPS LATITUDE (degrees)", " GPS LONGITUDE (degrees)", "GPS SATELLITES IN RANGE",
        " TIME SINCE START (ms)", " DATE (YYYY-MO-DD HH-MI-SS_SSS)",
        " ACCELEROMETER X (m/s\xb2)", " ACCELEROMETER Y (m/s\xb2)", " ACCELEROMETER Z (m/s\xb2)",
        " GYROSCOPE Yaw (rad/s)", " GYROSCOPE Pitch (rad/s)", " GYROSCOPE Roll (rad/s)",
    ]
    lines = [",".join(header)]
    for i in range(n):
        held = (i // stride) * stride
        ms_of_day = int(round((t0 + i * dt) * 1000))
        hh, rem = divmod(ms_of_day, 3_600_000)
        mm, rem = divmod(rem, 60_000)
        ss, ms = divmod(rem, 1000)
        stamp = f"2019-03-14 {hh % 24:02d}-{mm:02d}-{ss:02d}_{ms:03d}"
        lines.append(
            f"{lat[held]:.9f},{lon0:.9f},{7 + i % 3},{i * dt * 1000:.1f},{stamp},"
            "0.0,0.0,9.81,0.0,0.0,0.0"
        )
    path.write_text("\n".join(lines), encoding="latin-1")
    return path


def _manifest_rows(*, stream, suffix=None, contains=None):
    """Rows from the committed manifest -- the same file the loaders resolve paths through."""
    with open(DEFAULT_MANIFEST, encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["stream"] == stream]
    if suffix:
        rows = [r for r in rows if r["path"].lower().endswith(suffix)]
    if contains:
        rows = [r for r in rows if contains in r["path"]]
    return [r for r in rows if "Synchronised V abd S datasets" in r["path"]]


def _track(n=600, t0=0.0, dt=DT, lat0=52.4, lon0=-1.5):
    t = t0 + np.arange(n) * dt
    lat = lat0 + np.arange(n) * (16.0 * dt) / 111_320.0
    return TruthTrack(name="synthetic", t_s=t, lat=lat, lon=np.full(n, lon0), source="memory")


# --------------------------------------------------------------------------------------------
# The guard: this module reads three columns and no others
# --------------------------------------------------------------------------------------------


def test_the_truth_allowlist_is_position_and_time_only():
    """Not a style point. A velocity column here becomes a speed label the first time someone is
    short of one, and the speed head is the part of this system whose honesty matters most."""
    assert TRUTH_COLUMNS == {"gps_lat", "gps_lon", "time_of_day_s"}


@pytest.mark.parametrize("column", SHIPPED_V_BANNED)
def test_wheel_channels_are_rejected_by_the_truth_guard(column):
    with pytest.raises(LeakageError):
        assert_truth_only([column])


@pytest.mark.parametrize(
    "column",
    [" GPS Velocity (Kmh)", " GPS Heading (degrees)", " GPS Height (km)", " Yaw Rate (deg/s)"],
)
def test_other_v_gps_channels_are_rejected_even_though_they_are_not_wheel_speed(column):
    """`EVALUATION.md` section 1.2 permits the `V-` GPS as *ground truth*. Truth is a position at
    a time; a velocity is a label, and this module is not a door to one."""
    with pytest.raises(LeakageError):
        assert_truth_only([column])


def test_longitudinal_accel_is_not_mistaken_for_longitude():
    """The `V-` stream carries 'Indicated Longitudinal Acceleration'. A loose longitude alias
    would swallow it, and the failure would look like a plausible trajectory."""
    assert normalise_truth_header(" Indicated Longitudinal Acceleration (g)") != "gps_lon"
    with pytest.raises(LeakageError):
        assert_truth_only([" Indicated Longitudinal Acceleration (g)"])


@pytest.mark.parametrize(
    "spelling", ["GPS Latitude (degrees)", "Latitude (deg)", " GPS Lat (deg)", "LATITUDE"]
)
def test_plausible_latitude_spellings_all_normalise(spelling):
    """The exact `V-` header spelling is not recorded anywhere in this repo. The aliases cover the
    plausible forms and `load_truth` fails loudly listing the headers it saw if none matches --
    see the test below. It does not guess."""
    assert normalise_truth_header(spelling) == "gps_lat"


def test_truth_columns_are_not_model_features():
    """The `S-` guard must still reject them: truth is not an input, and a tensor built from it
    would carry information the system does not have inside a tunnel."""
    with pytest.raises(LeakageError):
        assert_feature_safe(["gps_lat", "gps_lon"])


def test_the_truth_track_has_no_feature_path():
    """`TruthTrack` is deliberately not a `Sequence`. There is no call that hands it to a filter,
    which is the property that makes reading the banned stream for truth defensible."""
    track = _track()
    assert not hasattr(track, "features")
    assert set(vars(track)) == {"name", "t_s", "lat", "lon", "source"}


# --------------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------------


def test_load_truth_reads_position_and_time_past_the_banned_columns(tmp_path):
    track = load_truth(_v_csv(tmp_path / "V-x.csv"), "x")
    assert track.n_fixes == 600
    assert track.median_dt_s == pytest.approx(0.1, abs=1e-6)
    assert track.duration_s == pytest.approx(59.9, abs=1e-6)


def test_load_truth_names_the_headers_it_saw_when_a_spelling_is_unknown(tmp_path):
    """The failure a new folder layout produces must say what to add, not just that it failed."""
    p = tmp_path / "V-y.csv"
    p.write_text("Some Odd Position Column,Another\n1.0,2.0\n", encoding="latin-1")
    with pytest.raises(TruthPairingError, match="Headers seen"):
        load_truth(p, "y")


def test_a_truth_track_refuses_non_monotonic_time():
    """Five `S-` stems restart their clock mid-file. If a `V-` one does too, the file is two
    recordings and must fail rather than be sorted into a plausible single track."""
    with pytest.raises(ValueError, match="strictly increasing"):
        TruthTrack(
            name="broken",
            t_s=np.array([0.0, 1.0, 0.5]),
            lat=np.zeros(3),
            lon=np.zeros(3),
            source="memory",
        )


def test_time_of_day_unwraps_across_midnight():
    """IO-VNBD includes night driving. Without this a sequence crossing midnight reads as an
    86,400 s jump backwards and looks like a corrupt file."""
    t = unwrap_time_of_day(np.array([86_399.0, 86_399.5, 0.0, 0.5]))
    assert np.all(np.diff(t) > 0)
    assert t[-1] == pytest.approx(86_400.5)


def test_seconds_of_day_parses_the_shipped_date_format():
    parsed = seconds_of_day(["2019-03-14 15-22-31_500"])[0]
    assert parsed == pytest.approx(15 * 3600 + 22 * 60 + 31.5)


def test_seconds_of_day_refuses_a_column_it_cannot_parse():
    with pytest.raises(ValueError, match="time of day"):
        seconds_of_day(["not a date", "nor this"])


# --------------------------------------------------------------------------------------------
# Epoch lookup: nearest sample, never interpolation
# --------------------------------------------------------------------------------------------


def test_epoch_lookup_takes_the_nearest_sample(tmp_path):
    track = _track()
    idx = track.index_at(np.array([0.0, 1.0, 2.0, 10.0]))
    assert list(idx) == [0, 10, 20, 100]


def test_epoch_lookup_refuses_a_gap_rather_than_interpolating_across_it():
    """The whole reason truth moved off the `S-` stream. A lookup that quietly interpolated would
    reintroduce exactly the invented position this change exists to avoid -- and it would look
    entirely plausible on a plot."""
    sparse = TruthTrack(
        name="sparse",
        t_s=np.array([0.0, 9.0, 18.0]),
        lat=np.array([52.4, 52.41, 52.42]),
        lon=np.full(3, -1.5),
        source="memory",
    )
    with pytest.raises(TruthPairingError, match="no truth sample within"):
        sparse.index_at(np.arange(0.0, 10.0))


def test_the_epoch_tolerance_is_half_a_sample_period():
    assert MAX_EPOCH_OFFSET_S == pytest.approx(0.5 / TRUTH_RATE_HZ)


def test_displacements_are_per_epoch_not_absolute():
    """`per_epoch_errors` compares displacements, so a constant offset between two trajectories
    must not masquerade as a per-epoch error."""
    track = _track()
    d = track.displacements_ned(np.arange(0.0, 11.0))
    assert d.shape == (10, 2)
    assert np.allclose(d[:, 0], 16.0, atol=0.1)  # 16 m/s north, 1 s epochs
    assert np.allclose(d[:, 1], 0.0, atol=1e-6)


def test_distance_is_path_length_not_endpoint_separation():
    track = _track()
    assert track.distance_m(0.0, 10.0) == pytest.approx(160.0, rel=1e-3)


# --------------------------------------------------------------------------------------------
# Pairing through the manifest
# --------------------------------------------------------------------------------------------


def test_pairing_is_case_insensitive_where_the_dataset_is_not(tmp_path):
    """`V-vta9.csv` in the synchronised folder, `V-Vta9.csv` in the unsynchronised one. A
    `V-{stem}.csv` glob works on the Windows dev box and finds nothing on CI's Ubuntu."""
    for row in _manifest_rows(stream="V-", contains="Vta09"):
        target = tmp_path / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    found = paired_truth_path("Vta9", tmp_path)
    assert found.name.lower() == "v-vta9.csv"
    assert "Synchronised" in str(found)

def test_pairing_prefers_the_categorised_copy(tmp_path):
    """"""
    for row in _manifest_rows(stream="V-", suffix="v-s3a.csv"):
        target = tmp_path / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    assert "Uncategorised" not in str(paired_truth_path("S3a", tmp_path))

def test_pairing_refuses_a_stem_with_no_synchronised_vehicle_file(tmp_path):
    """Eleven stems ship on one stream only (D-044). A stem with no paired truth must be dropped
    from the protocol loudly, not graded against 9 s fixes."""
    with pytest.raises(TruthPairingError, match="no synchronised"):
        paired_truth_path("NotAStem", tmp_path)


def test_manifest_lookup_serves_both_streams(tmp_path):
    """The cadence tool resolves `S-` files the same way, so the case and folder handling is
    written once rather than twice."""
    for row in _manifest_rows(stream="S-", suffix="s-s3a.csv"):
        target = tmp_path / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    found = manifest_path_for("S3a", "S-", tmp_path, strict_checksum=False)
    assert found.name.lower() == "s-s3a.csv"
    assert "Uncategorised" not in str(found)


def test_a_stem_whose_two_copies_differ_is_refused_under_a_strict_checksum(tmp_path):
    """The `V-` copies are byte-identical today, so truth pairing keeps the check on and a future
    divergence there is an alarm rather than a silent change of ground truth."""
    for row in _manifest_rows(stream="S-", suffix="s-s3a.csv"):
        target = tmp_path / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    with pytest.raises(TruthPairingError, match="different checksums"):
        manifest_path_for("S3a", "S-", tmp_path)


def test_every_smartphone_stem_ships_as_two_different_files_and_no_vehicle_stem_does():
    """A finding, pinned so it cannot quietly change.

    All 72 `S-` stems in the synchronised folder ship as two files under different checksums; no
    `V-` stem does. Fifty-seven of the seventy-two differ substantively, the uncategorised copy
    larger every time by up to 8.9% -- that is rows, not line endings, so the two copies are
    different lengths of recording and sequence duration, outage tiling, fix count and every
    metric move with the choice between them. The other fifteen differ by 5 or 6 bytes, which is
    a trailing-newline difference and harmless.

    `load_split` globs and takes the first match, so today that choice is made by filesystem
    ordering -- a direct threat to Gate 0's "reproduces to the digit across two machines"."""
    divergence = divergent_copies()
    assert {d.stream for d in divergence} == {"S-"}
    assert len(divergence) == 72

    substantive = [d for d in divergence if abs(d.delta_bytes) >= 100]
    assert len(substantive) == 57
    assert all(d.delta_bytes > 0 for d in substantive)
    assert max(d.delta_bytes / d.categorised_bytes for d in substantive) == pytest.approx(
        0.089, abs=0.001
    )
    assert {d.delta_bytes for d in divergence if abs(d.delta_bytes) < 100} == {-5, -6}


# --------------------------------------------------------------------------------------------
# Alignment -- the measurement that decides whether any of this is usable
# --------------------------------------------------------------------------------------------


def test_a_synchronised_pair_agrees_to_within_gps_noise(tmp_path):
    seq = load_sequence(_s_csv(tmp_path / "S-a.csv"), "a")
    truth = load_truth(_v_csv(tmp_path / "V-a.csv"), "a")
    report = align_to_sequence(seq, truth)
    assert report.n_matched >= 6
    assert report.residual_median_m < 1.0
    assert report.is_usable


def test_a_one_second_misalignment_fails_the_usability_check(tmp_path):
    """The check has to be sharp enough to catch the failure it exists for. At 16 m/s one second
    of misalignment is ~16 m, well past two receivers each quoted at +/-3 m."""
    seq = load_sequence(_s_csv(tmp_path / "S-b.csv"), "b")
    truth = load_truth(_v_csv(tmp_path / "V-b.csv", t0=43_200.0 + 1.0), "b")
    report = align_to_sequence(seq, truth)
    assert report.residual_median_m > 10.0
    assert not report.is_usable


def test_a_constant_lag_is_reported_rather_than_removed(tmp_path):
    """A pair that agrees only after a time shift is a finding about the dataset. Applying the
    shift would make every pair align by construction and the check would assert nothing."""
    seq = load_sequence(_s_csv(tmp_path / "S-c.csv"), "c")
    truth = load_truth(_v_csv(tmp_path / "V-c.csv", t0=43_200.0 - 2.0), "c")
    report = align_to_sequence(seq, truth)
    assert report.best_lag_s == pytest.approx(-2.0, abs=0.15)
    assert report.residual_at_best_lag_m < 1.0
    assert report.residual_median_m > 10.0
    assert not report.is_usable


def test_a_reported_lag_is_a_clean_multiple_of_the_search_step(tmp_path):
    """`np.arange` accumulates float error, and a lag of -1.8e-14 in a committed artefact reads
    as a measurement rather than as zero."""
    seq = load_sequence(_s_csv(tmp_path / "S-i.csv"), "i")
    truth = load_truth(_v_csv(tmp_path / "V-i.csv"), "i")
    lag = align_to_sequence(seq, truth).best_lag_s
    assert lag == 0.0
    assert lag == round(lag, 3)


def test_alignment_needs_fix_timestamps(tmp_path):
    class _Undated:
        gnss = __import__("pandas").DataFrame({"gps_lat": [52.4], "gps_lon": [-1.5]})

    with pytest.raises(TruthPairingError, match="cannot be placed on the clock"):
        align_to_sequence(_Undated(), _track())


# --------------------------------------------------------------------------------------------
# Cadence: what the `S-` GPS actually does
# --------------------------------------------------------------------------------------------


def test_a_nine_second_stream_does_not_meet_the_protocols_1hz_claim(tmp_path):
    """`EVALUATION.md` section 2 was drafted as '1 Hz GNSS' from a paper written against the
    vehicle stream. Measured over all 72 `S-` stems, the median gap is 9 s."""
    row = measure_cadence(load_sequence(_s_csv(tmp_path / "S-d.csv"), "d"))
    assert row.median_gap_s == pytest.approx(9.0, abs=0.2)
    assert not row.meets_1hz


def test_a_genuine_1hz_stream_is_recognised(tmp_path):
    """Three stems -- Vta1a, Vta2, Vta1b -- really do update at 1 Hz, so the measurement must
    distinguish them rather than condemning the stream wholesale."""
    row = measure_cadence(load_sequence(_s_csv(tmp_path / "S-e.csv", fix_every_s=1.0), "e"))
    assert row.median_gap_s == pytest.approx(1.0, abs=0.05)
    assert row.meets_1hz


def test_a_fix_is_a_position_change_not_a_distinct_row(tmp_path):
    """Deduplicating across every GNSS column counted a row whose lat/lon repeated but whose
    sats-in-range had ticked. That inflated S3a's fix count 3.5x -- and the fix count is what the
    update rate, the re-acquisition study and the GNSS-available baseline are read off."""
    seq = load_sequence(_s_csv(tmp_path / "S-f.csv", n=600, fix_every_s=9.0), "f")
    assert len(seq.gnss) == pytest.approx(600 / 90, abs=1)
    assert len(seq.gnss["gps_lat"].round(9).unique()) == len(seq.gnss)


def test_every_fix_carries_its_timestamp_and_sample_index(tmp_path):
    """Fixes are not evenly spaced -- 9 s median, 109 s worst gap on a held-out stem -- so a fix
    index says nothing about when the fix happened."""
    seq = load_sequence(_s_csv(tmp_path / "S-g.csv"), "g")
    assert {"time_since_start_ms", "date", "sample_idx"} <= set(seq.gnss.columns)
    assert np.all(np.diff(seq.fix_times_s()) > 0)


def test_the_summary_carries_the_numbers_the_protocol_quotes():
    """The DECISION_LOG row and EVALUATION.md section 2 quote these, so they come out of the
    artefact rather than being retyped out of a terminal."""
    reports = [
        AlignmentReport("a", 10, 10, 2.0, 3.0, 4.0, 0.0, 2.0, True, 0.1),
        AlignmentReport("b", 10, 10, 30.0, 40.0, 50.0, 0.0, 30.0, True, 0.1),
    ]
    out = summarise([], reports)
    assert out["n_alignment_usable"] == 1
    assert out["truth_residual_worst_median_m"] == pytest.approx(30.0)


# --------------------------------------------------------------------------------------------
# The path that used to exist
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["ground_truth_ned", "distance_m"])
def test_the_smartphone_truth_helpers_now_refuse_and_say_where_to_go(tmp_path, method):
    """They had no caller and no test when the cadence was measured, which is the shape of a
    trap: the next person to wire the harness would have reached for the obvious method and
    computed a graded number against fixes 9 s apart, and nothing would have failed."""
    seq = load_sequence(_s_csv(tmp_path / "S-h.csv"), "h")
    with pytest.raises(NotImplementedError, match="eval.loaders.truth"):
        getattr(seq, method)()


def test_load_split_picks_between_divergent_copies_deterministically(tmp_path):
    """`candidates[0]` off a glob made the choice by filesystem ordering, and the two copies are
    materially different files -- so two machines on the same commit could evaluate different
    data. Gate 0's criterion is 'reproduces to the digit across two machines'."""
    from eval.loaders.io_vnbd import _preferred_copy

    cat = tmp_path / "Categorised IOVNB Dataset" / "S3a" / "S-S3a.csv"
    unc = tmp_path / "Uncategorised IOVNB Dataset" / "S-Dataset" / "S-S3a.csv"
    assert _preferred_copy([unc, cat]) == cat
    assert _preferred_copy([cat, unc]) == cat
