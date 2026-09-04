"""The `core/ffi/` interface definition (P-14).

There is no implementation to test, by decision (D-022, D-043) -- so what is tested is that the
header stays an accurate description of the Python reference it is the interface *to*. A header
that drifts from the filter is worse than no header: it is a contract two teams will write
against, and the disagreement surfaces when the JNI layer already exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.reference.inekf import ERROR_STATE_DIM, FilterConfig, InEKF

HEADER = Path(__file__).resolve().parents[1] / "core" / "ffi" / "idr_core.h"
TEXT = HEADER.read_text(encoding="utf-8")


def test_the_header_exists_and_is_an_interface_not_an_implementation():
    """D-043 ships a definition at screening. A function body here would be the October port
    starting early, in the file least likely to be reviewed for it."""
    assert HEADER.is_file()
    assert "INTERFACE DEFINITION" in TEXT
    # Every declaration ends in a semicolon; none opens a body.
    for decl in re.findall(r"^idr_status idr_\w+\([^;{]*[;{]", TEXT, re.MULTILINE):
        assert decl.rstrip().endswith(";"), f"function body in an interface file: {decl!r}"


def test_the_error_state_dimension_matches_the_filter():
    m = re.search(r"#define IDR_ERROR_STATE_DIM (\d+)", TEXT)
    assert m and int(m.group(1)) == ERROR_STATE_DIM


def test_every_entry_point_the_reference_filter_has_is_declared():
    """A surface that omits a call is a surface someone works around."""
    for name in (
        "idr_create", "idr_destroy", "idr_default_config", "idr_propagate",
        "idr_update_zupt", "idr_update_zaru", "idr_update_nhc", "idr_update_speed",
        "idr_update_gnss", "idr_reinflate_mount",
        "idr_get_state", "idr_get_covariance", "idr_get_yaw",
    ):
        assert f"{name}(" in TEXT, f"{name} is missing from the FFI surface"


def test_every_config_field_of_the_reference_filter_that_the_port_needs_is_present():
    """The port cannot reproduce the filter's behaviour without the values it is tuned by, and a
    field silently absent here becomes a hardcoded constant on the other side of the wall."""
    for field in (
        "gyro_arw", "accel_vrw", "gyro_bias_rw", "accel_bias_rw", "mount_rw",
        "imu_rate_hz", "zupt_sigma", "zaru_sigma",
        "nhc_sigma_lateral", "nhc_sigma_vertical", "chi2_gate_3dof",
    ):
        assert hasattr(FilterConfig(), field), f"{field} is not a real FilterConfig field"
        assert re.search(rf"\b{field}\b", TEXT), f"{field} is missing from idr_config"


def test_the_two_calls_that_can_decline_a_measurement_report_it_and_the_others_do_not():
    """`update_gnss` and `update_zaru` are gated (D-001, D-057) and return whether they applied;
    ZUPT and NHC are not, and a caller that expected an `applied` flag from them would silently
    read an uninitialised int."""
    gated = re.search(r"idr_update_gnss\((.*?)\);", TEXT, re.DOTALL).group(1)
    zaru = re.search(r"idr_update_zaru\((.*?)\);", TEXT, re.DOTALL).group(1)
    zupt = re.search(r"idr_update_zupt\((.*?)\);", TEXT, re.DOTALL).group(1)
    nhc = re.search(r"idr_update_nhc\((.*?)\);", TEXT, re.DOTALL).group(1)
    assert "applied" in gated and "applied" in zaru
    assert "applied" not in zupt and "applied" not in nhc

    # And the Python they describe agrees.
    f = InEKF()
    assert isinstance(f.update_gnss(f.state.p, __import__("numpy").eye(3) * 9.0), bool)
    assert isinstance(f.update_zaru(__import__("numpy").zeros(3)), bool)
    assert f.update_zupt() is None


def test_the_architectural_claim_is_written_into_the_contract():
    """"A rejected fix applies nothing" is the whole argument for "seamless transition within
    milliseconds", and it has to survive being reimplemented by someone reading only this file."""
    assert "A REJECTED FIX APPLIES NOTHING" in TEXT
    # Strip the block-comment line prefixes before flattening, or a phrase that happens to
    # wrap across two lines reads as "... to * switch" and the assertion becomes about wrapping.
    flowed = re.sub(r"\s+", " ", re.sub(r"(?m)^\s*\*\s?", "", TEXT))
    assert "There is no branch to switch" in flowed
    assert "no transition latency and no position jump" in flowed


def test_units_frames_and_ownership_are_stated():
    for phrase in ("Units", "Navigation", "Vehicle frame", "Ownership", "Threading"):
        assert phrase in TEXT


@pytest.mark.parametrize("decision", ["D-001", "D-013", "D-022", "D-028", "D-030", "D-043",
                                      "D-048", "D-050", "D-052", "D-055", "D-056", "D-057",
                                      "D-073", "D-076"])
def test_the_header_cites_the_decisions_its_shape_comes_from(decision):
    """The port happens in October, from this file, probably by someone who was not in these
    conversations. A constant with no reason attached is a constant that gets "simplified"."""
    assert decision in TEXT
