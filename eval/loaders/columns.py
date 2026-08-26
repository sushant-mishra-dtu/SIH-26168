"""Channel allowlist and the leakage guard.

PS 26168 disallows wheel odometry. IO-VNBD ships the wheel-speed columns in the same download,
in adjacent columns, on paired sequence names -- which makes accidental leakage a one-typo
mistake that would invalidate every number in the submission.

The rule is an **allowlist**, not a denylist. A denylist protects you from the columns you thought
of; an allowlist protects you from the ones you did not. The denylist below is a second layer that
exists to produce a *loud, specific* error message rather than a generic "unknown column".

See docs/EVALUATION.md section 1.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# --------------------------------------------------------------------------------------------
# Allowlist: IO-VNBD "S-" smartphone stream, 10 Hz (GPS 1 Hz).
# Names are matched case-insensitively after normalisation (see normalise()).
# --------------------------------------------------------------------------------------------

INERTIAL_CHANNELS: frozenset[str] = frozenset(
    {
        "accel_x", "accel_y", "accel_z",          # m/s^2
        "gravity_x", "gravity_y", "gravity_z",    # m/s^2
        "gyro_yaw", "gyro_pitch", "gyro_roll",    # rad/s
        "magnetic_x", "magnetic_y", "magnetic_z", # uT
        "orientation_yaw", "orientation_pitch", "orientation_roll",  # deg
    }
)

TIME_CHANNELS: frozenset[str] = frozenset({"time_since_start_ms", "date"})

#: GNSS is reference + gated update only. It is never a network input feature.
GNSS_CHANNELS: frozenset[str] = frozenset(
    {
        "gps_lat", "gps_lon", "gps_altitude_m", "gps_speed_kmh",
        "gps_accuracy_m", "gps_orientation_deg", "gps_sats",
    }
)

ALLOWED_COLUMNS: frozenset[str] = INERTIAL_CHANNELS | TIME_CHANNELS | GNSS_CHANNELS

#: What a model or filter may consume as an input feature. Deliberately excludes GNSS: during an
#: outage there is no GNSS, so a feature set containing it would train on information the system
#: does not have at inference time.
FEATURE_COLUMNS: frozenset[str] = INERTIAL_CHANNELS

# --------------------------------------------------------------------------------------------
# Denylist: the "V-" ECU/CAN stream. Second layer, for better error messages.
# --------------------------------------------------------------------------------------------

DENY_PATTERN = re.compile(
    r"wheel|steer|rpm|engine|brake|clutch|gear|pedal|handbrake|coolant|throttle|torque|odo",
    re.IGNORECASE,
)

V_STREAM_PATTERN = re.compile(r"^v[-_]", re.IGNORECASE)


class LeakageError(AssertionError):
    """A disallowed channel reached a feature path.

    Deliberately an AssertionError subclass: this is a broken invariant, not a recoverable
    condition. Nothing in this repo may catch it.
    """


def normalise(name: str) -> str:
    """Normalise a raw CSV header to our canonical snake_case form.

    AndroSensor headers are inconsistent across the three logging devices, carrying units,
    spaces and parentheses. Normalising here means the allowlist has one spelling to check
    rather than three.
    """
    n = name.strip().lower()
    n = re.sub(r"\(.*?\)", " ", n)        # drop "(m/s^2)", "(deg)", ...
    n = re.sub(r"[^a-z0-9]+", "_", n)     # everything else becomes an underscore
    return n.strip("_")


def assert_no_leakage(columns: Iterable[str], *, context: str = "feature path") -> None:
    """Raise LeakageError if any disallowed channel is present.

    Called by the loader on every read, and again by the trainer on the final feature frame. Two
    call sites on purpose -- the audit runs twice (Sprint 1 and pre-submission) and a guard that
    only sits at the boundary misses anything constructed downstream.
    """
    offenders: list[tuple[str, str]] = []
    for raw in columns:
        norm = normalise(raw)
        if V_STREAM_PATTERN.match(raw.strip()):
            offenders.append((raw, "belongs to the disallowed 'V-' ECU/CAN stream"))
        elif DENY_PATTERN.search(norm):
            offenders.append((raw, "matches the banned vehicle-sensor pattern"))
        elif norm not in ALLOWED_COLUMNS:
            offenders.append((raw, "is not on the allowlist in eval/loaders/columns.py"))

    if offenders:
        detail = "\n".join(f"  - {raw!r}: {why}" for raw, why in offenders)
        raise LeakageError(
            f"Disallowed channel(s) reached the {context}:\n{detail}\n\n"
            "PS 26168 disallows wheel odometry. If this column is genuinely permitted, add it to "
            "ALLOWED_COLUMNS *and* record a DECISION_LOG entry saying why -- do not silence this "
            "check locally."
        )


def assert_feature_safe(columns: Iterable[str]) -> None:
    """Stricter guard for tensors entering a model or filter: inertial channels only.

    Passing this means the feature set contains nothing the system would lack inside a tunnel.
    """
    cols = [normalise(c) for c in columns]
    assert_no_leakage(columns, context="model feature tensor")
    extra = sorted(set(cols) - FEATURE_COLUMNS)
    if extra:
        raise LeakageError(
            f"Non-feature channel(s) in a model input tensor: {extra}\n"
            "GNSS and time columns are reference/bookkeeping only. A model trained on GNSS "
            "features learns from information that does not exist during an outage, which is the "
            "same class of mistake as wheel-speed leakage and just as fatal to the result."
        )
