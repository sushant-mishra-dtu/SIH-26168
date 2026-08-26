"""Geodesy. Ground truth lives here, so this module is deliberately boring and well tested.

IO-VNBD computes true displacement between GNSS fixes with Vincenty's inverse formula on the
WGS-84 ellipsoid. We reproduce that exactly rather than using a haversine approximation -- over a
5.6 km sequence the difference between the two is metres, and metres are the unit we are graded in.
"""

from __future__ import annotations

import numpy as np

# WGS-84
_A = 6378137.0  # semi-major axis, m
_F = 1 / 298.257223563  # flattening
_B = (1 - _F) * _A  # semi-minor axis, m


def vincenty_inverse(
    lat1: float, lon1: float, lat2: float, lon2: float, *, max_iter: int = 200, tol: float = 1e-12
) -> float:
    """Geodesic distance in metres between two WGS-84 points.

    Returns 0.0 for coincident points. Raises if the solution fails to converge, which happens for
    near-antipodal points -- a condition that cannot arise in this dataset and therefore indicates
    corrupt input rather than a numerical edge case worth papering over.
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)

    u1 = np.arctan((1 - _F) * np.tan(phi1))
    u2 = np.arctan((1 - _F) * np.tan(phi2))
    sin_u1, cos_u1 = np.sin(u1), np.cos(u1)
    sin_u2, cos_u2 = np.sin(u2), np.cos(u2)

    lam = dl
    for _ in range(max_iter):
        sin_lam, cos_lam = np.sin(lam), np.cos(lam)
        sin_sigma = np.hypot(cos_u2 * sin_lam, cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lam)
        if sin_sigma == 0:
            return 0.0
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = np.arctan2(sin_sigma, cos_sigma)
        sin_alpha = cos_u1 * cos_u2 * sin_lam / sin_sigma
        cos_sq_alpha = 1 - sin_alpha**2
        # cos(2*sigma_m) is 0 on equatorial lines, where cos_sq_alpha is 0.
        cos_2sm = 0.0 if cos_sq_alpha == 0 else cos_sigma - 2 * sin_u1 * sin_u2 / cos_sq_alpha
        c = _F / 16 * cos_sq_alpha * (4 + _F * (4 - 3 * cos_sq_alpha))
        lam_prev = lam
        lam = dl + (1 - c) * _F * sin_alpha * (
            sigma + c * sin_sigma * (cos_2sm + c * cos_sigma * (-1 + 2 * cos_2sm**2))
        )
        if abs(lam - lam_prev) < tol:
            break
    else:
        raise ValueError(
            f"Vincenty failed to converge for ({lat1}, {lon1}) -> ({lat2}, {lon2}). "
            "Near-antipodal or corrupt coordinates."
        )

    u_sq = cos_sq_alpha * (_A**2 - _B**2) / _B**2
    a_ = 1 + u_sq / 16384 * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
    b_ = u_sq / 1024 * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
    d_sigma = (
        b_
        * sin_sigma
        * (
            cos_2sm
            + b_
            / 4
            * (
                cos_sigma * (-1 + 2 * cos_2sm**2)
                - b_ / 6 * cos_2sm * (-3 + 4 * sin_sigma**2) * (-3 + 4 * cos_2sm**2)
            )
        )
    )
    return float(_B * a_ * (sigma - d_sigma))


def path_length(lat: np.ndarray, lon: np.ndarray) -> float:
    """Cumulative geodesic path length in metres along a fix sequence.

    This is the denominator ``L`` in the drift-% metric that PS 26168 grades, so it is the
    ground-truth distance actually travelled -- not the straight-line displacement between the
    endpoints. On a roundabout those differ by nearly the whole path.
    """
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    if lat.shape != lon.shape:
        raise ValueError(f"lat/lon shape mismatch: {lat.shape} vs {lon.shape}")
    if lat.size < 2:
        return 0.0
    return float(
        sum(
            vincenty_inverse(lat[i], lon[i], lat[i + 1], lon[i + 1])
            for i in range(lat.size - 1)
        )
    )


def geodetic_to_ned(
    lat: np.ndarray, lon: np.ndarray, lat0: float, lon0: float
) -> np.ndarray:
    """Local NED (north, east) offsets in metres relative to an origin fix.

    Small-angle tangent-plane projection, adequate over the few-km spans of a single outage and
    consistent with the dataset's 2-D yaw-only convention. Returns shape ``(n, 2)`` as
    ``[north, east]``. Down is dropped -- we track 2-D horizontal, per EVALUATION.md section 2.
    """
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    phi0 = np.radians(lat0)
    m_per_deg_lat = 111132.92 - 559.82 * np.cos(2 * phi0) + 1.175 * np.cos(4 * phi0)
    m_per_deg_lon = 111412.84 * np.cos(phi0) - 93.5 * np.cos(3 * phi0)
    north = (lat - lat0) * m_per_deg_lat
    east = (lon - lon0) * m_per_deg_lon
    return np.column_stack([north, east])


def wrap_to_pi(angle: np.ndarray | float) -> np.ndarray | float:
    """Wrap an angle in radians to (-pi, pi].

    Yaw error is meaningless unwrapped: an estimate 0.01 rad past north must read as +0.01, not
    -6.27. Every yaw comparison in this repo goes through here.
    """
    wrapped = (np.asarray(angle, dtype=float) + np.pi) % (2 * np.pi) - np.pi
    # (-pi, pi] rather than [-pi, pi): map the -pi endpoint up.
    wrapped = np.where(wrapped == -np.pi, np.pi, wrapped)
    return float(wrapped) if np.isscalar(angle) or wrapped.ndim == 0 else wrapped
