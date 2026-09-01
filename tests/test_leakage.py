"""The leakage audit.

PS 26168 disallows wheel odometry. If this test ever passes when it should fail, every number in
the submission is invalid and no other test would notice.

Note the deliberate structure: we assert both that clean input passes **and** that dirty input
raises. A guard that has never been observed to reject something is not known to reject anything.
"""

from __future__ import annotations

import pytest

from eval.loaders.columns import (
    ALLOWED_COLUMNS,
    FEATURE_COLUMNS,
    LeakageError,
    assert_feature_safe,
    assert_no_leakage,
    normalise,
)

CLEAN = [
    "Accel X (m/s^2)", "Accel Y (m/s^2)", "Accel Z (m/s^2)",
    "Gravity X (m/s^2)", "Gravity Y (m/s^2)", "Gravity Z (m/s^2)",
    "Gyro Yaw (rad/s)", "Gyro Pitch (rad/s)", "Gyro Roll (rad/s)",
]


def test_clean_smartphone_columns_pass():
    assert_no_leakage(CLEAN)


def test_normalisation_strips_units_and_case():
    assert normalise("Accel X (m/s^2)") == "accel_x"
    assert normalise("  GYRO YAW  ") == "gyro_yaw"
    # Every GPS-speed spelling has to land on the one allowlisted name. This assertion previously
    # accepted "gps_speed_km_hr" or "gps_speed", neither of which is on the allowlist -- so a real
    # file was rejected whichever branch held. The shipped header is "GPS SPEED (Kmh)".
    assert normalise("GPS Speed (km/hr)") == "gps_speed_kmh"
    assert normalise("GPS SPEED (Kmh)") == "gps_speed_kmh"
    assert normalise("GPS Speed (km/hr)") in ALLOWED_COLUMNS


@pytest.mark.parametrize(
    "column",
    [
        "Wheel Speed FL (rad/s)",
        "wheel_speed_rr",
        "WHEELSPEED",
        "Steering Angle (deg)",
        "Engine Speed (rpm)",
        "Brake Pressure (psi)",
        "Clutch",
        "Gear Requested",
        "Accelerator Pedal (%)",
        "Handbrake",
    ],
)
def test_banned_vehicle_channels_raise(column):
    """Each of these is a real IO-VNBD 'V-' column name."""
    with pytest.raises(LeakageError, match="Disallowed channel"):
        assert_no_leakage(CLEAN + [column])


def test_v_stream_prefix_raises():
    with pytest.raises(LeakageError, match="V-"):
        assert_no_leakage(["V-wheel_speed_fl"])


def test_unknown_column_raises_even_if_innocent_looking():
    """The allowlist is the primary defence: unrecognised means rejected, not assumed safe."""
    with pytest.raises(LeakageError, match="not on the allowlist"):
        assert_no_leakage(CLEAN + ["some_new_sensor"])


def test_gnss_is_allowed_but_never_a_feature():
    """GNSS is reference and gated-update only.

    A model trained on GNSS features learns from information that does not exist inside a tunnel --
    the same class of mistake as wheel-speed leakage, and just as fatal to the result.
    """
    assert_no_leakage(["GPS Lat", "GPS Lon"])  # fine as reference
    with pytest.raises(LeakageError, match="Non-feature channel"):
        assert_feature_safe(["accel_x", "gps_lat"])


def test_feature_set_is_inertial_only():
    assert FEATURE_COLUMNS < ALLOWED_COLUMNS
    assert not any(c.startswith("gps_") for c in FEATURE_COLUMNS)


def test_guard_is_not_catchable_as_a_normal_error():
    """LeakageError subclasses AssertionError so a bare `except Exception` does not swallow it
    silently in a training loop."""
    assert issubclass(LeakageError, AssertionError)


# --------------------------------------------------------------------------------------------
# The ground-truth path into the "V-" stream
#
# EVALUATION.md section 1.2 permits the paired "V-" GPS as ground truth, and eval/loaders/truth.py
# is the one module that uses that permission. It is therefore the one place a wheel-speed column
# could enter this repo, so the audit job -- not only the truth module's own tests -- checks that
# it stays shut.
# --------------------------------------------------------------------------------------------


def test_the_truth_allowlist_is_a_strict_subset_of_position_and_time():
    """Whatever else changes, this module may never read a vehicle-dynamics channel."""
    from eval.loaders.truth import TRUTH_COLUMNS

    assert TRUTH_COLUMNS == {"gps_lat", "gps_lon", "time_of_day_s"}


@pytest.mark.parametrize(
    "column",
    [
        " Wheel Speed Front Left (rad/sec)",
        " Wheel Speed Rear Right (rad/sec)",
        " Steering Angle (degrees)",
        " Engine Speed (rev/min)",
        " Brake Pressure (psi)",
        " Indicated Vehicle Speed (Kmh)",
        " GPS Velocity (Kmh)",
    ],
)
def test_the_truth_guard_rejects_every_other_vehicle_channel(column):
    """Including `GPS Velocity`, which is neither wheel-derived nor banned by name. Truth is a
    position at a time; a velocity is a speed label, and the speed head is the part of this
    system whose honesty matters most."""
    from eval.loaders.truth import assert_truth_only

    with pytest.raises(LeakageError):
        assert_truth_only([column])


def test_truth_columns_can_never_become_model_features():
    """The two guards have to disagree in the right direction: the truth loader may read lat/lon,
    and the feature guard must still refuse them. Otherwise ground truth becomes an input and the
    model learns from information it will not have inside a tunnel."""
    from eval.loaders.truth import TRUTH_COLUMNS

    for column in sorted(TRUTH_COLUMNS):
        with pytest.raises(LeakageError):
            assert_feature_safe([column])


def test_the_smartphone_loader_still_refuses_a_vehicle_file():
    """The truth path is a separate module on purpose. `load_sequence` must not have acquired a
    way into the `V-` stream as a side effect of one existing elsewhere."""
    from eval.loaders.io_vnbd import load_sequence

    with pytest.raises(LeakageError, match="disallowed by PS 26168"):
        load_sequence("nonexistent/V-S3a.csv", name="V-S3a")


def test_the_truth_track_carries_no_inertial_channel():
    """Structural, not procedural. `TruthTrack` holds four fields and none of them is a sensor,
    so there is no call that hands ground truth to a filter or a model."""
    import inspect

    from eval.loaders.truth import TruthTrack

    fields = set(TruthTrack.__dataclass_fields__)
    assert fields == {"name", "t_s", "lat", "lon", "source"}
    assert not any(f in FEATURE_COLUMNS for f in fields)
    assert "features" not in dict(inspect.getmembers(TruthTrack))
