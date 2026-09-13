"""The logger's raw inertial sidecar, read back through `eval.loaders.android_raw`.

Seat A writes `<session-id>_raw_imu.csv` (`Records.RAW_IMU_HEADER`); `eval/allan.py` reads it for
the Allan run on our own hardware (android/HANDOVER.md section 9 item 7). The header is parsed
out of the Kotlin source rather than restated, so a change to the app's writer fails here before
it fails on a laptop after a drive. The rest pins the two decisions the loader makes on purpose:
pair on the sensor's own stamp and never interpolate; gate stationarity on the bias-compensated
gyro but hand the Allan estimator the raw one.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from eval import allan
from eval.loaders.android_raw import (
    ACCEL_BIAS_AXES,
    ACCEL_STREAM,
    GYRO_BIAS_AXES,
    GYRO_STREAM,
    RAW_IMU_HEADER,
    DeviceImuSequence,
    is_raw_imu_sidecar,
    load_raw_imu_sidecar,
)
from eval.loaders.io_vnbd import SAMPLE_RATE_HZ

_RECORDS_KT = (
    Path(__file__).resolve().parents[1]
    / "android" / "app" / "src" / "main" / "kotlin" / "org" / "idr26168" / "logger" / "Records.kt"
)

RATE_HZ = 125.0
DT_NS = int(round(1e9 / RATE_HZ))
G = 9.80665


# --------------------------------------------------------------------------------------------
# Fixtures: a sidecar written the way `Records.formatRawSample` writes one
# --------------------------------------------------------------------------------------------


def _rows(
    n: int,
    *,
    seed: int = 7,
    gyro_bias: tuple[float, float, float] = (0.005, 0.003, 0.0),
    gyro_sigma: float = 1e-4,
    accel_sigma: float = 0.01,
    accel_six_values: bool = True,
    bias_step_at: int | None = None,
) -> list[str]:
    """Interleaved magnetometer / gyroscope / accelerometer lines at 125 Hz, shared stamps."""
    rng = np.random.default_rng(seed)
    t0 = 287_217_245_046_953
    lines = []
    for i in range(n):
        ts = t0 + i * DT_NS
        arrival = ts + 3_500_000
        bias = np.array(gyro_bias)
        if bias_step_at is not None and i >= bias_step_at:
            bias = bias + np.array([0.000611, 0.0, 0.0])  # one LSB, like the LSM6DSV
        g = rng.normal(0.0, gyro_sigma, 3) + bias
        a = rng.normal(0.0, accel_sigma, 3) + np.array([0.0, 0.0, G])
        lines.append(f"magnetic_field_uncalibrated,{ts},{arrival},3,8.1,-8.4,-161.2,6.9,23.4,-125.2")
        lines.append(
            f"{GYRO_STREAM},{ts},{arrival},3,{g[0]:.6f},{g[1]:.6f},{g[2]:.6f},"
            f"{bias[0]:.6f},{bias[1]:.6f},{bias[2]:.6f}"
        )
        tail = ",0.000000,0.000000,0.000000" if accel_six_values else ",,,"
        lines.append(f"{ACCEL_STREAM},{ts},{arrival},3,{a[0]:.6f},{a[1]:.6f},{a[2]:.6f}{tail}")
    return lines


def _write(tmp_path: Path, lines: list[str], name: str = "S-IDR-20260913-141119-x_raw_imu.csv"):
    p = tmp_path / name
    p.write_text(",".join(RAW_IMU_HEADER) + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return p


# --------------------------------------------------------------------------------------------
# The contract with the app
# --------------------------------------------------------------------------------------------


def test_the_header_constant_is_the_one_records_kt_writes():
    text = _RECORDS_KT.read_text(encoding="utf-8")
    m = re.search(r'val RAW_IMU_HEADER\s*=\s*"([^"]+)"', text)
    assert m, "Records.kt no longer declares RAW_IMU_HEADER as a string literal"
    assert tuple(m.group(1).split(",")) == RAW_IMU_HEADER


def test_the_stream_keys_are_the_ones_sensorhub_registers():
    hub = _RECORDS_KT.with_name("SensorHub.kt").read_text(encoding="utf-8")
    assert f'"{ACCEL_STREAM}" to Sensor.TYPE_ACCELEROMETER_UNCALIBRATED' in hub
    assert f'"{GYRO_STREAM}" to Sensor.TYPE_GYROSCOPE_UNCALIBRATED' in hub


def test_detection_reads_the_header_not_the_name(tmp_path):
    sidecar = _write(tmp_path, _rows(4), name="anything.csv")
    main_csv = tmp_path / "S-IDR-x.csv"
    main_csv.write_text(
        "Time since start (ms),ACCELEROMETER X (m/s^2),GYROSCOPE X (rad/s)\n0,0,0\n",
        encoding="utf-8",
    )
    assert is_raw_imu_sidecar(sidecar) is True
    assert is_raw_imu_sidecar(main_csv) is False


def test_a_foreign_header_is_refused_by_name(tmp_path):
    p = tmp_path / "S-IDR-x_raw_imu.csv"
    p.write_text("stream,event_ns,v0,v1,v2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a raw IMU sidecar"):
        load_raw_imu_sidecar(p)


def test_a_sidecar_without_a_gyroscope_is_refused(tmp_path):
    lines = [ln for ln in _rows(50) if not ln.startswith(GYRO_STREAM)]
    with pytest.raises(ValueError, match=GYRO_STREAM):
        load_raw_imu_sidecar(_write(tmp_path, lines))


# --------------------------------------------------------------------------------------------
# What the loader does on purpose
# --------------------------------------------------------------------------------------------


def test_pairs_on_the_shared_stamp_and_reports_the_rate(tmp_path):
    seq = load_raw_imu_sidecar(_write(tmp_path, _rows(500)))

    assert isinstance(seq, DeviceImuSequence)
    assert seq.name == "S-IDR-20260913-141119-x"
    assert seq.split == "device"
    assert seq.n_samples == 500
    assert seq.n_unpaired == 0
    assert seq.sample_rate_hz == pytest.approx(RATE_HZ, rel=1e-6)
    assert seq.duration_s == pytest.approx(499 / RATE_HZ, rel=1e-6)
    assert seq.gnss.empty
    t = seq.imu["time_since_start_ms"].to_numpy()
    assert t[0] == 0.0
    assert np.allclose(np.diff(t), 1000.0 / RATE_HZ)
    # the magnetometer rows are in the file and nowhere in the frame
    assert not any("magnetic" in c for c in seq.imu.columns)


def test_unpaired_rows_are_dropped_and_counted_never_interpolated(tmp_path):
    lines = _rows(300)
    # three gyro samples with stamps no accelerometer sample shares, and one accelerometer stamp
    # repeated (a HAL re-delivery), which must collapse to one row
    lines.append(f"{GYRO_STREAM},999999999999999,999999999999999,3,0,0,0,0,0,0")
    lines.append(f"{GYRO_STREAM},999999999999998,999999999999998,3,0,0,0,0,0,0")
    lines.append(f"{GYRO_STREAM},999999999999997,999999999999997,3,0,0,0,0,0,0")
    dup = next(ln for ln in lines if ln.startswith(ACCEL_STREAM))
    lines.append(dup)

    seq = load_raw_imu_sidecar(_write(tmp_path, lines))

    assert seq.n_samples == 300
    assert seq.n_unpaired == 3
    assert seq.imu["event_ns"].is_monotonic_increasing
    assert seq.imu["event_ns"].is_unique


def test_the_raw_measurement_stays_raw_and_the_estimate_sits_beside_it(tmp_path):
    bias = (0.005, 0.003, 0.0)
    seq = load_raw_imu_sidecar(_write(tmp_path, _rows(2_000, gyro_bias=bias)))

    raw_mean = seq.imu[list(allan.GYRO_AXES)].mean().to_numpy()
    assert raw_mean == pytest.approx(bias, abs=2e-5)
    assert (seq.imu[list(GYRO_BIAS_AXES)].to_numpy() == np.array(bias)).all()
    assert (seq.imu[list(ACCEL_BIAS_AXES)].to_numpy() == 0.0).all()
    assert seq.n_gyro_bias_updates == 0


def test_a_stepping_os_estimate_is_counted(tmp_path):
    seq = load_raw_imu_sidecar(_write(tmp_path, _rows(400, bias_step_at=200)))
    assert seq.n_gyro_bias_updates == 1


def test_an_absent_estimate_is_a_zero_estimate(tmp_path):
    seq = load_raw_imu_sidecar(_write(tmp_path, _rows(50, accel_six_values=False)))
    assert (seq.imu[list(ACCEL_BIAS_AXES)].to_numpy() == 0.0).all()
    assert np.isfinite(seq.imu[list(allan.ACCEL_AXES)].to_numpy()).all()


# --------------------------------------------------------------------------------------------
# What the Allan module does with it
# --------------------------------------------------------------------------------------------


def test_imu_arrays_hands_the_gate_the_compensated_gyro_and_the_curve_the_raw_one(tmp_path):
    bias = (0.005, 0.003, 0.0)
    seq = load_raw_imu_sidecar(_write(tmp_path, _rows(2_000, gyro_bias=bias)))

    t_raw, a_raw, g_raw = allan.imu_arrays(seq)
    t_comp, a_comp, g_comp = allan.imu_arrays(seq, bias_compensated=True)

    assert g_raw.shape == g_comp.shape and t_raw.shape == t_comp.shape
    assert np.array_equal(t_raw, t_comp) and np.array_equal(a_raw, a_comp)
    assert g_raw.mean(axis=0) == pytest.approx(bias, abs=2e-5)
    assert g_comp.mean(axis=0) == pytest.approx((0.0, 0.0, 0.0), abs=2e-5)


def test_a_still_phone_with_a_static_bias_is_stationary_and_quiet(tmp_path):
    """0.0058 rad/s of static bias is above the quiet margin on its own (0.001 rad/s). It is not
    motion, and the detector must not read it as such -- while the raw stream keeps it."""
    n = int(130 * RATE_HZ)
    seq = load_raw_imu_sidecar(_write(tmp_path, _rows(n, gyro_bias=(0.005, 0.003, 0.0))))

    found = allan.find_stationary_segments(seq, min_duration_s=120.0)

    assert len(found) == 1
    assert found[0].is_quiet is True
    assert found[0].dt_s == pytest.approx(1.0 / RATE_HZ, rel=1e-6)
    assert found[0].duration_s == pytest.approx((n - 1) / RATE_HZ, abs=0.05)


def test_without_the_estimate_the_same_bias_reads_as_motion(tmp_path):
    """The compensation is the estimate's doing, not a hidden demean: strip the bias columns and
    the same rows fail the quiet margin, as a calibrated stream carrying 0.0058 rad/s would."""
    n = int(130 * RATE_HZ)
    seq = load_raw_imu_sidecar(_write(tmp_path, _rows(n, gyro_bias=(0.005, 0.003, 0.0))))
    stripped = DeviceImuSequence(
        name=seq.name,
        imu=seq.imu.drop(columns=list(GYRO_BIAS_AXES)),
        gnss=seq.gnss,
        split=seq.split,
        sample_rate_hz=seq.sample_rate_hz,
        source_path=seq.source_path,
        n_unpaired=0,
        n_gyro_bias_updates=0,
    )

    found = allan.find_stationary_segments(stripped, min_duration_s=120.0)

    assert found and found[0].is_quiet is False


def test_the_window_is_ten_seconds_at_the_sidecars_rate_not_at_ten_hertz(tmp_path):
    """A 10 s window sized for 10 Hz is 100 samples -- 0.8 s at 125 Hz. Size it by the sidecar's
    rate: a 130 s quiet record with one 0.5 s twitch in the middle splits into two halves too
    short to keep, which only happens if the twitch spans a whole window at 125 Hz."""
    n = int(130 * RATE_HZ)
    lines = _rows(n)
    mid = n // 2
    rng = np.random.default_rng(3)
    for i in range(mid, mid + int(0.5 * RATE_HZ)):
        g = rng.normal(0.0, 0.5, 3)
        lines[3 * i + 1] = (
            f"{GYRO_STREAM},{lines[3 * i + 1].split(',')[1]},0,3,"
            f"{g[0]:.6f},{g[1]:.6f},{g[2]:.6f},0.005000,0.003000,0.000000"
        )
    seq = load_raw_imu_sidecar(_write(tmp_path, lines))

    assert allan.sample_rate_hz(seq) == pytest.approx(RATE_HZ, rel=1e-6)
    assert allan.find_stationary_segments(seq, min_duration_s=120.0) == []


def test_an_iovnbd_sequence_still_windows_at_the_protocol_rate():
    """No `sample_rate_hz` attribute means 10 Hz, exactly as before this loader existed."""
    imu = pd.DataFrame(
        {
            **{a: np.zeros(4) for a in allan.ACCEL_AXES},
            **{g: np.zeros(4) for g in allan.GYRO_AXES},
            "time_since_start_ms": np.arange(4) * 100.0,
        }
    )
    from eval.loaders.io_vnbd import Sequence

    seq = Sequence(name="S-x", imu=imu, gnss=pd.DataFrame(), split="train")
    assert allan.sample_rate_hz(seq) == SAMPLE_RATE_HZ


# --------------------------------------------------------------------------------------------
# The command line
# --------------------------------------------------------------------------------------------


def test_a_sidecar_may_not_write_into_the_iovnbd_artefact_directory(tmp_path):
    sidecar = _write(tmp_path, _rows(50))
    with pytest.raises(SystemExit) as exc:
        allan.main([str(sidecar)])
    assert exc.value.code == 2


def test_a_quiet_sidecar_runs_end_to_end_into_its_own_directory(tmp_path, capsys):
    n = int(130 * RATE_HZ)
    sidecar = _write(tmp_path, _rows(n))
    out = tmp_path / "device"

    rc = allan.main([str(sidecar), "--out-dir", str(out)])

    assert rc == 0
    printed = capsys.readouterr().out
    assert "raw sidecar" in printed and "125.00 Hz" in printed
    for name in ("allan_segments.csv", "allan_curve.csv", "allan_coefficients.csv",
                 "allan_summary.json", "allan_stamp.json"):
        assert (out / name).is_file(), name
    coefficients = pd.read_csv(out / "allan_coefficients.csv", comment="#")
    # the curve saw the raw stream at 125 Hz: taus start at one sample, not at 0.1 s
    curve = pd.read_csv(out / "allan_curve.csv", comment="#")
    assert curve["tau_s"].min() == pytest.approx(1.0 / RATE_HZ, rel=1e-6)
    # white synthetic noise reads back as white on every axis
    assert coefficients["random_walk_is_white"].all()
