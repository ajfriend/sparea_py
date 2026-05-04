# sparea: Spherical Polygon Area

Python bindings for [sparea_zig](https://github.com/ajfriend/sparea_zig), a
Zig library for computing the area of spherical polygons.

```python
import math
from sparea import polygon_area

# Octant triangle: equator at lng=0, equator at lng=π/2, north pole.
verts = [
    (0.0,         0.0),
    (0.0,         math.pi / 2),
    (math.pi / 2, 0.0),
]
polygon_area(verts)   # ≈ pi / 2
```

The result is in steradians, in `[0, 4π)`. Reverse the vertex order
to get the complementary region (`4π − interior`).

## Installing

Wheels aren't on PyPI yet, but you can install straight from the git
repo with either pip or uv. You'll need a Zig 0.15.2+ compiler on
PATH (`brew install zig` on macOS, see
[ziglang.org](https://ziglang.org/learn/getting-started/) otherwise).
The build pulls the `sparea_zig` source over the network from the URL
pinned in `src/zig/build.zig.zon`.

```sh
# regular pip
pip install git+https://github.com/ajfriend/sparea_py.git

# uv (project add)
uv add git+https://github.com/ajfriend/sparea_py.git

# uv (one-off in a venv)
uv pip install git+https://github.com/ajfriend/sparea_py.git
```

Both code paths run the same hatchling build hook
(`src/hatch_build.py`), which shells out to `zig build` to compile
`libsparea.{dylib,so,dll}` and bundles it into the wheel before pip
installs it.

See [`dev.md`](dev.md) for architecture, layout, and contributor
notes.
