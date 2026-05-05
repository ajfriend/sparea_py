from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from cffi import FFI


class SpareaError(ValueError):
    """Base class for sparea errors propagated from the C ABI."""


class AntipodalEdgeError(SpareaError):
    """A polygon edge connects (near-)antipodal vertices, leaving the
    geodesic between them ambiguous and the polygon geometrically
    ill-defined. Insert an intermediate vertex on the great-circle arc
    to disambiguate."""


class TooFewVerticesError(SpareaError):
    """The polygon has fewer than 3 vertices."""


# C ABI declarations (must match src/zig/c_api.zig).
_ffi = FFI()
_ffi.cdef("""
    int sparea_polygon_area_xyz(
        const double *xs, const double *ys, const double *zs,
        size_t n, double *out
    );
""")

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


def _load_lib():
    here = Path(__file__).parent
    suffix = {"darwin": ".dylib", "win32": ".dll"}.get(sys.platform, ".so")
    return _ffi.dlopen(str(here / f"libsparea{suffix}"))


_lib = _load_lib()


def polygon_area(verts) -> float:
    """Area in steradians of a spherical polygon on the unit sphere.

    Args:
        verts: 2-D array-like of vertices, shape (N, 2) or (N, 3).
            (N, 2): each row is (lat, lng) in radians.
            (N, 3): each row is a unit (x, y, z) on the sphere.

    Returns:
        Area in steradians, in `[0, 4π)`.

    Raises:
        AntipodalEdgeError, TooFewVerticesError, ValueError.
    """
    arr = np.ascontiguousarray(verts, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] not in (2, 3):
        raise ValueError(
            "verts must be a 2-D array of shape (N, 2) or (N, 3)"
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

    out = _ffi.new("double*")
    err = _lib.sparea_polygon_area_xyz(
        _ffi.from_buffer("double[]", xs),
        _ffi.from_buffer("double[]", ys),
        _ffi.from_buffer("double[]", zs),
        xs.size,
        out,
    )
    if err == _SPAREA_OK:
        return out[0]
    cls = _ERROR_CLASSES.get(err, SpareaError)
    msg = _ERROR_MESSAGES.get(err, f"unknown error code: {err}")
    raise cls(msg)


__all__ = [
    "polygon_area",
    "SpareaError",
    "AntipodalEdgeError",
    "TooFewVerticesError",
]
