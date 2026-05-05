from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import numpy as np
from numpy.ctypeslib import ndpointer


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


# C error codes — must match src/zig/c_api.zig.
_ERRORS: dict[int, tuple[type[SpareaError], str]] = {
    1: (
        AntipodalEdgeError,
        "polygon contains an antipodal or near-antipodal edge "
        "(consecutive vertices ~180° apart, geodesic ambiguous); "
        "insert an intermediate vertex to disambiguate",
    ),
    2: (
        TooFewVerticesError,
        "polygon needs at least 3 vertices to bound a region",
    ),
    3: (
        SpareaError,
        "out of memory allocating vertex buffer in libsparea",
    ),
}


def _load_lib() -> ctypes.CDLL:
    here = Path(__file__).parent
    suffix = {"darwin": ".dylib", "win32": ".dll"}.get(sys.platform, ".so")
    return ctypes.CDLL(str(here / f"libsparea{suffix}"))


_lib = _load_lib()
# Pass numpy arrays directly into the call — ndpointer validates the
# dtype/ndim/contiguity and hands the C side the raw buffer pointer.
_arr1d = ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS")
_lib.sparea_polygon_area_xyz.argtypes = [
    _arr1d, _arr1d, _arr1d, ctypes.c_size_t, ctypes.POINTER(ctypes.c_double),
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
        lat, lng = arr[:, 0], arr[:, 1]
        cl = np.cos(lat)
        xs = np.ascontiguousarray(cl * np.cos(lng))
        ys = np.ascontiguousarray(cl * np.sin(lng))
        zs = np.ascontiguousarray(np.sin(lat))
    else:
        xs = np.ascontiguousarray(arr[:, 0])
        ys = np.ascontiguousarray(arr[:, 1])
        zs = np.ascontiguousarray(arr[:, 2])

    out = ctypes.c_double()
    err = _lib.sparea_polygon_area_xyz(xs, ys, zs, xs.size, ctypes.byref(out))
    if err == 0:
        return out.value
    cls, msg = _ERRORS.get(err, (SpareaError, f"unknown error code: {err}"))
    raise cls(msg)


__all__ = [
    "polygon_area",
    "SpareaError",
    "AntipodalEdgeError",
    "TooFewVerticesError",
]
