# cython: language_level=3
"""Prototype Cython binding for sparea.

Compiled by meson (driven by meson-python); links against the Zig
static archive libsparea.{a,lib}. Exposed as `sparea._cy`.

The Windows sincos shim that used to live here is now in
sparea_zig itself (windows-msvc-only export, gated at @import time)
since v0.3.0 — see sparea_zig#1.
"""

cdef extern from *:
    """
    int sparea_polygon_area_vec3(const double *verts, size_t n, double *out);
    """
    int sparea_polygon_area_vec3(const double *verts, size_t n, double *out)


def polygon_area(double[:, ::1] verts not None) -> float:
    """Area in steradians of a spherical polygon. `verts` is a
    contiguous (N, 3) numpy array of unit xyz vectors."""
    if verts.shape[1] != 3:
        raise ValueError("verts must be a 2-D array of shape (N, 3)")

    cdef double out
    cdef int err = sparea_polygon_area_vec3(&verts[0, 0], verts.shape[0], &out)

    if err == 0:
        return out
    if err == 1:
        raise ValueError(
            "polygon contains an antipodal or near-antipodal edge "
            "(consecutive vertices ~180° apart)"
        )
    if err == 2:
        raise ValueError("polygon needs at least 3 vertices to bound a region")
    if err == 3:
        raise MemoryError("out of memory allocating vertex buffer in libsparea")
    raise ValueError(f"sparea: unknown error code {err}")
