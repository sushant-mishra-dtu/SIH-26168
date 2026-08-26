"""Geodesy tests. Ground truth depends on these, so they check against published values."""

from __future__ import annotations

import numpy as np
import pytest

from idr.geo import geodetic_to_ned, path_length, vincenty_inverse, wrap_to_pi


def test_coincident_points_are_zero():
    assert vincenty_inverse(51.5, -0.12, 51.5, -0.12) == 0.0


def _dms(deg: float, minute: float, sec: float, negative: bool = False) -> float:
    """Degrees-minutes-seconds to decimal degrees.

    The canonical test coordinates are published in DMS. Converting here rather than pasting
    rounded decimals keeps the reference exact -- a 1e-6 deg rounding is ~0.1 m, which is the
    same order as the tolerance we are asserting.
    """
    value = deg + minute / 60 + sec / 3600
    return -value if negative else value


def test_known_geodesic_distance():
    """Vincenty's own worked example: Flinders Peak to Buninyong, Australia = 54,972.271 m."""
    lat1 = _dms(37, 57, 3.72030, negative=True)  # Flinders Peak
    lon1 = _dms(144, 25, 29.52440)
    lat2 = _dms(37, 39, 10.15610, negative=True)  # Buninyong
    lon2 = _dms(143, 55, 35.38390)
    assert vincenty_inverse(lat1, lon1, lat2, lon2) == pytest.approx(54972.271, abs=0.01)


def test_one_degree_of_latitude_is_about_111km():
    d = vincenty_inverse(0.0, 0.0, 1.0, 0.0)
    assert 110_500 < d < 111_000


def test_symmetry():
    a = vincenty_inverse(28.6139, 77.2090, 28.7041, 77.1025)  # Delhi
    b = vincenty_inverse(28.7041, 77.1025, 28.6139, 77.2090)
    assert a == pytest.approx(b, abs=1e-6)


def test_path_length_sums_segments_not_endpoints():
    """A there-and-back path has ~zero displacement but nonzero distance travelled.

    This is the distinction that matters for drift-%: the denominator is distance travelled, so a
    roundabout must not report a near-zero denominator and an infinite drift.
    """
    lat = np.array([28.60, 28.61, 28.60])
    lon = np.array([77.20, 77.20, 77.20])
    total = path_length(lat, lon)
    endpoint = vincenty_inverse(lat[0], lon[0], lat[-1], lon[-1])
    assert endpoint == pytest.approx(0.0, abs=1e-6)
    assert total > 2000


def test_path_length_degenerate_inputs():
    assert path_length(np.array([28.6]), np.array([77.2])) == 0.0
    with pytest.raises(ValueError, match="shape mismatch"):
        path_length(np.array([28.6, 28.7]), np.array([77.2]))


def test_ned_axes_point_the_right_way():
    """North is +0, east is +1. A sign error here mirrors every trajectory plot."""
    ned = geodetic_to_ned(np.array([28.61]), np.array([77.20]), 28.60, 77.20)
    assert ned[0, 0] > 0  # moved north
    assert ned[0, 1] == pytest.approx(0.0, abs=1e-6)

    ned = geodetic_to_ned(np.array([28.60]), np.array([77.21]), 28.60, 77.20)
    assert ned[0, 0] == pytest.approx(0.0, abs=1e-6)
    assert ned[0, 1] > 0  # moved east


@pytest.mark.parametrize(
    ("angle", "expected"),
    [(0.0, 0.0), (np.pi, np.pi), (-np.pi, np.pi), (3 * np.pi, np.pi), (2 * np.pi + 0.1, 0.1)],
)
def test_wrap_to_pi_endpoints(angle, expected):
    assert wrap_to_pi(angle) == pytest.approx(expected, abs=1e-12)


def test_wrap_to_pi_vectorised():
    out = wrap_to_pi(np.array([0.0, 3 * np.pi, -3 * np.pi]))
    assert out.shape == (3,)
    assert out == pytest.approx([0.0, np.pi, np.pi])
