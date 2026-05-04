from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import numpy as np


class SpareaError(ValueError):
    """Base class for sparea errors propagated from the C ABI."""


class AntipodalEdgeError(SpareaError):
    """A polygon edge connects (near-)antipodal vertices, leaving the
    geodesic between them ambiguous and the polygon geometrically
    ill-defined. Insert an intermediate vertex on the great-circle arc
    to disambiguate."""


class TooFewVerticesError(SpareaError):
    """The polygon has fewer than 3 vertices. A spherical polygon
    needs at least 3 vertices to bound a region."""


# C error codes — must match sparea_py/src/c_api.zig
_SPAREA_OK = 0
_SPAREA_ANTIPODAL_EDGE = 1
_SPAREA_TOO_FEW_VERTICES = 2
_SPAREA_OOM = 3

_ERROR_CLASSES: dict[int, type[SpareaError]] = {
    _SPAREA_ANTIPODAL_EDGE: AntipodalEdgeError,
    _SPAREA_TOO_FEW_VERTICES: TooFewVerticesError,
}

_ERROR_MESSAGES: dict[int, str] = {
    _SPAREA_ANTIPODAL_EDGE: (
        "polygon contains an antipodal or near-antipodal edge "
        "(consecutive vertices ~180° apart, geodesic ambiguous); "
        "insert an intermediate vertex to disambiguate"
    ),
    _SPAREA_TOO_FEW_VERTICES: (
        "polygon needs at least 3 vertices to bound a region"
    ),
    _SPAREA_OOM: "out of memory allocating vertex buffer in libsparea",
}


def _load_lib() -> ctypes.CDLL:
    here = Path(__file__).parent
    suffix = {"darwin": ".dylib", "win32": ".dll"}.get(sys.platform, ".so")
    return ctypes.CDLL(str(here / f"libsparea{suffix}"))


_lib = _load_lib()
_lib.sparea_polygon_area_xyz.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_double),
]
_lib.sparea_polygon_area_xyz.restype = ctypes.c_int


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
        AntipodalEdgeError: any consecutive vertex pair is
            (near-)antipodal — the geodesic between them is ambiguous
            and the polygon is geometrically ill-defined.
        TooFewVerticesError: the polygon has fewer than 3 vertices.
        ValueError: input shape is not (N, 2) or (N, 3).
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
        xs = np.ascontiguousarray(cl * np.cos(lng))
        ys = np.ascontiguousarray(cl * np.sin(lng))
        zs = np.ascontiguousarray(np.sin(lat))
    else:
        xs = np.ascontiguousarray(arr[:, 0])
        ys = np.ascontiguousarray(arr[:, 1])
        zs = np.ascontiguousarray(arr[:, 2])

    out = ctypes.c_double()
    err = _lib.sparea_polygon_area_xyz(
        xs.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ys.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        zs.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        xs.size,
        ctypes.byref(out),
    )
    if err == _SPAREA_OK:
        return out.value
    cls = _ERROR_CLASSES.get(err, SpareaError)
    msg = _ERROR_MESSAGES.get(err, f"unknown error code: {err}")
    raise cls(msg)


__all__ = [
    "polygon_area",
    "SpareaError",
    "AntipodalEdgeError",
    "TooFewVerticesError",
]
