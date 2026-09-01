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

SAMPLE_RATE_HZ = 10

#: Measured median interval between distinct `S-` GPS fixes, in seconds, across all 72 stems in
#: the synchronised folder. **Not 1 Hz.** The protocol was drafted as "1 Hz GNSS" from the paper,
#: which is written against the `V-` stream; the smartphone GPS updates roughly every nine
#: seconds, and three stems contain no position change at all. Ground truth therefore comes from
#: the paired `V-` VBOX track (`eval/loaders/truth.py`); these fixes remain the gated filter
#: update, which is the measurement a phone actually has. Regenerate with `python -m eval.cadence`.
GNSS_MEDIAN_INTERVAL_S = 9.0


#: Why the two `S-` truth helpers refuse. They had no caller and no test when the cadence was
#: measured, which is exactly the shape of a trap: the next person to wire the harness would have
#: reached for the obvious method and computed a graded number against fixes 9 s apart, and
#: nothing would have failed. Raising costs one line at the call site and makes the mistake
#: impossible instead of merely unlikely.
_NOT_TRUTH = (
    "Sequence.{what}() reads the 'S-' smartphone GPS, which updates roughly every 9 s "
    "(median across all 72 stems; 109 s worst gap on a held-out one). CTE and CRSE sum over 1 s "
    "epochs and drift-% needs a position at the outage boundary, so neither is measurable from "
    "it.\n\nUse the paired 'V-' VBOX track instead:\n"
    "    from eval.loaders.truth import load_truth, paired_truth_path\n"
    "    truth = load_truth(paired_truth_path(name, data_root), name)\n\n"
    "EVALUATION.md section 1.2 permits the 'V-' GPS as ground truth on paired sequences. The "
    "'S-' fixes on this object stay the gated filter update, which is a different question."
)


@dataclass(frozen=True)
class Sequence:
    """One loaded IO-VNBD sequence, guarded and canonicalised.

    ``imu`` holds the inertial channels at 10 Hz. ``gnss`` holds the distinct GPS fixes -- one row
    per *position change*, at roughly 9 s intervals, each carrying the timestamp and the IMU
    sample index it occurred at. They are kept separate rather than merged so that nothing
    downstream can accidentally treat a forward-filled GNSS column as a per-sample input.

    These fixes are the **gated filter update**, not ground truth. Truth is the paired `V-` VBOX
    track -- see `eval/loaders/truth.py` and EVALUATION.md section 1.2.
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

    def fix_times_s(self) -> np.ndarray:
        """Seconds since the start of the recording at each distinct GPS fix.

        Fixes are timestamped rather than counted because they are not evenly spaced: the median
        interval is ~9 s and the largest gap on a held-out stem is 109 s, so a fix index carries
        no information about when the fix happened.
        """
        if "time_since_start_ms" not in self.gnss.columns:
            raise ValueError(
                f"{self.name}: fixes carry no timestamp, so their cadence cannot be measured and "
                "they cannot be placed against the paired 'V-' truth track."
            )
        return self.gnss["time_since_start_ms"].to_numpy(dtype=float) / 1000.0

    def ground_truth_ned(self) -> np.ndarray:
        """Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`."""
        raise NotImplementedError(_NOT_TRUTH.format(what="ground_truth_ned"))

    def distance_m(self, start_fix: int = 0, end_fix: int | None = None) -> float:
        """Refuses. The drift-% denominator is not measured off 9 s fixes."""
        raise NotImplementedError(_NOT_TRUTH.format(what="distance_m"))


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

    # GNSS arrives far more slowly than the 10 Hz rows it sits in, so rows repeat or are blank
    # between fixes. Take the distinct fixes only. Never forward-fill -- an interpolated
    # "measurement" fed back as truth is circular.
    #
    # A fix is a **position change**, not a distinct row. Deduplicating across every GNSS column
    # counted a row whose lat/lon repeated but whose sats-in-range had ticked as a new fix, which
    # inflated the count 3.5x on S3a (879 rows kept against 253 real position changes) -- and the
    # fix count is what the update rate, the re-acquisition study (EVALUATION.md section 6) and
    # the GNSS-available baseline are all read off.
    gnss = _distinct_fixes(df, gnss_cols)

    return Sequence(name=seq_name, imu=imu, gnss=gnss, split=split_of(seq_name))


def _distinct_fixes(df: pd.DataFrame, gnss_cols: list[str]) -> pd.DataFrame:
    """One row per GPS position change, carrying its timestamp and IMU sample index."""
    if "gps_lat" not in gnss_cols or "gps_lon" not in gnss_cols:
        raise ValueError(
            f"GNSS columns {gnss_cols} carry no position; ground truth and the gated update both "
            "need lat/lon"
        )
    carried = [c for c in ("time_since_start_ms", "date") if c in df.columns]
    frame = df[gnss_cols + carried].copy()
    frame["sample_idx"] = np.arange(len(df), dtype=int)

    positioned = frame[frame["gps_lat"].notna() & frame["gps_lon"].notna()]
    pos = positioned[["gps_lat", "gps_lon"]]
    changed = (pos != pos.shift()).any(axis=1)
    return positioned[changed].reset_index(drop=True)


def _preferred_copy(candidates: list[Path]) -> Path:
    """Pick deterministically between multiple copies of the same stem.

    Every one of the 72 `S-` stems ships twice in the synchronised folder under two different
    checksums, and on 57 of them the uncategorised copy is materially larger -- rows, not line
    endings, so sequence duration, outage tiling and every metric move with the choice. Taking
    `candidates[0]` off a glob made that choice by filesystem ordering, which is a direct threat
    to Gate 0's "reproduces to the digit across two machines".

    The categorised tree wins, matching `eval.loaders.truth.manifest_path_for`. That is a
    tie-break for determinism, not a ruling on which copy the protocol should use: seat D owns
    that, and `eval.loaders.truth.divergent_copies` quantifies it.
    """
    return min(candidates, key=lambda p: ("Uncategorised" in str(p), str(p)))


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
        loaded[name] = load_sequence(_preferred_copy(candidates), name=name)
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} sequence(s) not found under {root}: {missing}\n"
            "Check data/manifest/ and docs/DATASETS.md for the expected layout."
        )
    return loaded
