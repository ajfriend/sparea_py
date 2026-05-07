from __future__ import annotations

import numpy as np

from . import _cy  # Cython extension

_GEO_COLS = {'latlng': 2, 'vec3': 3}
_ALGO = {'auto': 0, 'cross': 1, 'angle': 2}


def area(
    verts,
    *,
    geo: str = 'latlng',
    algo: str = 'auto',
    signed: bool = False,
) -> float:
    """Area in steradians of a spherical polygon on the unit sphere.

    Args:
        verts: 2-D array-like of vertices. Anything numpy can normalize
            to a contiguous float64 matrix (list of tuples, list of
            lists, ndarray, memoryview, ...) is accepted. The number
            of columns must match `geo`: 2 for `'latlng'`, 3 for
            `'vec3'`.
        geo: input convention.
            `'latlng'` (default): each row is `(lat, lng)` in radians.
            `'vec3'`: each row is a unit `(x, y, z)` on the sphere.
        algo: kernel selection.
            `'auto'` (default): hemisphere-contained polygons take the
                cross-product centroid-fan path; others fall back to
                the per-edge angle formula.
            `'cross'`: force the cross-product kernel.
            `'angle'`: force the angle-formula kernel.
        signed: output sign convention.
            `False` (default): fold the result into `[0, 4π)`.
                Reversing the vertex order yields the complementary
                region (`4π − interior`).
            `True`: return the raw signed kernel value (positive for
                CCW-from-outside, negative otherwise).

    Returns:
        Area in steradians. In `[0, 4π)` when `signed=False`; signed
        kernel value when `signed=True`.

    Raises:
        ValueError: invalid `geo` / `algo`, mismatched shape,
            antipodal edge, or fewer than 3 vertices.
    """
    if geo not in _GEO_COLS:
        raise ValueError(f"geo must be 'latlng' or 'vec3', got {geo!r}")
    if algo not in _ALGO:
        raise ValueError(
            f"algo must be 'auto', 'cross', or 'angle', got {algo!r}"
        )

    arr = np.ascontiguousarray(verts, dtype=np.float64)
    cols = _GEO_COLS[geo]
    if arr.ndim != 2 or arr.shape[1] != cols:
        raise ValueError(
            f'verts must be a 2-D array with shape (N, {cols}) for '
            f'geo={geo!r}, got shape {arr.shape}'
        )

    if geo == 'latlng':
        lat = arr[:, 0]
        lng = arr[:, 1]
        cl = np.cos(lat)
        # column_stack returns a fresh C-contiguous (N, 3) f64.
        arr = np.column_stack([cl * np.cos(lng), cl * np.sin(lng), np.sin(lat)])

    return _cy.area(arr, _ALGO[algo], bool(signed))


__all__ = ['area']
