"""Ground truth from the paired `V-` VBOX GPS.

**Why this module exists.** `docs/EVALUATION.md` §2 was drafted as "1 Hz GNSS". The `S-`
smartphone GPS is not 1 Hz: measured across all 72 `S-` stems in the synchronised folder the
median inter-fix interval is **9.0 s**, and only three stems update at 1 Hz. CTE and CRSE are
defined as sums over 1 s epochs (D-054), and drift-% needs a truth position at the outage
boundary -- neither is computable from a fix every 9 s without inventing positions between
fixes. `EVALUATION.md` §1.2 already permits the paired `V-` GPS as ground truth on paired
sequences, and it is a 10 Hz VBOX. That is the truth source this module reads.

**What this module is not.** It is not a second way into the `V-` stream. Three properties
keep it narrow, and each is pinned by a test:

1. The column allowlist here is *lat, lon and time of day*. Nothing else -- not GPS velocity,
   not heading. A velocity column here becomes a speed label the first time someone is short of
   one, and the speed head is the part of this system whose honesty matters most.
2. Columns are selected from the header *before* the file body is read, so a wheel-speed column
   is never materialised in memory at all, let alone dropped later.
3. `TruthTrack` is deliberately not a `Sequence`. It has no `features()` and holds no inertial
   channels, so there is no call that hands it to a model or a filter.

The `S-` GNSS columns keep their other role unchanged: they remain the gated filter update, which
is the measurement a phone would actually have. Truth is what we grade against; the update is what
the system gets. Sourcing them differently is the whole point.

Protocol: `docs/EVALUATION.md` §1.2 and §2. Guard semantics: `eval/loaders/columns.py`.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from eval.loaders.columns import DENY_PATTERN, LeakageError
from idr.geo import geodetic_to_ned, path_length, vincenty_inverse

if TYPE_CHECKING:  # pragma: no cover - import kept out of the runtime path
    from eval.loaders.io_vnbd import Sequence

#: The VBOX GPS rate. Unlike the `S-` stream's nominal rate this one is measured and holds:
#: median inter-sample interval 0.10 s on every paired file checked.
TRUTH_RATE_HZ = 10

#: How far an epoch boundary may sit from the nearest `V-` sample before the lookup refuses.
#: Half a sample period. At 10 Hz truth every 1 s epoch lands on a sample, so this tolerance is
#: never *needed* -- it exists so that a file which quietly is not 10 Hz fails here instead of
#: being silently interpolated into a plausible-looking trajectory.
MAX_EPOCH_OFFSET_S = 0.05

#: Everything this module is allowed to read out of a `V-` file.
TRUTH_COLUMNS: frozenset[str] = frozenset({"gps_lat", "gps_lon", "time_of_day_s"})

#: `V-` header spellings, matched against the whitespace-collapsed lowercase header.
#:
#: Anchored at the start and, for the time column, on its unit -- the mirror image of the anchor
#: D-047 put on the `S-` side so that the two streams' time columns cannot be confused for one
#: another in either direction. They are different quantities: `S-` counts milliseconds from the
#: start of the recording, `V-` counts seconds from midnight.
_TRUTH_ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(gps )?lat(itude)?\b"), "gps_lat"),
    (re.compile(r"^(gps )?long?(itude)?\b"), "gps_lon"),
    (re.compile(r"^time since start of day\b"), "time_of_day_s"),
)

SECONDS_PER_DAY = 86_400.0

#: `S-` date format, per the shipped header `DATE (YYYY-MO-DD HH-MI-SS_SSS)`. Some files truncate
#: the millisecond group, so the fractional part is optional.
#: The `S-` `date` value, as the files actually ship it.
#:
#: The header advertises `YYYY-MO-DD HH-MI-SS_SSS`, and this pattern was originally written from
#: that string rather than from the bytes. The bytes disagree in two ways, and every real `S-`
#: file fails on both: the sub-second separator is a colon, not `_` or `.`
#: (`19:21:51:494`), and each value is wrapped in literal single quotes that the `$`
#: anchor then refuses. The trailing-quote class and the `:` in the sub-second group are what
#: make the shipped spelling parse; the advertised spelling still parses unchanged.
_S_DATE = re.compile(
    r"(?P<h>\d{1,2})[-:](?P<m>\d{2})[-:](?P<s>\d{2})(?:[._:](?P<ms>\d{1,3}))?['\"\s]*$"
)

#: The calendar half of the same value, anchored at the start so it cannot match the time.
#: `_S_DATE` deliberately reads only the clock; this reads only the date, because whether the
#: clock is BST or GMT is a question the date answers and the time cannot (D-091).
_S_CALENDAR_DATE = re.compile(r"^['\"\s]*(?P<Y>\d{4})-(?P<Mo>\d{1,2})-(?P<D>\d{1,2})")

#: British Summer Time is UTC+1.
BST_OFFSET_S = 3600.0


class TruthPairingError(LookupError):
    """No usable paired `V-` file, or more than one that disagree.

    Not a LeakageError: nothing disallowed happened. It means the truth for this sequence cannot
    be established, which is a reason to drop the sequence from the protocol -- loudly -- rather
    than to fall back to the 9 s `S-` fixes and report the number anyway.
    """


def normalise_truth_header(name: str) -> str:
    """Normalise a `V-` header to a canonical name, or to a generic form the allowlist rejects."""
    collapsed = re.sub(r"\s+", " ", name.strip().lower())
    for pattern, canonical in _TRUTH_ALIASES:
        if pattern.match(collapsed):
            return canonical
    generic = re.sub(r"\(.*?\)", " ", collapsed)
    generic = re.sub(r"[^a-z0-9]+", "_", generic)
    return generic.strip("_")


def assert_truth_only(columns: Iterable[str]) -> None:
    """Raise unless every column is one of lat, lon, time of day.

    An allowlist, like the `S-` guard, and a deliberately smaller one. The denylist is applied
    first so that a wheel-speed column produces the loud, specific message rather than the
    generic "not on the truth allowlist" -- reaching this function with a wheel column in hand
    means something upstream is badly wrong and the error should say so.
    """
    offenders: list[tuple[str, str]] = []
    for raw in columns:
        norm = normalise_truth_header(raw)
        if DENY_PATTERN.search(norm):
            offenders.append((raw, "matches the banned vehicle-sensor pattern"))
        elif norm not in TRUTH_COLUMNS:
            offenders.append((raw, "is not on the truth allowlist in eval/loaders/truth.py"))
    if offenders:
        detail = "\n".join(f"  - {raw!r}: {why}" for raw, why in offenders)
        raise LeakageError(
            f"Disallowed channel(s) reached the ground-truth path:\n{detail}\n\n"
            "This module reads lat, lon and time of day from the paired 'V-' file and nothing "
            "else. Widening it is a protocol change (EVALUATION.md section 1.2), not a code "
            "change -- record a DECISION_LOG entry first."
        )


# --------------------------------------------------------------------------------------------
# The track
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TruthTrack:
    """A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else.

    Deliberately not a `Sequence`. There is no `features()` here and no inertial channel, so the
    type system itself prevents this reaching a model input -- which is the property that makes
    reading the banned stream for truth defensible rather than merely permitted.
    """

    name: str
    t_s: np.ndarray  # seconds since midnight, unwrapped, strictly increasing
    lat: np.ndarray
    lon: np.ndarray
    source: str

    def __post_init__(self) -> None:
        if not (self.t_s.shape == self.lat.shape == self.lon.shape):
            raise ValueError(
                f"{self.name}: truth arrays disagree in shape -- "
                f"t {self.t_s.shape}, lat {self.lat.shape}, lon {self.lon.shape}"
            )
        if self.t_s.size < 2:
            raise ValueError(f"{self.name}: a truth track needs at least two fixes")
        if not np.all(np.diff(self.t_s) > 0):
            raise ValueError(
                f"{self.name}: truth timestamps are not strictly increasing. Sort or reject the "
                "file; do not interpolate over it."
            )

    @property
    def n_fixes(self) -> int:
        return int(self.t_s.size)

    @property
    def duration_s(self) -> float:
        return float(self.t_s[-1] - self.t_s[0])

    @property
    def median_dt_s(self) -> float:
        return float(np.median(np.diff(self.t_s)))

    def index_at(self, times_s: np.ndarray, *, tol_s: float = MAX_EPOCH_OFFSET_S) -> np.ndarray:
        """Nearest-sample indices for a set of epoch times. Raises if any is further than tol.

        Nearest sample, never interpolation. At 10 Hz truth a 1 s epoch boundary coincides with a
        sample, so interpolation would buy nothing and would quietly manufacture a position the
        instrument never reported the moment the assumption stopped holding.
        """
        t = np.atleast_1d(np.asarray(times_s, dtype=float))
        if t.size == 0:
            raise ValueError("no epoch times requested")
        idx = np.searchsorted(self.t_s, t)
        idx = np.clip(idx, 1, self.t_s.size - 1)
        left, right = self.t_s[idx - 1], self.t_s[idx]
        nearest = np.where(t - left <= right - t, idx - 1, idx)
        offset = np.abs(self.t_s[nearest] - t)
        bad = offset > tol_s
        if np.any(bad):
            worst = int(np.argmax(offset))
            raise TruthPairingError(
                f"{self.name}: {int(bad.sum())} of {t.size} epoch(s) have no truth sample within "
                f"{tol_s} s; worst is {offset[worst]:.3f} s at t = {t[worst]:.3f} s. The paired "
                "'V-' file does not cover this window at 10 Hz -- drop the window from the "
                "protocol rather than interpolating across the gap."
            )
        return nearest

    def positions_at(self, times_s: np.ndarray, *, tol_s: float = MAX_EPOCH_OFFSET_S) -> np.ndarray:
        """Latitude/longitude at each epoch time, shape ``(n, 2)``."""
        idx = self.index_at(times_s, tol_s=tol_s)
        return np.column_stack([self.lat[idx], self.lon[idx]])

    def ned_at(self, times_s: np.ndarray, *, tol_s: float = MAX_EPOCH_OFFSET_S) -> np.ndarray:
        """Local NED positions at each epoch time, relative to the first, shape ``(n, 2)``."""
        pos = self.positions_at(times_s, tol_s=tol_s)
        return geodetic_to_ned(pos[:, 0], pos[:, 1], pos[0, 0], pos[0, 1])

    def displacements_ned(
        self, times_s: np.ndarray, *, tol_s: float = MAX_EPOCH_OFFSET_S
    ) -> np.ndarray:
        """Per-epoch NED *displacements*, shape ``(n-1, 2)``.

        This is what `eval.metrics.core.per_epoch_errors` consumes: it compares displacements,
        not absolute positions, so a constant offset between the two trajectories does not
        masquerade as a per-epoch error.
        """
        ned = self.ned_at(times_s, tol_s=tol_s)
        if ned.shape[0] < 2:
            raise ValueError(f"{self.name}: need at least two epochs to form a displacement")
        return np.diff(ned, axis=0)

    def distance_m(
        self, t_start_s: float, t_end_s: float, *, tol_s: float = MAX_EPOCH_OFFSET_S
    ) -> float:
        """Vincenty path length between two times, in metres.

        The `L` in drift-%. Path length along the driven route, not endpoint separation -- on a
        roundabout the two differ by nearly the whole path, and drift-% is the graded number.
        """
        lo, hi = self.index_at(np.array([t_start_s, t_end_s]), tol_s=tol_s)
        if hi <= lo:
            raise ValueError(
                f"{self.name}: empty truth window [{t_start_s}, {t_end_s}] s"
            )
        return path_length(self.lat[lo : hi + 1], self.lon[lo : hi + 1])


# --------------------------------------------------------------------------------------------
# Pairing -- which file on disk is this stem's truth
# --------------------------------------------------------------------------------------------

DEFAULT_MANIFEST = Path("data/manifest/io_vnbd.csv")

#: Truth comes from the synchronised folder only. The unsynchronised copy of the same stem is a
#: different recording alignment, and the whole argument for using `V-` GPS as truth rests on the
#: two streams sharing a clock.
_SYNCHRONISED = "Synchronised"


def manifest_path_for(
    stem: str,
    stream: str,
    data_root: str | Path,
    *,
    manifest: str | Path = DEFAULT_MANIFEST,
    strict_checksum: bool = True,
) -> Path:
    """Locate one shipped file by stem and stream, via the checksum manifest.

    Via the manifest, not a glob, for three reasons. The manifest records the exact shipped path,
    so it survives the folder layout changing; it carries the sha256, so two copies of a stem can
    be checked to be the same recording rather than assumed to be; and it sidesteps case. The same
    stem ships as `V-vta9.csv` in the synchronised folder and `V-Vta9.csv` in the unsynchronised
    one, so a `V-{stem}.csv` glob works on the Windows dev box and silently finds nothing on CI's
    Ubuntu -- a difference that would surface as an absent held-out sequence, not as an error.

    ``strict_checksum`` refuses when the two synchronised copies of a stem are not the same bytes.
    That holds for every `V-` file, so truth pairing keeps it on and a future divergence there is
    a real alarm. It does **not** hold for the `S-` stream -- all 72 stems ship as two different
    files -- so the `S-` lookup turns it off and takes the categorised copy, deliberately and in
    one place. See `divergent_copies`.
    """
    manifest_path = Path(manifest)
    if not manifest_path.exists():
        raise TruthPairingError(
            f"manifest not found at {manifest_path}. Truth pairing reads the manifest rather than "
            "globbing the dataset; see docs/DATASETS.md."
        )

    wanted = f"{stream.lower()}{stem.lower()}.csv"
    rows: list[dict[str, str]] = []
    with manifest_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("stream") != stream:
                continue
            if Path(row["path"]).name.lower() != wanted:
                continue
            if _SYNCHRONISED not in row["path"]:
                continue
            rows.append(row)

    if not rows:
        raise TruthPairingError(
            f"no synchronised {stream!r} file for stem {stem!r} in {manifest_path}. Without a "
            "paired 10 Hz VBOX track a sequence has no usable ground truth (EVALUATION.md "
            "section 1.2) and must be dropped from the split, not graded against 9 s 'S-' fixes."
        )

    shas = {row["sha256"] for row in rows}
    if len(shas) > 1 and strict_checksum:
        listing = "\n".join(f"  - {row['path']} ({row['sha256'][:12]})" for row in rows)
        raise TruthPairingError(
            f"{stem}: {len(rows)} synchronised {stream!r} copies with different checksums:\n"
            f"{listing}\nThey are not the same recording, so which one is authoritative is a "
            "question about the dataset and not something this loader may pick for you."
        )

    # Prefer the categorised tree, always and everywhere. Where the copies are identical this is
    # merely a stable path; where they are not (every `S-` stem) it is the choice itself, made
    # once and visibly rather than by whichever order a glob happened to return -- which is what
    # Gate 0's "reproduces to the digit across two machines" criterion turns on.
    chosen = min(rows, key=lambda r: ("Uncategorised" in r["path"], r["path"]))
    resolved = Path(data_root) / chosen["path"]
    if not resolved.exists():
        raise TruthPairingError(
            f"{stem}: manifest names {chosen['path']} but it is not under {data_root}. "
            "Re-check the download against data/manifest/io_vnbd.csv."
        )
    return resolved


def paired_truth_path(
    stem: str, data_root: str | Path, *, manifest: str | Path = DEFAULT_MANIFEST
) -> Path:
    """The `V-` file paired with an `S-` stem: this sequence's ground truth."""
    return manifest_path_for(stem, "V-", data_root, manifest=manifest)


@dataclass(frozen=True)
class CopyDivergence:
    """A stem whose two synchronised copies are not the same file."""

    stream: str
    filename: str
    categorised_sha: str
    uncategorised_sha: str
    categorised_bytes: int
    uncategorised_bytes: int

    @property
    def delta_bytes(self) -> int:
        return self.uncategorised_bytes - self.categorised_bytes


def divergent_copies(*, manifest: str | Path = DEFAULT_MANIFEST) -> list[CopyDivergence]:
    """Every stem shipping twice in the synchronised folder under two different checksums.

    Found while wiring truth pairing, and worth its own artefact: **all 72 `S-` stems diverge and
    no `V-` stem does.** Fifty-seven differ substantively, the uncategorised copy larger every
    time by up to 8.9%; the remaining fifteen differ by 5 or 6 bytes, which is a trailing newline.
    A percentage difference is rows, not line endings, so those two copies are different lengths
    of recording and every derived number moves with the choice between them: sequence duration,
    the outage tiling, the fix count, the metrics.

    `load_split` currently globs and takes the first match, so today that choice is made by
    filesystem ordering. Which copy the protocol should use is seat D's to settle; this function
    exists so the question is visible and quantified rather than silently answered per machine.
    """
    rows: dict[tuple[str, str], list[dict[str, str]]] = {}
    with Path(manifest).open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if _SYNCHRONISED not in row["path"]:
                continue
            rows.setdefault((row["stream"], Path(row["path"]).name.lower()), []).append(row)

    out: list[CopyDivergence] = []
    for (stream, filename), group in sorted(rows.items()):
        if len(group) < 2 or len({r["sha256"] for r in group}) == 1:
            continue
        cat = next((r for r in group if "Uncategorised" not in r["path"]), None)
        unc = next((r for r in group if "Uncategorised" in r["path"]), None)
        if cat is None or unc is None:
            continue
        out.append(
            CopyDivergence(
                stream=stream,
                filename=filename,
                categorised_sha=cat["sha256"][:12],
                uncategorised_sha=unc["sha256"][:12],
                categorised_bytes=int(cat["bytes"]),
                uncategorised_bytes=int(unc["bytes"]),
            )
        )
    return out


def paired_stems(*, manifest: str | Path = DEFAULT_MANIFEST) -> list[str]:
    """Every stem shipping **both** an `S-` and a `V-` file in the synchronised folder.

    This is the candidate pool for the D-044 split re-pick, and it is the pool because those two
    conditions are exactly what a held-out sequence needs: an `S-` smartphone stream to consume
    (H-1 bars the `V-` side from the feature path) and a paired `V-` VBOX track to be graded
    against (EVALUATION.md section 1.2). Synchronised only, for the reason `_SYNCHRONISED` gives
    -- the argument for `V-` GPS as truth rests on the two streams sharing a clock.

    **Membership of the pool is not fitness for the split.** It says the two files exist, which is
    what a file listing can establish and the limit of what it can: D-044 was drafted from a
    listing and the first contact with real bytes refused 6 of its 14 stems. Whether a stem may be
    graded is `align_to_sequence`, and `python -m eval.cadence --all-paired` is what runs it over
    this pool (D-090).

    Read from the manifest rather than the tree so the pool is the same on a machine that has not
    downloaded the dataset -- which is the machine the enumeration was needed on -- and so it
    sidesteps the case difference between `V-vta9.csv` and `V-Vta9.csv` that `manifest_path_for`
    documents. Returned in the manifest's own spelling of the `S-` file, sorted case-insensitively.
    """
    manifest_path = Path(manifest)
    if not manifest_path.exists():
        raise TruthPairingError(
            f"manifest not found at {manifest_path}. The candidate pool is read from the manifest "
            "rather than from the dataset tree; see docs/DATASETS.md."
        )

    seen: dict[str, dict[str, str]] = {}
    with manifest_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            stream = row.get("stream", "")
            if stream not in ("S-", "V-") or _SYNCHRONISED not in row["path"]:
                continue
            name = Path(row["path"]).name
            stem = name[len(stream) : -len(".csv")]
            seen.setdefault(stem.lower(), {})[stream] = stem

    return sorted(
        (spellings["S-"] for spellings in seen.values() if "S-" in spellings and "V-" in spellings),
        key=str.lower,
    )


# --------------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------------


def load_truth(path: str | Path, name: str) -> TruthTrack:
    """Read lat, lon and time of day from one `V-` file.

    The header is read on its own first and the body is then read with `usecols` restricted to the
    three truth columns, so no banned channel is ever materialised. latin-1 for the same reason
    the `S-` loader uses it (D-047): the shipped headers carry raw 0xB0/0xB5 bytes.
    """
    p = Path(path)
    header = pd.read_csv(p, encoding="latin-1", nrows=0)
    mapping = {raw: normalise_truth_header(raw) for raw in header.columns}
    selected = {raw: norm for raw, norm in mapping.items() if norm in TRUTH_COLUMNS}

    missing = TRUTH_COLUMNS - set(selected.values())
    if missing:
        raise TruthPairingError(
            f"{p} is missing truth column(s) {sorted(missing)}.\n"
            f"Headers seen: {list(header.columns)}\n"
            "If the shipped spelling differs from the aliases in eval/loaders/truth.py, add the "
            "spelling -- do not widen TRUTH_COLUMNS."
        )
    duplicated = sorted({n for n in selected.values() if list(selected.values()).count(n) > 1})
    if duplicated:
        raise TruthPairingError(
            f"{p}: more than one header maps onto {duplicated}. Resolve the spelling before "
            "using this file as truth; picking one silently would pick it differently on the "
            "next file."
        )

    assert_truth_only(selected.keys())
    df = pd.read_csv(p, encoding="latin-1", usecols=list(selected), low_memory=False)
    df = df.rename(columns=selected)[sorted(TRUTH_COLUMNS)]
    df = df.dropna().reset_index(drop=True)

    t = unwrap_time_of_day(df["time_of_day_s"].to_numpy(dtype=float))
    keep = np.concatenate([[True], np.diff(t) > 0])
    return TruthTrack(
        name=name,
        t_s=t[keep],
        lat=df["gps_lat"].to_numpy(dtype=float)[keep],
        lon=df["gps_lon"].to_numpy(dtype=float)[keep],
        source=str(p),
    )


def unwrap_time_of_day(t_s: np.ndarray) -> np.ndarray:
    """Make a seconds-since-midnight series monotonic across a midnight rollover.

    IO-VNBD includes night driving, and a sequence that crosses midnight otherwise reads as an
    86,400 s jump backwards -- which would fail the monotonicity check as if the file were corrupt.
    """
    t = np.asarray(t_s, dtype=float).copy()
    if t.size < 2:
        return t
    rollovers = np.diff(t) < -SECONDS_PER_DAY / 2
    return t + np.concatenate([[0.0], np.cumsum(rollovers) * SECONDS_PER_DAY])


def _last_sunday(year: int, month: int) -> int:
    """Day of the month of its last Sunday. March and October both have 31 days."""
    # `date.weekday()` is Mon=0 .. Sun=6, so this steps back from the 31st to the nearest Sunday.
    return 31 - ((date(year, month, 31).weekday() - 6) % 7)


def uk_utc_offset_s(year: int, month: int, day: int, hour: int) -> float:
    """Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or zero.

    The published rule: British Summer Time runs from **01:00 UTC on the last Sunday of March**
    to **01:00 UTC on the last Sunday of October**, which in local terms is 01:00 GMT -> 02:00 BST
    in spring and 02:00 BST -> 01:00 GMT in autumn. Implemented from the standard rather than via
    `zoneinfo`, which needs the `tzdata` package on Windows -- the dev box -- and G-5 forbids the
    dependency. The boundaries are pinned by hand-computed tests, not by this code's own output.

    **The autumn transition has one ambiguous local hour** (01:00-01:59 occurs twice, once BST and
    once GMT) which no local timestamp can resolve. It is read as BST, the earlier of the two, and
    said out loud here rather than guessed silently. No IO-VNBD recording falls in it: the dataset
    was collected 2019-08-30 to 2020-01-08 and the 2019 transition is 2019-10-27.
    """
    if not 3 <= month <= 10:
        return 0.0
    if month == 3:
        start = _last_sunday(year, 3)
        return BST_OFFSET_S if (day > start or (day == start and hour >= 2)) else 0.0
    if month == 10:
        end = _last_sunday(year, 10)
        return BST_OFFSET_S if (day < end or (day == end and hour < 2)) else 0.0
    return BST_OFFSET_S


def seconds_of_day(dates: Iterable[object]) -> np.ndarray:
    """Parse the `S-` `date` column into seconds since midnight, **as shipped**.

    This is the parser and nothing more: the value it returns is UK *local* time, because that is
    what the column holds. Use `seconds_of_day_utc` to compare it with anything on the `V-` clock.

    The header's format string is not what the column contains -- see `_S_DATE`. Both the
    advertised and the shipped spellings parse.
    """
    return unwrap_time_of_day(_parse_local_seconds(list(dates)))


def _parse_local_seconds(values: list[object]) -> np.ndarray:
    """Local seconds since midnight per row, **not** unwrapped. NaN where the row does not parse.

    Split out so the timezone conversion can happen between parsing and unwrapping. Unwrapping
    first and converting after would let a midnight rollover and a BST transition be applied in
    the wrong order, and the result would differ by a day rather than by an hour.
    """
    out = np.full(len(values), np.nan)
    for i, value in enumerate(values):
        if not isinstance(value, str):
            continue
        m = _S_DATE.search(value)
        if m is None:
            continue
        ms = m.group("ms")
        out[i] = (
            int(m.group("h")) * 3600
            + int(m.group("m")) * 60
            + int(m.group("s"))
            + (int(ms.ljust(3, "0")) / 1000.0 if ms else 0.0)
        )
    if np.all(np.isnan(out)):
        sample = next((d for d in values if isinstance(d, str)), None)
        raise ValueError(
            "no value in the 'date' column parses as a time of day; first string seen: "
            f"{sample!r}. Expected the header's 'YYYY-MO-DD HH-MI-SS_SSS' form or the "
            "'YYYY-MO-DD HH:MI:SS:SSS' form the files actually ship."
        )
    return out


def seconds_of_day_utc(dates: Iterable[object]) -> np.ndarray:
    """The same column, converted from UK local time to UTC -- the `V-` VBOX clock (D-091).

    `seconds_of_day`'s docstring used to say that no timezone question arises because "both
    streams were logged on the same vehicle on the same clock". The vehicle is one thing and the
    two loggers are another: AndroSensor writes the phone's civil time and the VBOX writes UTC, so
    every recording made inside British Summer Time puts the two exactly an hour apart. Measured
    on three reset-free BST stems -- S3a +3593.5 s, S1 +3600.5 s, S3c +3600.7 s -- against
    Vta1a -13.6 s, Vw4 +0.3 s and Vtb3 -1.4 s outside it. That was S3a's "0 of 254 fixes matched".

    **Per row, from that row's own date**, not once for the file. A recording that straddled the
    autumn transition would carry both offsets, and applying one file-wide would reintroduce the
    hour it exists to remove. Converting each row first also makes the series continuous across
    the transition, where the local clock genuinely steps backwards, so `unwrap_time_of_day` is
    applied after the conversion and not before.

    A row whose calendar date does not parse keeps its local time and is **not** silently assumed
    to be UTC: the value is left as `seconds_of_day` read it and `align_to_sequence` then reports
    an hour of residual, which is loud. Guessing an offset for a date we could not read is how a
    frame error becomes invisible.
    """
    values = list(dates)
    local = _parse_local_seconds(values)
    for i, value in enumerate(values):
        if not isinstance(value, str) or not np.isfinite(local[i]):
            continue
        cal = _S_CALENDAR_DATE.match(value)
        clock = _S_DATE.search(value)
        if cal is None or clock is None:
            continue
        local[i] -= uk_utc_offset_s(
            int(cal.group("Y")), int(cal.group("Mo")), int(cal.group("D")), int(clock.group("h"))
        )
    return unwrap_time_of_day(local)


# --------------------------------------------------------------------------------------------
# Alignment -- the check that decides whether any of this is usable
# --------------------------------------------------------------------------------------------


#: Lags searched when asking whether the two streams describe the same drive at the same time.
#: +/-5 s at the truth sample period. Wide enough to expose a synchronisation error that matters
#: (at 16 m/s even 0.5 s is 8 m of residual) and narrow enough that the search cannot wander onto
#: a different part of the route and report a spurious agreement.
LAG_SEARCH_S = 5.0
LAG_STEP_S = 0.1

#: Largest residual, in metres, at which a stem may be graded against `V-` truth. Two receivers
#: each quoted at +/-3 m, differenced, sit comfortably inside this; a genuine misalignment at
#: motorway speed puts a whole second of driving (~16 m) into the residual and fails.
MAX_TRUTH_RESIDUAL_M = 10.0

#: Largest best-fit lag treated as agreement rather than as a synchronisation defect.
MAX_TRUTH_LAG_S = 0.5


@dataclass(frozen=True)
class AlignmentReport:
    """How well the paired `V-` track agrees with the `S-` fixes it is standing in for.

    This is the evidence for the protocol change, not a diagnostic. If the residual at the `S-`
    stream's own fixes is not of order the +/-3 m the two receivers are quoted at, then the two
    files are not describing the same drive at the same time and `V-` truth is not usable for this
    stem -- whatever the folder is called.

    Both a zero-lag residual and a best-fit lag are reported, because they fail differently. A
    small residual at a lag of zero is a synchronised pair. A small residual at a lag of 0.4 s is
    a pair that is synchronised to within a constant offset -- usable in principle, a finding
    about the dataset, and not something this module may silently subtract away. A residual that
    no lag improves is two different drives, and the stem has no truth.
    """

    sequence: str
    n_s_fixes: int
    n_matched: int
    residual_median_m: float
    residual_p95_m: float
    residual_max_m: float
    best_lag_s: float
    residual_at_best_lag_m: float
    s_time_is_monotonic: bool
    truth_median_dt_s: float

    @property
    def is_usable(self) -> bool:
        """Whether this stem may be graded against `V-` truth."""
        return (
            self.n_matched >= max(2, self.n_s_fixes // 2)
            and self.residual_median_m <= MAX_TRUTH_RESIDUAL_M
            and abs(self.best_lag_s) <= MAX_TRUTH_LAG_S
            and self.s_time_is_monotonic
        )


def _nearest(truth: TruthTrack, times_s: np.ndarray) -> np.ndarray:
    """Index of the nearest truth sample to each time, clipped to the track."""
    idx = np.clip(np.searchsorted(truth.t_s, times_s), 1, truth.t_s.size - 1)
    left, right = truth.t_s[idx - 1], truth.t_s[idx]
    return np.where(times_s - left <= right - times_s, idx - 1, idx)


def _approx_residuals_m(
    truth: TruthTrack, times_s: np.ndarray, lat: np.ndarray, lon: np.ndarray
) -> np.ndarray:
    """Tangent-plane separation in metres. Used for the lag search only.

    Vincenty for every candidate lag would be tens of thousands of calls per stem for a difference
    far below the metre the search is resolving; the reported residuals are computed exactly.
    """
    idx = _nearest(truth, times_s)
    ned = geodetic_to_ned(
        np.concatenate([lat, truth.lat[idx]]),
        np.concatenate([lon, truth.lon[idx]]),
        float(lat[0]),
        float(lon[0]),
    )
    half = lat.size
    return np.linalg.norm(ned[:half] - ned[half:], axis=1)


def _best_lag_s(
    truth: TruthTrack, times_s: np.ndarray, lat: np.ndarray, lon: np.ndarray
) -> tuple[float, float]:
    """The lag minimising the median residual, and that median. Reported, never applied."""
    # Rounded at construction: np.arange accumulates float error, and a reported lag of
    # -1.8e-14 in a committed artefact reads as a measurement rather than as zero.
    lags = np.round(np.arange(-LAG_SEARCH_S, LAG_SEARCH_S + LAG_STEP_S / 2, LAG_STEP_S), 3)
    medians = np.array(
        [float(np.median(_approx_residuals_m(truth, times_s + lag, lat, lon))) for lag in lags]
    )
    best = int(np.argmin(medians))
    return float(lags[best]), float(medians[best])


def align_to_sequence(seq: Sequence, truth: TruthTrack) -> AlignmentReport:
    """Compare a loaded `S-` sequence's own GPS fixes against the paired `V-` track.

    Alignment is by absolute time of day: both streams carry it, so no row-index correspondence
    has to be assumed -- which matters, because five `S-` stems restart their clock mid-file and
    any row-counting scheme would straddle the break without saying so. The clock offset is
    reported rather than corrected: a synchronised pair should show one near zero, and a large one
    is a finding about the dataset, not something to subtract away.
    """
    gnss = seq.gnss
    if "date" not in gnss.columns:
        raise TruthPairingError(
            f"{truth.name}: the loaded sequence carries no 'date' column, so its fixes cannot be "
            "placed on the clock. Reload it with a loader that keeps the fix timestamps."
        )

    # UTC, not the shipped local time: the `V-` track's clock is UTC, and comparing a BST
    # timestamp against it puts an hour of road between two files that describe the same drive
    # (D-091). This is the frame conversion; the residual below is still reported, never fitted.
    t_s = seconds_of_day_utc(gnss["date"].tolist())
    lat = gnss["gps_lat"].to_numpy(dtype=float)
    lon = gnss["gps_lon"].to_numpy(dtype=float)
    finite = np.isfinite(t_s) & np.isfinite(lat) & np.isfinite(lon)
    t_s, lat, lon = t_s[finite], lat[finite], lon[finite]
    monotonic = bool(t_s.size < 2 or np.all(np.diff(t_s) >= 0))

    in_range = (t_s >= truth.t_s[0] - MAX_EPOCH_OFFSET_S) & (
        t_s <= truth.t_s[-1] + MAX_EPOCH_OFFSET_S
    )
    matched_t, matched_lat, matched_lon = t_s[in_range], lat[in_range], lon[in_range]

    if matched_t.size == 0:
        return AlignmentReport(
            sequence=truth.name,
            n_s_fixes=int(t_s.size),
            n_matched=0,
            residual_median_m=float("inf"),
            residual_p95_m=float("inf"),
            residual_max_m=float("inf"),
            best_lag_s=float("nan"),
            residual_at_best_lag_m=float("inf"),
            s_time_is_monotonic=monotonic,
            truth_median_dt_s=truth.median_dt_s,
        )

    nearest = _nearest(truth, matched_t)
    residuals = np.array(
        [
            vincenty_inverse(a, b, c, d)
            for a, b, c, d in zip(
                matched_lat, matched_lon, truth.lat[nearest], truth.lon[nearest], strict=True
            )
        ]
    )
    lag, lag_residual = _best_lag_s(truth, matched_t, matched_lat, matched_lon)
    return AlignmentReport(
        sequence=truth.name,
        n_s_fixes=int(t_s.size),
        n_matched=int(matched_t.size),
        residual_median_m=float(np.median(residuals)),
        residual_p95_m=float(np.percentile(residuals, 95)),
        residual_max_m=float(np.max(residuals)),
        best_lag_s=lag,
        residual_at_best_lag_m=lag_residual,
        s_time_is_monotonic=monotonic,
        truth_median_dt_s=truth.median_dt_s,
    )
