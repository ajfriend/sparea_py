"""Hatchling build hook: runs `zig build` and stages libsparea.* into
src/sparea/ at wheel-build time. The Zig toolchain comes from the
`ziglang` build-system requirement, so no host install is needed."""

from __future__ import annotations

import os
import platform
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

        build_data["pure_python"] = False
        build_data["infer_tag"] = True

        # ziglang's only entry point is `python -m ziglang` (no `zig`
        # console script). Using sys.executable here picks up the
        # build-env's pinned ziglang regardless of $PATH.
        cmd = [sys.executable, "-m", "ziglang", "build", "-Doptimize=ReleaseFast"]

        # delocate-wheel rejects libs built for a newer macOS than the
        # wheel claims, and Zig defaults to the host SDK version. Pin
        # to MACOSX_DEPLOYMENT_TARGET (set by cibuildwheel).
        if sys.platform == "darwin":
            macos_min = os.environ.get("MACOSX_DEPLOYMENT_TARGET", "11.0")
            zig_arch = "aarch64" if platform.machine() == "arm64" else "x86_64"
            cmd.append(f"-Dtarget={zig_arch}-macos.{macos_min}")

        subprocess.check_call(cmd, cwd=zig_dir)

        # Zig drops the lib in different places per platform:
        #   linux:   zig-out/lib/libsparea.so
        #   macos:   zig-out/lib/libsparea.dylib
        #   windows: zig-out/bin/sparea.dll  (no "lib" prefix, in bin/)
        # Force a uniform `libsparea.<ext>` name so the ctypes loader
        # in src/sparea/__init__.py uses one scheme across platforms.
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
