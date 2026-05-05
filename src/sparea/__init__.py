from __future__ import annotations

import numpy as np

from . import _nb  # nanobind C++ extension


def polygon_area(verts) -> float:
    """Area in steradians of a spherical polygon on the unit sphere.

    Args:
        verts: 2-D array-like of vertices, shape (N, 2) or (N, 3).
            - shape (N, 2): each row is a `(lat, lng)` pair in radians.
            - shape (N, 3): each row is a unit 3-vector `(x, y, z)` on
              the sphere; caller is responsible for normalization.
            Vertices traverse the polygon boundary; CCW as viewed from
            outside the sphere yields the interior area, CW yields the
            complement (4π − interior). At least 3 vertices required.

    Returns:
        Area in steradians, in `[0, 4π)`.

    Raises:
        ValueError: invalid input shape, antipodal edge, or fewer than
            3 vertices. (The C++ binding maps each error condition to
            a distinct ValueError message.)
    """
    arr = np.ascontiguousarray(verts, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] not in (2, 3):
        raise ValueError(
            "verts must be a 2-D array of shape (N, 2) for lat/lng "
            "or (N, 3) for unit xyz vectors"
        )

    if arr.shape[1] == 2:
        # lat/lng → unit xyz, then a contiguous copy for the C++ binding.
        lat = arr[:, 0]
        lng = arr[:, 1]
        cl = np.cos(lat)
        arr = np.ascontiguousarray(
            np.column_stack([cl * np.cos(lng), cl * np.sin(lng), np.sin(lat)])
        )

    return _nb.polygon_area(arr)


__all__ = ["polygon_area"]
