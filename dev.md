# Development notes

Internal-facing notes on architecture, build mechanics, and
contributor workflows for `sparea_py`.

## Architecture

A thin Cython binding around a small C ABI shim that calls into the
upstream `sparea_zig` package. The Python side accepts a polygon as a
list of `(lat, lng)` pairs in radians, converts each vertex to a unit
3-vector with NumPy, and hands a contiguous `(N, 3)` buffer to the
Cython extension via a typed memoryview (`double[:, ::1]`) — no copy.

The C ABI shim (`src/zig/c_api.zig`) and `src/zig/build.zig` both
live here, not in the upstream `sparea_zig` package. The split is
intentional:

- **`sparea_zig` (upstream)**: pure Zig algorithm library. Exports a
  `Module` for other Zig code; no C ABI, no shared library.
- **`sparea_py` (this repo)**: depends on `sparea_zig` via
  `build.zig.zon`, wraps it in a tiny C ABI
  (`sparea_polygon_area_vec3`), builds a static archive, and links
  it directly into the Cython extension `_cy.<EXT>`.

libsparea is a **static** archive (not a shared library) so it gets
pulled into `_cy.so` / `_cy.pyd` at link time. That sidesteps both
the Windows MSVC CRT mismatch and the macOS dylib `__dso_handle`
regression you hit when shipping a Zig dynamic library; see
[sparea_zig#1](https://github.com/ajfriend/sparea_zig/issues/1) and
the linked Zig issues there for details.

## Layout

```
.
├── pyproject.toml          — meson-python config, package metadata
├── meson.build             — drives Zig static-archive build + Cython compile
├── justfile                — reinstall / test / wheel / clean / purge
├── src/
│   ├── cython/
│   │   └── _cy.pyx         — Cython binding, exposes polygon_area
│   ├── sparea/
│   │   └── __init__.py     — Python wrapper: shape-check + lat/lng→xyz
│   │                         numpy trig + delegate to _cy
│   └── zig/
│       ├── build.zig       — produces libsparea.{a,lib} (static archive)
│       ├── build.zig.zon   — pins the sparea_zig dependency
│       └── c_api.zig       — pub export fn sparea_polygon_area_vec3
└── tests/
    └── test_bindings.py
```

The wheel ships a single `_cy.<EXT>` (the Cython extension with
libsparea statically linked in); no separate dylib.

## Building and testing locally

```sh
just reinstall  # uv cache clean sparea + uv sync --reinstall-package sparea
just test       # reinstall + uv run pytest
just wheel      # uv build
```

`uv sync` invokes meson-python, which runs Zig (via `python -m
ziglang build`, since `ziglang` is in `[build-system].requires`),
then cythonizes `src/cython/_cy.pyx` and links the result against
the Zig static archive. No host-level Zig or Cython install needed —
both come from PyPI as build deps. Local dev uses non-editable
installs (`UV_NO_EDITABLE=1` at the top of the justfile) so each
edit force-reinstalls; `just test` chains through `just reinstall`
to make sure stale artifacts don't survive a test run.

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
