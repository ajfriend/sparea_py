# nanobind prototype — branch report

**Branch**: `nanobind-prototype` · **PR**: #1 · **Verdict**: works
cross-platform now that libsparea is a static archive, but for the
current 1-function surface still not worth the C++ + CMake cost.

This branch was an end-to-end prototype of replacing the `ctypes`
binding on `main` with a `nanobind` binding driven by
`scikit-build-core` + CMake. Companion to the `cffi-prototype`
(PR #2) and `pybind11-prototype` (PR #3) branches — together the
three give a fair picture of where each binding sits.

## What got built

| File | Purpose |
|------|---------|
| `CMakeLists.txt` | Drives both Zig build (custom command via `python -m ziglang`) and the nanobind extension (`nanobind_add_module`). Wraps Zig's static archive as an IMPORTED CMake target and links it into `_nb`. |
| `src/cpp/binding.cpp` | Single-function C++ binding using `nb::ndarray<const double, nb::shape<-1, 3>, nb::c_contig>` for zero-copy `(N, 3)` numpy arrays. |
| `src/zig/build.zig` | Switched to `linkage = .static, pic = true` so the archive gets pulled into the C++ extension at link time — no runtime DLL/dylib. |
| `src/zig/c_api.zig` | Added `sparea_polygon_area_vec3(verts, n, *out)` paired with the nanobind binding's interleaved `(N, 3)` layout. |
| `src/sparea/__init__.py` | 14 stmts (down from 43): shape-check + `(N, 2)` lat/lng → xyz numpy trig + delegate to `_nb`. Custom exception classes are gone — nanobind raises `ValueError` directly. |
| `pyproject.toml` | Build backend swapped from `hatchling` to `scikit-build-core`. Pulled in `nanobind>=2.0` as a build dep. |
| `src/hatch_build.py` | Deleted — CMake replaces it. |

## Cross-platform results

All four wheel platforms green after the static-archive switch:
Linux x86_64 (manylinux + musllinux), Linux aarch64, macOS arm64,
Windows AMD64. sdist round-trip too.

## What we hit and what fixed it (with research links)

### macOS 26 / Xcode 26 — `__dso_handle` linker error

When linking nanobind's static lib (or any pybind11 LTO build) against
a Zig **dylib** on macOS 26:

```
ld: fixup error (kind=arm64_adrp_lo12) at '_OUTLINED_FUNCTION_0'+0x24
from libnanobind-static.a[N](nb_internals.cpp.o), target '___dso_handle'
does not have address
```

Initial workaround was to define `__dso_handle = nullptr` (visibility
hidden) in `binding.cpp` — works but smelly.

**Actual root cause**: not nanobind, not the Apple linker — **Zig**.
[zig#24370](https://github.com/ziglang/zig/issues/24370) ("Zig does
not populate `__dso_handle` correctly on macOS"). Zig's MachO backend
regressed and stopped emitting the symbol in dylibs from 0.14.1+.
clang's MachineOutliner / LTO surface the issue by emitting ADRP+ADD
fixups against the missing symbol.

**Real fix**: make libsparea a static archive instead of a dylib.
The consuming linker (the one building the `.so`/`.pyd`) emits
`__dso_handle` for the final image, and the Zig regression doesn't
apply.

### Windows — MSVC C-runtime mismatch

When linking the nanobind extension against Zig's import library
`sparea.lib`, the MSVC linker complained about unresolved CRT symbols
(`__std_exception_copy`, `__imp___acrt_iob_func`,
`__imp___stdio_common_vfprintf`, …). Adding `vcruntime`/`ucrt`/etc to
the link line surfaced more missing symbols each time.

**Root cause**: Zig's MSVC C-runtime story for shared libraries is
broken:
- [zig#19672](https://github.com/ziglang/zig/issues/19672) — `-fms-runtime-lib` is silently ignored.
- [zig#18685](https://github.com/ziglang/zig/issues/18685) — MSVC target broken with C++.
- [zig#11422](https://github.com/ziglang/zig/issues/11422) — unwinding across shared-library boundaries broken on Windows.

A Zig DLL built on Windows pulls in some Zig-internal mix of
UCRT/vcruntime/MSVCRT that doesn't line up with what an MSVC-built
`.pyd` expects. Forcing `CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL`
on the C++ side doesn't help — it doesn't reach Zig's link step.

**Real fix**: same as the macOS one — static archive, not DLL. With a
static lib there's only one CRT in play (the `.pyd`'s own `/MD`),
because Zig's link-time CRT decisions don't survive into the final
`.pyd`. The DLL goes away, the import library goes away, the
mismatch goes away.

This is the same architectural pattern Rust+pyo3 / scikit-build /
mainstream native-extension projects use: build the lower-level
library as a static archive, link it into the Python extension. No
public projects ship a Zig **DLL** + an MSVC C++ binding — that combo
is essentially un-trodden ground because Zig's MSVC-DLL story isn't
ready.

### Windows — `unresolved external symbol sincos`

After the static-archive switch, Windows surfaced one last linker
error: Zig's optimized object code references `sincos`, a glibc
extension that MSVC's libm doesn't ship. LLVM's optimizer
auto-fuses adjacent `sin(x)` + `cos(x)` calls (which the upstream
`sparea_zig` does for lat/lng → xyz conversion) into a single
`sincos(x)` call.

**Fix**: a one-line `extern "C" void sincos(double, double*, double*)`
shim in `binding.cpp` (Windows-only).

## Code shape comparison

For just the `polygon_area` surface (lat/lng *or* xyz input → area in
steradians):

| | `ctypes` (`main`) | `nanobind` (this branch) |
|---|---|---|
| Python wrapper LOC | ~125 (43 stmts) | ~50 (14 stmts) |
| C/C++ binding LOC | 0 | ~60 (`binding.cpp`, including 8-line Windows sincos shim) |
| Build-glue LOC | ~50 (`hatch_build.py`) | ~70 (`CMakeLists.txt`) |
| Languages to debug | Python | Python + C++ + CMake |
| Custom exception classes | yes | no (nanobind raises `ValueError`) |
| Cross-platform CI | green on first try | green after static-archive switch + sincos shim |
| Build deps | `hatchling`, `ziglang` | `scikit-build-core`, `cmake`, `ziglang`, `nanobind` |
| Wheel artifact | `__init__.py` + `libsparea.{dylib,so,dll}` (~50 KB) | `__init__.py` + `_nb.{so,pyd,dylib}` (~165 KB, libsparea baked in) |

Total LOC is roughly a wash. The Python file got nicer; the build
glue got bigger and gained two new languages. Wheel is ~3× larger
because nanobind's runtime bytes get linked in alongside libsparea.

## Verdict — when to revisit

For the current 1-function surface, the cost/benefit doesn't favor
nanobind. The Python wrapper is shorter but you pay with C++ + CMake
+ knowing about Zig's macOS/Windows quirks. The `xs.ctypes.data_as(...)`
line ctypes makes you write isn't worth the trade.

**Revisit nanobind if**:
- We add a batched API (`polygon_areas(list_of_polygons)` where the
  loop runs in C++ — `nb::ndarray`'s stride handling pays off).
- We add many more functions (the binding boilerplate amortizes).
- We hit a real perf wall on per-call overhead.

## Pointers

- PR #1 (nanobind, this branch): https://github.com/ajfriend/sparea_py/pull/1
- PR #2 (cffi, see its `branch_report.md`): https://github.com/ajfriend/sparea_py/pull/2
- PR #3 (pybind11, see its `branch_report.md`): https://github.com/ajfriend/sparea_py/pull/3
- Upstream tracking: zig#24370 (macOS dso_handle), zig#19672 / #18685 / #11422 (Windows MSVC).
