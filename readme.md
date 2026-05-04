# sparea: Spherical Polygon Area

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

Wheels aren't on PyPI yet, but you can install straight from the git
repo with either pip or uv:

```sh
# regular pip
pip install git+https://github.com/ajfriend/sparea_py.git

# uv (project add)
uv add git+https://github.com/ajfriend/sparea_py.git

# uv (one-off in a venv)
uv pip install git+https://github.com/ajfriend/sparea_py.git
```

The Zig toolchain is pulled in automatically via the `ziglang` PyPI
wheel listed in `[build-system].requires` — no host-level Zig install
needed. The hatchling build hook (`src/hatch_build.py`) compiles
`libsparea.{dylib,so,dll}` and bundles it into the wheel before pip
installs it. The upstream `sparea_zig` source is fetched over the
network from the URL pinned in `src/zig/build.zig.zon`.

See [`dev.md`](dev.md) for architecture, layout, and contributor
notes.
