# sparea: Spherical Polygon Area

[![PyPI](https://img.shields.io/pypi/v/sparea.svg)](https://pypi.org/project/sparea/)
[![Python](https://img.shields.io/pypi/pyversions/sparea.svg)](https://pypi.org/project/sparea/)
[![License](https://img.shields.io/pypi/l/sparea.svg)](https://github.com/ajfriend/sparea_py/blob/main/license)
[![Tests](https://github.com/ajfriend/sparea_py/actions/workflows/test.yml/badge.svg)](https://github.com/ajfriend/sparea_py/actions/workflows/test.yml)
[![Wheels](https://github.com/ajfriend/sparea_py/actions/workflows/wheels.yml/badge.svg)](https://github.com/ajfriend/sparea_py/actions/workflows/wheels.yml)

Python bindings for [sparea_zig](https://github.com/ajfriend/sparea_zig), a
Zig library for computing the area of spherical polygons.

```python
import sparea as sp

# Octant triangle: equator at lng=0, equator at lng=90°, north pole.
sp.area([
    (0.0,  0.0),
    (0.0, 90.0),
    (90.0, 0.0),
])  # ≈ pi / 2

# Same polygon expressed as unit (x, y, z) vectors.
sp.area([
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
], geo='vec3')  # ≈ pi / 2
```

`sp.area` accepts three keyword arguments:

- `geo`: input convention.
  - `'latlng'` (default) and `'latlng_deg'` — each row is
    `(lat, lng)` in **degrees** (matching h3's convention).
  - `'latlng_rad'` — each row is `(lat, lng)` in radians.
  - `'vec3'` — each row is a unit `(x, y, z)`.

  The number of input columns must match (2 for the `latlng` family,
  3 for `vec3`).
- `algo`: kernel selection. `'auto'` (default) dispatches between a
  cross-product centroid-fan path (for hemisphere-contained polygons)
  and a per-edge angle formula. `'cross'` and `'angle'` force the
  named kernel.
- `signed`: output sign convention. `False` (default) folds the
  result into `[0, 4π)` — reversing the vertex order yields the
  complementary region (`4π − interior`). `True` returns the raw
  signed kernel value (positive for CCW-from-outside, negative
  otherwise).

## Installing

```sh
pip install sparea
# or
uv add sparea
```

Wheels are published for Python 3.11–3.14 across Linux (x86_64,
aarch64, manylinux + musllinux), macOS arm64, and Windows AMD64. No
host-level Zig install needed.

To install the unreleased main branch instead, point pip/uv at the
git URL:

```sh
pip install git+https://github.com/ajfriend/sparea_py.git
uv pip install git+https://github.com/ajfriend/sparea_py.git
```

That path triggers a source build: the hatchling hook
(`src/hatch_build.py`) pulls the Zig toolchain from the `ziglang`
PyPI wheel, compiles `libsparea.{dylib,so,dll}`, and bundles it into
the wheel before pip installs it. The upstream `sparea_zig` source
is fetched over the network from the URL pinned in
`src/zig/build.zig.zon`.

See [`dev.md`](dev.md) for architecture, layout, and contributor
notes.
