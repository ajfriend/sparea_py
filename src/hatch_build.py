"""Hatchling build hook: runs `zig build` and stages libsparea.* into
src/sparea/ before hatchling collects files for the wheel/sdist.

Picked up automatically by `pip wheel`, `uv build`, and cibuildwheel.
For cibuildwheel, ensure `zig` is on PATH in the build image (e.g. via
`CIBW_BEFORE_ALL`).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ZigBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        zig_dir = root / "src" / "zig"
        pkg_dir = root / "src" / "sparea"

        subprocess.check_call(
            ["zig", "build", "-Doptimize=ReleaseFast"],
            cwd=zig_dir,
        )

        # Zig drops the lib in different places per platform:
        #   linux:   zig-out/lib/libsparea.so
        #   macos:   zig-out/lib/libsparea.dylib
        #   windows: zig-out/bin/sparea.dll  (no "lib" prefix, in bin/)
        # On Windows, rename to libsparea.dll so the Python ctypes loader
        # can use a single naming scheme across all platforms.
        zig_out = zig_dir / "zig-out"
        candidates = [
            *(zig_out / "lib").glob("libsparea.dylib"),
            *(zig_out / "lib").glob("libsparea.so"),
            *(zig_out / "bin").glob("sparea.dll"),
        ]
        if not candidates:
            raise RuntimeError(f"zig build produced no shared library in {zig_out}")
        for lib in candidates:
            target = lib.name if lib.name.startswith("lib") else f"lib{lib.name}"
            shutil.copy2(lib, pkg_dir / target)
