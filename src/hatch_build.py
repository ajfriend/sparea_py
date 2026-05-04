"""Hatchling build hook: runs `zig build` and stages libsparea.* into
src/sparea/ before hatchling collects files for the wheel/sdist.

Picked up automatically by `pip wheel`, `uv build`, and cibuildwheel.
For cibuildwheel, ensure `zig` is on PATH in the build image (e.g. via
`CIBW_BEFORE_ALL`).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ZigBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        zig_dir = root / "src" / "zig"
        pkg_dir = root / "src" / "sparea"

        # We're shipping a compiled artifact; tell hatchling to emit a
        # platform-tagged wheel (cp3X-cp3X-<platform>) instead of the
        # default py3-none-any.
        build_data["pure_python"] = False
        build_data["infer_tag"] = True

        # The `ziglang` build dep doesn't expose a `zig` console script —
        # only `python -m ziglang`. Going through sys.executable picks up
        # the build-env's pinned ziglang regardless of what's on PATH.
        subprocess.check_call(
            [sys.executable, "-m", "ziglang", "build", "-Doptimize=ReleaseFast"],
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
