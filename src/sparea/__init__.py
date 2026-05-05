from __future__ import annotations

import numpy as np

from . import _pb  # pybind11 C++ extension


def polygon_area(verts) -> float:
    """Area in steradians of a spherical polygon on the unit sphere.

    Args:
        verts: 2-D array-like of vertices, shape (N, 2) or (N, 3).
            (N, 2): each row is (lat, lng) in radians.
            (N, 3): each row is a unit (x, y, z) on the sphere.

    Returns:
        Area in steradians, in `[0, 4π)`.

    Raises:
        ValueError: invalid input shape, antipodal edge, or fewer than
            3 vertices.
    """
    arr = np.ascontiguousarray(verts, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] not in (2, 3):
        raise ValueError(
            "verts must be a 2-D array of shape (N, 2) for lat/lng "
            "or (N, 3) for unit xyz vectors"
        )

    if arr.shape[1] == 2:
        lat = arr[:, 0]
        lng = arr[:, 1]
        cl = np.cos(lat)
        arr = np.ascontiguousarray(
            np.column_stack([cl * np.cos(lng), cl * np.sin(lng), np.sin(lat)])
        )

    return _pb.polygon_area(arr)


__all__ = ["polygon_area"]
