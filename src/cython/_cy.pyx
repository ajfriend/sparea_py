# cython: language_level=3
"""Prototype Cython binding for sparea.

Compiled by meson (driven by meson-python); links against the Zig
static archive libsparea.{a,lib}. Exposed as `sparea._cy`.
"""

# Windows sincos shim — LLVM auto-fuses adjacent sin/cos in Zig's
# optimized object code into a sincos() call, which MSVC's libm
# doesn't ship. We route the shim's sin/cos through volatile function
# pointers so MSVC's link-time codegen can't re-fuse them into a
# recursive sincos() call.
cdef extern from *:
    """
    #ifdef _WIN32
    #include <math.h>
    typedef double (*sparea_unary_d)(double);
    static volatile sparea_unary_d sparea_sin_fn = sin;
    static volatile sparea_unary_d sparea_cos_fn = cos;
    void sincos(double x, double *s, double *c) {
        *s = sparea_sin_fn(x);
        *c = sparea_cos_fn(x);
    }
    #endif
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
