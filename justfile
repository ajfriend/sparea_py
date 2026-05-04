# disable editable installs so uv sync does a full build of the zig extension
export UV_NO_EDITABLE := "1"
export UV_OFFLINE := "0"  # toggle on when offline to avoid failures

_:
    just --list

# force-rebuild the zig extension to avoid stale builds
reinstall:
    uv cache clean sparea
    uv sync --reinstall-package sparea

# locally, always reinstall before testing
test: reinstall ci-test

ci-test:
    uv run pytest -q

# Build the wheel.
wheel:
    uv build

# Bump the pinned sparea_zig version.
bump version:
    cd src/zig && zig fetch --save=sparea https://github.com/ajfriend/sparea_zig/archive/refs/tags/{{version}}.tar.gz

# Rebuild libsparea.* in src/sparea/ standalone (no uv needed).
build:
    cd src/zig && zig build -Doptimize=ReleaseFast
    cp src/zig/zig-out/lib/libsparea.* src/sparea/

purge:
    just _rm .venv
    just _rm '*.pytest_cache'
    just _rm .DS_Store
    just _rm '*.egg-info'
    just _rm dist
    just _rm __pycache__
    just _rm uv.lock
    just _rm build
    just _rm zig-out
    just _rm .zig-cache
    just _rm .mypy_cache
    just _rm .ruff_cache
    just _rm 'libsparea.*'
    uv cache clean sparea

_rm pattern:
    -@find . -name "{{pattern}}" -prune -exec rm -rf {} +
