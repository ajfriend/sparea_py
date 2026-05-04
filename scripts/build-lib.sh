#!/usr/bin/env bash
# Build the sparea shared library and copy it into ./sparea/ so
# editable installs (`uv sync`) can find it. Wheel builds invoke
# the same logic via setup.py's BuildZig command.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"

(cd "$REPO" && zig build -Doptimize=ReleaseFast)

cp "$REPO"/zig-out/lib/libsparea.* "$REPO/sparea/"
echo "copied libsparea.* to $REPO/sparea/:"
ls "$REPO/sparea/"libsparea.*
