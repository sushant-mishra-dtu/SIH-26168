"""IO-VNBD "S-" smartphone-stream loader.

Every read passes through the leakage guard in columns.py. There is no unguarded path to the data
by design -- if you find yourself wanting one, that is the signal to stop.

Dataset background: docs/DATASETS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from eval.loaders.columns import (
    FEATURE_COLUMNS,
    GNSS_CHANNELS,
    LeakageError,
    assert_no_leakage,
    normalise,
)
from eval.splits import split_of
from idr.geo import geodetic_to_ned, path_length

SAMPLE_RATE_HZ = 10
GNSS_RATE_HZ = 1


@dataclass(frozen=True)
class Sequence:
    """One loaded IO-VNBD sequence, guarded and canonicalised.

    ``imu`` holds the inertial channels at 10 Hz. ``gnss`` holds the 1 Hz reference fixes.
    They are kept separate rather than merged so that nothing downstream can accidentally treat a
    forward-filled GNSS column as a per-sample input.
    """

    name: str
    imu: pd.DataFrame
    gnss: pd.DataFrame
    split: str

    @property
    def n_samples(self) -> int:
        return len(self.imu)

    @property
    def duration_s(self) -> float:
        return self.n_samples / SAMPLE_RATE_HZ

    def features(self) -> np.ndarray:
        """Inertial feature matrix, shape (n, 15). Guarded on the way out."""
        cols = [c for c in self.imu.columns if c in FEATURE_COLUMNS]
        from eval.loaders.columns import assert_feature_safe

        assert_feature_safe(cols)
        return self.imu[sorted(cols)].to_numpy(dtype=float)

    def ground_truth_ned(self) -> np.ndarray:
        """GNSS reference track as local NED offsets, shape (n_fixes, 2)."""
        lat = self.gnss["gps_lat"].to_numpy(dtype=float)
        lon = self.gnss["gps_lon"].to_numpy(dtype=float)
        return geodetic_to_ned(lat, lon, lat[0], lon[0])

    def distance_m(self, start_fix: int = 0, end_fix: int | None = None) -> float:
        """Vincenty ground-truth path length over a fix range, in metres."""
        lat = self.gnss["gps_lat"].to_numpy(dtype=float)[start_fix:end_fix]
        lon = self.gnss["gps_lon"].to_numpy(dtype=float)[start_fix:end_fix]
        return path_length(lat, lon)


def _canonicalise(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise headers, then guard. Guard *after* normalisation so that a disguised wheel-speed
    column ('Wheel Speed FL (rad/s)') is caught by the same pattern as a bare one."""
    renamed = {c: normalise(c) for c in df.columns}
    assert_no_leakage(df.columns, context="raw CSV read")
    return df.rename(columns=renamed)


def load_sequence(path: str | Path, name: str | None = None) -> Sequence:
    """Load one sequence CSV.

    Raises LeakageError if the file contains any disallowed channel -- including if someone points
    this at a "V-" file by mistake, which is exactly the accident worth failing loudly on.
    """
    p = Path(path)
    seq_name = name or p.stem

    if seq_name.upper().startswith("V-") or seq_name.upper().startswith("V_"):
        raise LeakageError(
            f"{seq_name!r} names a 'V-' ECU/CAN sequence. That stream contains wheel speed and is "
            "disallowed by PS 26168. Load the paired 'S-' sequence instead."
        )

    # latin-1, not utf-8: the shipped headers carry raw 0xB0/0xB5 bytes ("(deg)", "(uT)") that
    # are not valid UTF-8, so the default encoding raises before the guard ever runs. latin-1
    # never fails, and the bytes it mis-renders live only inside parentheses that normalise()
    # strips anyway.
    raw = pd.read_csv(p, encoding="latin-1", low_memory=False)
    df = _canonicalise(raw)

    imu_cols = sorted(c for c in df.columns if c in FEATURE_COLUMNS)
    gnss_cols = sorted(c for c in df.columns if c in GNSS_CHANNELS)
    if not imu_cols:
        raise ValueError(
            f"{p} contains no inertial channels after normalisation: {list(df.columns)}"
        )
    if not gnss_cols:
        raise ValueError(f"{p} contains no GNSS reference channels; cannot compute ground truth")

    time_col = "time_since_start_ms"
    imu = df[imu_cols + ([time_col] if time_col in df.columns else [])].copy()

    # GNSS arrives at 1 Hz inside a 10 Hz file: rows repeat or are blank between fixes. Take the
    # distinct fixes only. Never forward-fill -- an interpolated "measurement" fed back as truth
    # is circular.
    gnss = df[gnss_cols].dropna(how="all").drop_duplicates().reset_index(drop=True)

    return Sequence(name=seq_name, imu=imu, gnss=gnss, split=split_of(seq_name))


def load_split(data_dir: str | Path, sequences: tuple[str, ...]) -> dict[str, Sequence]:
    """Load a named set of sequences from a directory. Missing files are reported together.

    Failing on the first missing file makes you rerun once per missing file; reporting them all at
    once makes it one trip to fix the manifest.
    """
    root = Path(data_dir)
    loaded: dict[str, Sequence] = {}
    missing: list[str] = []
    for name in sequences:
        candidates = list(root.glob(f"**/{name}.csv")) or list(root.glob(f"**/S-{name}.csv"))
        if not candidates:
            missing.append(name)
            continue
        loaded[name] = load_sequence(candidates[0], name=name)
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} sequence(s) not found under {root}: {missing}\n"
            "Check data/manifest/ and docs/DATASETS.md for the expected layout."
        )
    return loaded
