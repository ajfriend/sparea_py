# Development notes

Internal-facing notes on architecture, build mechanics, and
contributor workflows for `sparea_py`.

## Architecture

A thin `ctypes` wrapper around a small C ABI shim that calls into the
upstream `sparea_zig` package. The Python side accepts a polygon as a
list of `(lat, lng)` pairs in radians, converts each vertex to a unit
3-vector with NumPy, and hands the parallel `xs`/`ys`/`zs` buffers to
the Zig kernel.

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

## Layout

```
.
├── pyproject.toml          — hatchling config, package metadata
├── justfile                — reinstall / test / wheel / clean / purge
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

## Building and testing locally

```sh
just reinstall  # uv cache clean sparea + uv sync --reinstall-package sparea
just test       # reinstall + uv run pytest
just wheel      # uv build
```

The `zig build` step is wired into the hatchling build backend via
`src/hatch_build.py` (`[tool.hatch.build.targets.wheel.hooks.custom]`),
so every install path — `uv sync`, `uv build`, `pip wheel .`,
cibuildwheel — triggers it automatically. The Zig toolchain itself
is a build-system dep (`ziglang>=0.15.2` in
`[build-system].requires`), so no host-level Zig install is needed
anywhere. Local dev uses non-editable installs (`UV_NO_EDITABLE=1`
at the top of the justfile) so the dylib lands in site-packages
alongside `sparea/__init__.py`, where the ctypes loader expects it.
`just test` chains through `just reinstall`, which clears uv's wheel
cache and force-reinstalls sparea — so a stale zig artifact never
silently survives a test run.

## Bumping the sparea_zig version

The upstream Zig package is pinned in `src/zig/build.zig.zon` by URL
+ content hash. To bump:

```sh
cd src/zig && zig fetch --save=sparea \
  https://github.com/ajfriend/sparea_zig/archive/refs/tags/vX.Y.Z.tar.gz
```

That rewrites the `dependencies.sparea` entry with the new URL and
hash. Re-run `just test` to confirm the new version still works.

## Cutting a release

Trusted-Publisher OIDC is wired up — no API tokens involved. To
publish a new version to PyPI from the GitHub web UI:

1. **Bump the version** in `pyproject.toml` (`project.version`).
   Commit + push to `main`. Wait for `test` and `wheels` to go green.

2. **Create a tag and a release in one go.**
   - Go to https://github.com/ajfriend/sparea_py/releases →
     **Draft a new release**.
   - **Choose a tag**: type `vX.Y.Z` (matching the `pyproject.toml`
     version) and pick **"Create new tag: vX.Y.Z on publish"**.
   - **Target**: leave on `main`.
   - **Release title**: `vX.Y.Z` (or anything descriptive).
   - Click **Generate release notes** — fills in commit history.
   - Leave **Set as a pre-release** unchecked for normal releases.
   - **Publish release**.

3. **Watch the publish.** The release-publish event triggers the
   `wheels` workflow on https://github.com/ajfriend/sparea_py/actions.
   It rebuilds + tests every wheel (sdist + 35 wheels), then the
   `to-pypi` job downloads them all and pushes to PyPI via OIDC.
   - If the `pypi` environment has required reviewers configured,
     the `to-pypi` job pauses with **"Waiting on review"** — open
     the workflow run and click **Review deployments** → **Approve
     and deploy**.

4. **Verify.** Once `to-pypi` is green, the version shows up on
   https://pypi.org/project/sparea/ within a minute. Test with
   `pip install sparea==X.Y.Z` in a fresh venv.

If something goes wrong mid-publish (e.g. PyPI rejects the upload
because that version already exists), you cannot reuse the version
number — bump to `X.Y.Z+1` and try again. Tags are also immutable on
PyPI; a deleted release can't be re-uploaded under the same version.
