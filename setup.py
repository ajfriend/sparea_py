"""Build hook: shells `zig build` (which fetches the upstream sparea
Zig package via build.zig.zon) and bundles the resulting shared
library into the sparea Python package directory.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


HERE = Path(__file__).parent.resolve()
PKG_DIR = HERE / "sparea"


class BuildZig(build_py):
    def run(self):
        subprocess.check_call(
            ["zig", "build", "-Doptimize=ReleaseFast"],
            cwd=HERE,
        )
        out = HERE / "zig-out" / "lib"
        copied = []
        for lib in out.glob("libsparea.*"):
            dest = PKG_DIR / lib.name
            shutil.copy2(lib, dest)
            copied.append(dest.name)
        if not copied:
            raise RuntimeError(f"no libsparea.* produced in {out}")
        super().run()


setup(cmdclass={"build_py": BuildZig})
