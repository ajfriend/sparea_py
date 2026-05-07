# cython: language_level=3
"""Cython binding for sparea — internal; called from `sparea.area`.

Compiled by meson (driven by meson-python); links against the Zig
static archive libsparea.{a,lib}. Exposed as `sparea._cy`.
"""

cdef extern from *:
    """
    int sparea_polygon_area_vec3(const double *verts, size_t n, int algo, int signed_, double *out);
    """
    int sparea_polygon_area_vec3(const double *verts, size_t n, int algo, int signed_, double *out)


def area(double[:, ::1] verts not None, int algo, int signed) -> float:
    if verts.shape[1] != 3:
        raise ValueError('verts must be a 2-D array of shape (N, 3)')

    cdef double out
    cdef int err = sparea_polygon_area_vec3(&verts[0, 0], verts.shape[0], algo, signed, &out)

    if err == 0:
        return out
    if err == 1:
        raise ValueError(
            'polygon contains an antipodal or near-antipodal edge '
            '(consecutive vertices ~180° apart)'
        )
    if err == 2:
        raise ValueError('polygon needs at least 3 vertices to bound a region')
    if err == 3:
        raise ValueError(f'sparea: bad algo code {algo}')
    raise ValueError(f'sparea: unknown error code {err}')
