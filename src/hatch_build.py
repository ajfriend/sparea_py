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

        copied = []
        for lib in (zig_dir / "zig-out" / "lib").glob("libsparea.*"):
            dest = pkg_dir / lib.name
            shutil.copy2(lib, dest)
            copied.append(dest.name)
        if not copied:
            raise RuntimeError(
                f"zig build produced no libsparea.* in {zig_dir / 'zig-out' / 'lib'}"
            )
