# sparea (Python)

Python bindings for [sparea_zig](https://github.com/ajfriend/sparea_zig), a
Zig library for computing the area of spherical polygons.

## What this package is

A thin `ctypes` wrapper around a small C ABI shim that calls into the
upstream sparea Zig package. The Python side accepts a polygon as a
list of `(lat, lng)` pairs in radians, converts each vertex to a unit
3-vector with NumPy, and hands the parallel `xs`/`ys`/`zs` buffers to
the Zig kernel.

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

## Architecture

The C ABI shim (`src/zig/c_api.zig`) and `src/zig/build.zig` both
live here, not in the upstream `sparea_zig` package. The split is
intentional:

- **`sparea_zig` (upstream)**: pure Zig algorithm library. Exports a
  `Module` for other Zig code; no C ABI, no shared library.
- **`sparea_py` (this repo)**: depends on `sparea_zig` via
  `build.zig.zon`, wraps it in a tiny C ABI
  (`sparea_polygon_area_xyz`), builds a shared library, and
  ctypes-binds it from Python.

The shim takes parallel `xs`/`ys`/`zs` `f64` arrays (the natural
NumPy layout), reconstructs a `[]Vec3` on the Zig side, and calls
`sparea.polygon_area(f64, verts)`.

## Building locally

For development on this repo (rather than installing from git), use
the justfile:

```sh
just reinstall  # uv cache clean sparea + uv sync --reinstall-package sparea
just test       # reinstall + uv run pytest
just wheel      # uv build
```

The `zig build` step is wired into the hatchling build backend via
`hatch_build.py` (`[tool.hatch.build.hooks.custom]`), so every install
path — `uv sync`, `uv build`, `pip wheel .`, cibuildwheel — triggers
it automatically. Local dev uses non-editable installs
(`UV_NO_EDITABLE=1` is set at the top of the justfile) so the dylib
lands in site-packages alongside `sparea/__init__.py`, where the
ctypes loader expects it. `just test` chains through `just reinstall`
which clears uv's wheel cache and force-reinstalls sparea, so a stale
zig artifact never silently survives a test run.

For cibuildwheel, install Zig once per build image via
`CIBW_BEFORE_ALL` (e.g. `pip install ziglang` or download from
ziglang.org); the hook handles the rest.

## Layout

```
.
├── pyproject.toml          — hatchling config, package metadata
├── justfile                — build / sync / test / wheel / bump / clean
├── src/
│   ├── hatch_build.py      — hatchling hook: runs `zig build`,
│   │                         stages libsparea.* into src/sparea/
│   ├── sparea/
│   │   └── __init__.py     — ctypes wrapper, exposes polygon_area +
│   │                         SpareaError, AntipodalEdgeError,
│   │                         TooFewVerticesError
│   └── zig/
│       ├── build.zig       — produces libsparea.{dylib,so,dll}
│       ├── build.zig.zon   — pins the sparea_zig dependency
│       └── c_api.zig       — pub export fn sparea_polygon_area_xyz
└── tests/
    └── test_bindings.py
```

After a successful build, `src/sparea/libsparea.{dylib,so,dll}` will
exist — that's the bundled artifact that ships in wheels. It's
`.gitignore`d.

## Bumping the sparea_zig version

```sh
just bump vX.Y.Z
```

That rewrites the `dependencies.sparea` entry in
`src/zig/build.zig.zon` with the new URL and content hash.
