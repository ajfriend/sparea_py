# pybind11 prototype — branch report

**Branch**: `pybind11-prototype` · **PR**: #3 · **Verdict**: works
cross-platform with libsparea as a static archive, but for the
current 1-function surface still not worth the C++ + CMake cost.

This branch swaps `ctypes` for a `pybind11` binding driven by
`scikit-build-core` + CMake. Companion to the `nanobind-prototype`
(PR #1) and `cffi-prototype` (PR #2) branches — together the three
give a fair picture of where each binding sits.

## What got built

| File | Purpose |
|------|---------|
| `CMakeLists.txt` | Drives both Zig build (custom command via `python -m ziglang`) and the pybind11 extension (`pybind11_add_module`). Wraps Zig's static archive as an IMPORTED CMake target and links it into `_pb`. |
| `src/cpp/binding.cpp` | Single-function C++ binding using `py::array_t<double, py::array::c_style \| py::array::forcecast>` for `(N, 3)` numpy arrays. |
| `src/zig/build.zig` | `linkage = .static, pic = true` so the archive gets pulled into the C++ extension at link time — no runtime DLL/dylib. |
| `src/zig/c_api.zig` | Added `sparea_polygon_area_vec3(verts, n, *out)` — interleaved `(N, 3)` C ABI matching what `py::array_t` hands us. |
| `src/sparea/__init__.py` | 14 stmts (down from 43): shape-check + `(N, 2)` lat/lng → xyz numpy trig + delegate to `_pb`. Custom exception classes are gone — pybind11 raises `ValueError`. |
| `pyproject.toml` | Build backend swapped from `hatchling` to `scikit-build-core`. Pulled in `pybind11>=2.13` as a build dep. |
| `src/hatch_build.py` | Deleted — CMake replaces it. |

## Cross-platform results

All four wheel platforms green: Linux x86_64 (manylinux + musllinux),
Linux aarch64, macOS arm64, Windows AMD64. sdist round-trip too.

## What we hit and what fixed it

### macOS 26 / Xcode 26 — `__dso_handle` linker error

Same error as the nanobind branch hit, even though pybind11 is
header-only and has no static lib of its own:

```
ld: fixup error (kind=arm64_adrp_lo12) at '_PyInit__pb'+0x17C from
lto.o, target '___dso_handle' does not have address
```

**Root cause**: not pybind11, not the Apple linker — **Zig**.
[zig#24370](https://github.com/ziglang/zig/issues/24370) — Zig's MachO
backend regressed and stopped emitting `__dso_handle` in dylibs from
0.14.1+. clang's MachineOutliner / LTO surface it by emitting ADRP+ADD
fixups against the missing symbol. The same bug shows up in any C++
extension that links against a Zig dylib on macOS 26.

**Real fix**: static archive instead of dylib. The consuming linker
emits `__dso_handle` for the final image and the Zig regression
doesn't apply.

### Windows — MSVC C-runtime mismatch

When linking `_pb` against Zig's import library `sparea.lib`, the MSVC
linker complained about unresolved CRT symbols (`__std_exception_copy`
and friends). Each lib I added to the link line surfaced more.

**Root cause**: Zig's MSVC C-runtime story for shared libraries is
broken: [zig#19672](https://github.com/ziglang/zig/issues/19672),
[zig#18685](https://github.com/ziglang/zig/issues/18685),
[zig#11422](https://github.com/ziglang/zig/issues/11422). A Zig DLL
on Windows pulls in a Zig-internal mix of UCRT/vcruntime/MSVCRT that
doesn't line up with what an MSVC-built `.pyd` expects.

**Real fix**: same as macOS — static archive, not DLL. With a static
lib the only CRT in play is the `.pyd`'s own `/MD`. No mismatch.

This is the same architectural pattern Rust+pyo3 / scikit-build /
mainstream native-extension projects use: build the lower-level
library as a static archive, link it into the Python extension.

### Windows — `unresolved external symbol sincos`

After the static-archive switch, Windows surfaced one last linker
error: Zig's optimized object code references `sincos`, a glibc
extension that MSVC's libm doesn't ship. LLVM auto-fuses adjacent
`sin(x)` + `cos(x)` calls (which the upstream `sparea_zig` does for
lat/lng → xyz conversion) into one `sincos(x)` call.

**Fix**: a one-line `extern "C" void sincos(double, double*, double*)`
shim in `binding.cpp` (Windows-only).

## Code shape comparison

For just the `polygon_area` surface (lat/lng *or* xyz input → area in
steradians):

| | `ctypes` (`main`) | `pybind11` (this branch) |
|---|---|---|
| Python wrapper LOC | ~125 (43 stmts) | ~50 (14 stmts) |
| C/C++ binding LOC | 0 | ~70 (`binding.cpp`, including 8-line Windows sincos shim) |
| Build-glue LOC | ~50 (`hatch_build.py`) | ~70 (`CMakeLists.txt`) |
| Languages to debug | Python | Python + C++ + CMake |
| Custom exception classes | yes | no (pybind11 raises `ValueError`) |
| Cross-platform CI | green on first try | green after static-archive switch + sincos shim |
| Build deps | `hatchling`, `ziglang` | `scikit-build-core`, `cmake`, `ziglang`, `pybind11` |
| Wheel artifact | `__init__.py` + `libsparea.{dylib,so,dll}` (~50 KB) | `__init__.py` + `_pb.{so,pyd,dylib}` (libsparea baked in) |

## pybind11 vs nanobind (same architecture, different binding lib)

- **pybind11**: `py::array_t<double, py::array::c_style \| py::array::forcecast>`
  forces a contiguous (N, M) array, then `verts.unchecked<2>()` gives
  a typed pointer. No LTO config needed; simpler build.
- **nanobind**: `nb::ndarray<const double, nb::shape<-1, 3>, nb::c_contig>`
  encodes the shape constraint in the type. nanobind has stable-ABI
  builds (a wheel that works across Python minor versions); pybind11
  doesn't natively.

For this project both feel about equivalent. nanobind would have a
small edge if we shipped wheels with stable ABI (one wheel per
platform instead of per Python-version), but cibuildwheel's
per-version wheels work fine for sparea's scale.

## Verdict — when to revisit

For the current 1-function surface, the cost/benefit doesn't favor
pybind11 (or nanobind, or any C++ binding). The Python wrapper is
shorter but you pay with C++ + CMake + knowing about Zig's
macOS/Windows quirks.

**Revisit pybind11 if**:
- We add a batched API (`polygon_areas(list_of_polygons)`) where the
  loop runs in C++ — `py::array_t`'s zero-copy buffer access pays off.
- We add many more functions (binding boilerplate amortizes).
- We hit a real perf wall on per-call overhead.

If we ever do migrate, the choice between pybind11 and nanobind is
secondary — the bigger architectural decision is "C++ binding via
scikit-build-core" vs "stay in pure Python with ctypes/cffi". The
research that fixed both prototypes' cross-platform issues (static
archive instead of Zig dylib) applies identically to whichever C++
binding lib you pick.

## Pointers

- PR #3 (pybind11, this branch): https://github.com/ajfriend/sparea_py/pull/3
- PR #2 (cffi, see its `branch_report.md`): https://github.com/ajfriend/sparea_py/pull/2
- PR #1 (nanobind, see its `branch_report.md`): https://github.com/ajfriend/sparea_py/pull/1
- Upstream tracking: zig#24370 (macOS dso_handle), zig#19672 / #18685 / #11422 (Windows MSVC).
