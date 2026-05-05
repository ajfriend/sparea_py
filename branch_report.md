# nanobind prototype — branch report

**Branch**: `nanobind-prototype` · **PR**: #1 · **Verdict**: not worth merging today.

This branch was an end-to-end prototype of replacing the `ctypes`
binding on `main` with a `nanobind` binding driven by
`scikit-build-core` + CMake. The goal was to see whether the resulting
code/build is actually nicer than the status quo.

## What got built

| File | Purpose |
|------|---------|
| `CMakeLists.txt` | Drives both Zig build (custom command via `python -m ziglang`) and the nanobind extension (`nanobind_add_module`). Stages both under `sparea/` for the wheel install. |
| `src/cpp/binding.cpp` | Single-function C++ binding using `nb::ndarray<const double, nb::shape<-1, 3>, nb::c_contig>` for zero-copy `(N, 3)` numpy arrays. |
| `src/zig/c_api.zig` | Added `sparea_polygon_area_vec3(verts, n, *out)` — paired with the nanobind binding's interleaved `(N, 3)` layout. The original `_xyz` (parallel arrays) entry point is unused on this branch. |
| `src/sparea/__init__.py` | Shrunk from 43 stmts to 14: shape-check + `(N, 2)` lat/lng → xyz numpy trig + delegate to `_nb`. Custom exception classes (`AntipodalEdgeError`, `TooFewVerticesError`) are gone — nanobind raises `ValueError`. |
| `pyproject.toml` | Build backend swapped from `hatchling` to `scikit-build-core`. Pulled in `nanobind>=2.0` as a build dep. |
| `src/hatch_build.py` | Deleted — CMake replaces it. |

## Cross-platform results (CI, after iterations)

| Platform | Result |
|---|---|
| Linux x86_64 (manylinux + musllinux) | ✓ |
| Linux aarch64 (manylinux + musllinux) | ✓ |
| macOS arm64 | ✓ (with workarounds, see below) |
| Windows AMD64 | ✗ — never got past the link step |
| sdist round-trip | ✓ |

## Notable issues + workarounds

### macOS 26 / Xcode 26 linker — `__dso_handle`

Linking nanobind's static lib produced:
```
ld: fixup error (kind=arm64_adrp_lo12) at '_OUTLINED_FUNCTION_0'+0x24
from libnanobind-static.a[2](nb_internals.cpp.o), target '___dso_handle'
does not have address
```

The new macOS linker fails to assign an address to `__dso_handle`
referenced from C++ global ctors in nanobind's static lib (clang
outlines these via ADRP+LO12 instruction pairs and the linker can't
resolve them).

**Tried** (all failed):
- `-Wl,-no_fixup_chains`
- `-mno-outline`
- Setting `CMAKE_OSX_DEPLOYMENT_TARGET=11.0` to match Python's

**What worked**: define the symbol ourselves in `binding.cpp`:
```cpp
#if defined(__APPLE__)
extern "C" __attribute__((visibility("hidden"))) void *__dso_handle = nullptr;
#endif
```

Probably specific to recent macOS dev machines — CI's `macos-latest`
(currently macOS 14/15) shouldn't trigger it, but the workaround is
harmless.

### Windows — MSVC CRT mismatch (the blocker)

Linking `_nb` against `sparea.lib` (Zig's import library for
`libsparea.dll`) consistently surfaces unresolved CRT symbols:

- First attempt: `unresolved external symbol __std_exception_copy`
- After adding `vcruntime` to `target_link_libraries`: missing
  `__imp___acrt_iob_func`, `__imp___stdio_common_vfprintf` (UCRT)
- After forcing `CMAKE_MSVC_RUNTIME_LIBRARY = MultiThreadedDLL`
  (`/MD`): back to `__std_exception_copy`

The root cause: nanobind's static lib was compiled against one MSVC
runtime ABI; Zig's `libsparea.dll`/`sparea.lib` references a
different one. Each fix surfaces another missing symbol from a
different sub-library (UCRT, vcruntime, MSVCRT).

**Real fixes** (any of these would work, all are significant rework):
1. Build `sparea` as a static `.lib` on Windows (no DLL, no import
   library, no CRT mismatch). Changes the artifact shape. Need to
   verify Zig's static lib output is MSVC-link-compatible (target
   triple `x86_64-windows-msvc`, COFF format, PIC).
2. Don't link against `sparea.lib` at all on Windows — use
   `LoadLibrary` + `GetProcAddress` at module init. Re-implements
   ctypes inside the C++ binding. Defeats the "static link" benefit
   nanobind would otherwise give us.
3. Pin Zig's MSVC version to exactly match cibuildwheel's. Fragile,
   has to track upstream.

None of these is clean for a one-function library.

## Code shape comparison

For just the `polygon_area` surface (lat/lng *or* xyz input → area in
steradians):

| | `ctypes` (`main`) | `nanobind` (this branch) |
|---|---|---|
| Python wrapper LOC | ~125 (43 stmts) | ~50 (14 stmts) |
| C/C++ binding LOC | 0 | ~50 (`binding.cpp`) |
| Build-glue LOC | ~50 (`hatch_build.py`) | ~95 (`CMakeLists.txt`) + per-platform workarounds |
| Languages to debug | Python | Python + C++ + CMake |
| Custom exception classes | yes | no (nanobind raises `ValueError`) |
| Cross-platform CI | green on first try | macOS workaround needed; Windows broken |
| Build deps | `hatchling`, `ziglang` | `scikit-build-core`, `cmake`, `ziglang`, `nanobind` |

Total LOC is roughly a wash. The Python file got nicer; the build
glue got worse and gained two new languages.

## Verdict — when to revisit

For the current 1-function surface, the cost/benefit doesn't favor
nanobind. The Python wrapper is shorter but the build complexity and
cross-platform fragility cost more than the `xs.ctypes.data_as(...)`
line buys back.

**Revisit nanobind if**:
- We add a batched API (e.g. `polygon_areas(list_of_polygons)` where
  the loop runs in C++ — that's where the per-call overhead actually
  matters and where `nb::ndarray`'s stride handling pays off).
- We add many more functions (the binding boilerplate amortizes).
- We hit a real perf wall on per-call overhead (currently `ctypes`
  does ~1µs per call, dominated by descriptor lookups; for any
  workload calling `polygon_area` >100k times in Python, this would
  start to bite).

**Don't revisit just to** "use a more modern binding tool" — for one
function returning a scalar, ctypes is adequate.

## Pointers

- PR with full diff: https://github.com/ajfriend/sparea_py/pull/1
- Final commit on branch: see `git log nanobind-prototype`
- The standalone `sparea_polygon_area_vec3` C ABI added to
  `src/zig/c_api.zig` is harmless — could be kept on `main` if/when
  we want to expose an interleaved-buffer interface (e.g. via a
  future `polygon_area_xyz_interleaved` ctypes call).
