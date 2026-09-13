"""The logger's raw inertial sidecar, read for Allan variance on our own hardware.

`android/` writes two inertial files per session. The 10 Hz main CSV uses IO-VNBD's column
vocabulary and goes through `io_vnbd.load_sequence` unchanged (D-116). The full-rate sidecar,
`<session-id>_raw_imu.csv`, holds the *uncalibrated* accelerometer and gyroscope with the OS bias
estimate alongside every sample -- `Records.RAW_IMU_HEADER` in the app, `v0..v2` the measurement
and `v3..v5` the estimate. The harness never reads the sidecar. This module exists so that
`eval/allan.py` can (android/HANDOVER.md section 9 item 7): an Allan curve wants the sensor at
the rate the sensor runs, not a 10 Hz sample-and-hold of it.

Two things the loader does on purpose:

* **Pairs accelerometer and gyroscope on the sensor's own `event_ns`, exactly.** On the STM
  LSM6DSV both come out of one FIFO with identical stamps, so the inner join loses nothing; on a
  part that stamps them independently, the unpaired rows are dropped and counted, never
  interpolated -- a synthesised IMU sample inside an Allan run is indistinguishable from a real
  one (see `allan.imu_arrays`).
* **Keeps the raw measurement under the canonical axis names and the bias estimate beside it.**
  The Allan second difference annihilates a constant offset, so the raw stream is the right input
  for the curve; subtracting a vendor estimate that steps by one LSB whenever the phone is judged
  still would inject edges at precisely the taus bias instability lives at. The estimate is kept
  for the stationarity gate, where a static bias must not be mistaken for motion.

Everything here is a phone on a desk, not a graded number. D-038 seeds `Q_c` from IO-VNBD's own
stationary segments; what this reads is recorded next to those, never in place of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from eval.loaders.io_vnbd import Sequence

#: `Records.RAW_IMU_HEADER`, verbatim. `tests/test_android_raw_sidecar.py` reads the Kotlin
#: constant and fails if the two ever differ.
RAW_IMU_HEADER: tuple[str, ...] = (
    "stream", "event_ns", "arrival_ns", "accuracy", "v0", "v1", "v2", "v3", "v4", "v5",
)

#: Stream keys as `SensorHub.WANTED` registers them.
ACCEL_STREAM = "accelerometer_uncalibrated"
GYRO_STREAM = "gyroscope_uncalibrated"

#: Canonical axis names, matching `eval.loaders.columns` so that `allan.ACCEL_AXES` and
#: `allan.GYRO_AXES` read a device sequence and an IO-VNBD one with the same code. "gyro_yaw" is
#: device x, as the comment in `columns.py` explains -- it is a label, not the vertical axis.
ACCEL_AXES: tuple[str, str, str] = ("accel_x", "accel_y", "accel_z")
GYRO_AXES: tuple[str, str, str] = ("gyro_yaw", "gyro_pitch", "gyro_roll")

#: The OS bias estimate that arrived with each sample (`v3..v5`), one column per axis.
ACCEL_BIAS_AXES: tuple[str, str, str] = ("accel_x_bias", "accel_y_bias", "accel_z_bias")
GYRO_BIAS_AXES: tuple[str, str, str] = ("gyro_yaw_bias", "gyro_pitch_bias", "gyro_roll_bias")

SUFFIX = "_raw_imu.csv"


@dataclass(frozen=True)
class DeviceImuSequence(Sequence):
    """A raw sidecar, shaped like a `Sequence` so the Allan module needs no second code path.

    `imu` carries `time_since_start_ms`, `event_ns`, the six canonical axes and the six bias
    columns, one row per paired sample. `gnss` is empty: the sidecar has no fixes, and nothing
    that reads this should be looking for any.
    """

    sample_rate_hz: float
    source_path: str
    n_unpaired: int  #: rows of either stream with no partner at the same `event_ns`
    n_gyro_bias_updates: int  #: how many times the OS estimate changed over the record

    @property
    def duration_s(self) -> float:
        t = self.imu["time_since_start_ms"].to_numpy(dtype=float)
        return float(t[-1] - t[0]) / 1000.0 if t.size > 1 else 0.0


def is_raw_imu_sidecar(path: str | Path) -> bool:
    """True if the file's first line is the sidecar header. Decided from bytes, not the name."""
    with Path(path).open("r", encoding="utf-8", errors="replace") as fh:
        first = fh.readline().strip()
    return tuple(first.split(",")) == RAW_IMU_HEADER


def load_raw_imu_sidecar(path: str | Path, name: str | None = None) -> DeviceImuSequence:
    """Read one `<session-id>_raw_imu.csv` into a `DeviceImuSequence`.

    Refuses a header that is not `RAW_IMU_HEADER` -- the app's `Records.kt` is the only writer,
    and a different header means a different file, not a variant of this one.
    """
    p = Path(path)
    raw = pd.read_csv(p, encoding="utf-8", low_memory=False)
    if tuple(raw.columns) != RAW_IMU_HEADER:
        raise ValueError(
            f"{p.name}: not a raw IMU sidecar -- header is {list(raw.columns)}, "
            f"expected {list(RAW_IMU_HEADER)}"
        )

    accel = _stream(raw, ACCEL_STREAM, p)
    gyro = _stream(raw, GYRO_STREAM, p)

    paired = accel.merge(gyro, on="event_ns", how="inner", suffixes=("_a", "_g"))
    paired = paired.sort_values("event_ns", kind="stable").reset_index(drop=True)
    if len(paired) < 2:
        raise ValueError(f"{p.name}: fewer than two accelerometer/gyroscope pairs share a stamp")
    n_unpaired = (len(accel) - len(paired)) + (len(gyro) - len(paired))

    event_ns = paired["event_ns"].to_numpy(dtype=np.int64)
    dt_ns = np.diff(event_ns)
    sample_rate_hz = 1e9 / float(np.median(dt_ns))

    imu = pd.DataFrame({"time_since_start_ms": (event_ns - event_ns[0]) / 1e6})
    imu["event_ns"] = event_ns
    for i, axis in enumerate(ACCEL_AXES):
        imu[axis] = paired[f"v{i}_a"].to_numpy(dtype=float)
    for i, axis in enumerate(GYRO_AXES):
        imu[axis] = paired[f"v{i}_g"].to_numpy(dtype=float)
    # `formatRawSample` leaves `v3..v5` empty when a sensor reports three values rather than six;
    # an absent estimate is a zero estimate, and the raw columns above are untouched by it.
    for i, axis in enumerate(ACCEL_BIAS_AXES):
        imu[axis] = paired[f"v{i + 3}_a"].fillna(0.0).to_numpy(dtype=float)
    for i, axis in enumerate(GYRO_BIAS_AXES):
        imu[axis] = paired[f"v{i + 3}_g"].fillna(0.0).to_numpy(dtype=float)

    bias = imu[list(GYRO_BIAS_AXES)].to_numpy(dtype=float)
    n_bias_updates = int((np.abs(np.diff(bias, axis=0)) > 0).any(axis=1).sum())

    stem = p.name[: -len(SUFFIX)] if p.name.endswith(SUFFIX) else p.stem
    return DeviceImuSequence(
        name=name or stem,
        imu=imu,
        gnss=pd.DataFrame({"gps_lat": pd.Series(dtype=float), "gps_lon": pd.Series(dtype=float)}),
        split="device",
        sample_rate_hz=float(sample_rate_hz),
        source_path=str(p).replace("\\", "/"),
        n_unpaired=int(n_unpaired),
        n_gyro_bias_updates=n_bias_updates,
    )


def _stream(raw: pd.DataFrame, key: str, p: Path) -> pd.DataFrame:
    """One stream's rows, numeric, de-duplicated on `event_ns` (first wins), stamp-sorted."""
    rows = raw.loc[raw["stream"] == key, ["event_ns", "v0", "v1", "v2", "v3", "v4", "v5"]]
    if rows.empty:
        raise ValueError(f"{p.name}: no '{key}' rows -- the sidecar was written without it")
    rows = rows.apply(pd.to_numeric, errors="coerce")
    rows = rows[np.isfinite(rows[["event_ns", "v0", "v1", "v2"]]).all(axis=1)]
    rows["event_ns"] = rows["event_ns"].astype(np.int64)
    rows = rows.drop_duplicates("event_ns", keep="first")
    return rows.sort_values("event_ns", kind="stable")
