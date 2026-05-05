# sparea: Spherical Polygon Area

[![PyPI](https://img.shields.io/pypi/v/sparea.svg)](https://pypi.org/project/sparea/)
[![Python](https://img.shields.io/pypi/pyversions/sparea.svg)](https://pypi.org/project/sparea/)
[![License](https://img.shields.io/pypi/l/sparea.svg)](https://github.com/ajfriend/sparea_py/blob/main/license)
[![Tests](https://github.com/ajfriend/sparea_py/actions/workflows/test.yml/badge.svg)](https://github.com/ajfriend/sparea_py/actions/workflows/test.yml)
[![Wheels](https://github.com/ajfriend/sparea_py/actions/workflows/wheels.yml/badge.svg)](https://github.com/ajfriend/sparea_py/actions/workflows/wheels.yml)

Python bindings for [sparea_zig](https://github.com/ajfriend/sparea_zig), a
Zig library for computing the area of spherical polygons.

```python
import math
from sparea import polygon_area

# Octant triangle: equator at lng=0, equator at lng=π/2, north pole.
# Vertices may be either (lat, lng) in radians or unit (x, y, z).
polygon_area([
    (0.0,         0.0),
    (0.0,         math.pi / 2),
    (math.pi / 2, 0.0),
])  # ≈ pi / 2

polygon_area([
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
])  # ≈ pi / 2
```

The result is in steradians, in `[0, 4π)`. Reverse the vertex order
to get the complementary region (`4π − interior`).

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
