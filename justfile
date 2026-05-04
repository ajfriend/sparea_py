default:
    @just --list

# Build libsparea and copy it into sparea/ for editable installs.
build:
    ./scripts/build-lib.sh

# Sync the venv (assumes `just build` has produced sparea/libsparea.*).
sync:
    uv sync

# Run the Python test suite.
test:
    uv run pytest -q

# Build the wheel via setup.py's BuildZig hook.
wheel:
    uv build

# Bump the pinned sparea_zig version.
bump version:
    zig fetch --save=sparea https://github.com/ajfriend/sparea_zig/archive/refs/tags/{{version}}.tar.gz

# Remove build artifacts.
clean:
    rm -rf zig-out .zig-cache build dist sparea.egg-info sparea/libsparea.*
