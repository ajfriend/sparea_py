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

## Architecture

The C ABI shim (`src/c_api.zig`) and `build.zig` both live here, not
in the upstream `sparea_zig` package. The split is intentional:

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

You need:

- Zig 0.15.2+ on PATH (`brew install zig` on macOS, see
  https://ziglang.org/learn/getting-started/ otherwise).
- `uv` for Python deps and venv management.

The upstream sparea Zig source is fetched automatically by `zig build`
from the URL pinned in `build.zig.zon` — no separate checkout needed.

```sh
# Step 1: build the shared library and copy it into sparea/.
# Required for editable installs because setuptools' editable mode
# doesn't propagate generated artifacts from the build dir back to
# the source tree.
./scripts/build-lib.sh

# Step 2: install Python deps.
uv sync

# Step 3: run tests.
uv run pytest -q
```

For wheel builds (`uv build` or `cibuildwheel`) the prebuild step
isn't needed — `setup.py`'s `BuildZig` command runs `zig build` and
bundles `libsparea.*` into the wheel automatically.

## Layout

```
.
├── pyproject.toml          — setuptools config, package metadata
├── setup.py                — custom build_py that runs `zig build` and
│                             bundles libsparea.* into the wheel
├── build.zig               — produces libsparea.{dylib,so,dll} from
│                             src/c_api.zig + the upstream sparea module
├── build.zig.zon           — pins the sparea_zig dependency
├── src/
│   └── c_api.zig           — pub export fn sparea_polygon_area_xyz
├── scripts/
│   └── build-lib.sh        — prebuild script for editable installs
├── sparea/
│   └── __init__.py         — ctypes wrapper, exposes polygon_area +
│                             SpareaError, AntipodalEdgeError,
│                             TooFewVerticesError
└── tests/
    └── test_bindings.py
```

After a successful build, `sparea/libsparea.{dylib,so,dll}` will exist —
that's the bundled artifact that ships in wheels. It's `.gitignore`d.

## Bumping the sparea_zig version

```sh
zig fetch --save=sparea \
  https://github.com/ajfriend/sparea_zig/archive/refs/tags/vX.Y.Z.tar.gz
```

That rewrites the `dependencies.sparea` entry in `build.zig.zon` with
the new URL and content hash.
