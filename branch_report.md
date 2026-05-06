# Cython prototype — branch report

**Branch**: `cython-prototype` · **PR**: #4 · **Verdict**: works
cross-platform with meson-python; the `.pyx` is the cleanest binding
code of the four prototypes — but for the current 1-function surface
the build-system overhead still doesn't pay back.

Companion to the `cffi-prototype` (PR #2), `nanobind-prototype`
(PR #1), and `pybind11-prototype` (PR #3) branches.

## What got built

| File | Purpose |
|------|---------|
| `meson.build` | 44 LOC. Drives Zig static-archive build via `custom_target` and the Cython extension via `py.extension_module(... 'foo.pyx', ...)` (meson runs `cython` natively — no manual custom-command). |
| `src/cython/_cy.pyx` | Cython binding. Typed memoryview `double[:, ::1] verts` for zero-copy contiguous (N, 3) numpy input, inline `cdef extern` declaration of the C ABI, plus a Windows sincos shim. |
| `src/zig/build.zig` | `linkage = .static, pic = true` so the archive gets pulled into the Cython extension at link time. |
| `src/zig/c_api.zig` | Added `sparea_polygon_area_vec3` (interleaved buffer) for the binding. |
| `src/sparea/__init__.py` | 14 stmts: shape-check + `(N, 2)` lat/lng → xyz numpy trig + delegate to `_cy`. Custom exception classes are gone — `_cy.polygon_area` raises `ValueError`. |
| `pyproject.toml` | Build backend swapped from `hatchling` to `meson-python`. Added `cython>=3.0` build dep. |
| `src/hatch_build.py` | Deleted — meson replaces it. |

## Cross-platform results

All four wheel platforms green: Linux x86_64 (manylinux + musllinux),
Linux aarch64, macOS arm64, Windows AMD64. sdist round-trip too.

## What we hit and what fixed it

### macOS / Windows base issues — same as the C++ branches

Both showed up here too and the fixes are the same as on the
nanobind / pybind11 prototype branches:

- **macOS**: Zig's MachO `__dso_handle` regression
  ([zig#24370](https://github.com/ziglang/zig/issues/24370)) — fixed
  by switching libsparea to a static archive instead of a dylib (the
  consuming linker emits `__dso_handle` for the final image).
- **Windows MSVC CRT mismatch**: Zig's MSVC C-runtime story for
  shared libraries is broken
  ([zig#19672](https://github.com/ziglang/zig/issues/19672),
  [#18685](https://github.com/ziglang/zig/issues/18685),
  [#11422](https://github.com/ziglang/zig/issues/11422)) — same fix
  as macOS: static archive, not DLL. Single CRT in play.

### Build system — initial scikit-build-core + CMake → meson-python

First version used `scikit-build-core + CMake` (~70 LOC of
CMakeLists, identical structure to the nanobind / pybind11 branches).
Switched to **meson-python + meson** (~44 LOC) after researching what
the broader scientific-Python ecosystem uses for Cython:

- NumPy / SciPy / Cython itself migrated from setuptools+distutils
  to meson-python (Ralf Gommers'
  [Moving SciPy to the Meson build system](https://labs.quansight.org/blog/moving-scipy-to-meson)
  is the canonical writeup).
- Meson has first-class Cython support
  ([Cython reference](https://mesonbuild.com/Cython.html)) —
  `py.extension_module(... 'foo.pyx', ...)` runs `cython` and links
  in one call, no manual `custom_command`.
- Static-archive consumption is clean via `custom_target` +
  `link_with`.

### Windows-specific: sincos auto-fusion (only on meson)

After switching to meson-python, Windows started crashing with a
stack overflow in `test_two_octant_polygon` (the test that takes the
angle-algorithm path through `sin`/`cos`):

```
Windows fatal exception: stack overflow
  ...
  File "...sparea/__init__.py", line 38 in polygon_area
```

**Root cause**: LLVM's optimizer in Zig fuses adjacent `sin(x)+cos(x)`
calls into a `sincos(x)` call. MSVC's libm doesn't ship `sincos`, so
we provide a shim. **Under meson's MSVC link-time codegen defaults
(but not under scikit-build-core's CMake defaults)**, MSVC re-fuses
the `sin(x)+cos(x)` calls *inside our own shim* back into another
`sincos()` call — recursing into the shim until the stack overflows.

**Fix**: route the shim's sin/cos through `volatile` function
pointers so the linker can't fuse them:

```c
typedef double (*sparea_unary_d)(double);
static volatile sparea_unary_d sparea_sin_fn = sin;
static volatile sparea_unary_d sparea_cos_fn = cos;
void sincos(double x, double *s, double *c) {
    *s = sparea_sin_fn(x);
    *c = sparea_cos_fn(x);
}
```

The C++ branches don't hit this because `scikit-build-core`'s default
MSVC flags don't enable LTCG aggressively enough to perform the
re-fusion. (You could probably trigger the same bug on those branches
by switching them to meson-python.)

## Code shape comparison

For just the binding source code — Python wrapper isn't shown, it's
the same 14-line `__init__.py` across the C++/Cython branches.

| | binding code looks like | binding LOC |
|---|---|---|
| ctypes (main) | Python with `argtypes` ceremony | ~30 (in `__init__.py`) |
| cffi | Python with one `cdef` block | ~30 (in `__init__.py`) |
| nanobind | C++ with `nb::ndarray<...>` template gymnastics | ~50 |
| pybind11 | C++ with `py::array_t<double>` | ~70 (incl. sincos shim) |
| **Cython** | **Python with `cdef` annotations, typed memoryview** | **~50 (incl. sincos shim)** |

The `.pyx` reads like Python with a few type annotations:

```cython
def polygon_area(double[:, ::1] verts not None) -> float:
    if verts.shape[1] != 3:
        raise ValueError("verts must be a 2-D array of shape (N, 3)")
    cdef double out
    cdef int err = sparea_polygon_area_vec3(&verts[0, 0], verts.shape[0], &out)
    if err == 0: return out
    ...
```

That `double[:, ::1]` typed memoryview is arguably the prettiest
zero-copy numpy syntax of any binding tool — no nb::ndarray template,
no py::array_t, no manual buffer-cast. It's just "a 2-D contiguous
double array".

## Build system comparison

| | LOC | first-class Cython? | first-try cross-platform? |
|---|---|---|---|
| scikit-build-core + CMake | ~70 | no — manual `add_custom_command` to invoke `cython` | yes (no platform tweaks needed beyond static-archive + sincos shim) |
| **meson-python + meson** | **44** | **yes — `py.extension_module(... 'foo.pyx', ...)` auto-invokes cython** | needed an extra `volatile`-fn-ptr trick on Windows to defeat MSVC LTCG sincos re-fusion |

Both work; meson-python is the modern path the scientific-Python
ecosystem converged on. The CMake fallback is more "boring" / more
deterministic on Windows MSVC linking.

## Verdict — when to revisit

Same as the other binding-prototype branches: for the current
1-function surface, the build-system overhead doesn't pay back. The
binding code itself is the cleanest of all four prototypes (Python
syntax, typed memoryviews), but you still pay for meson + Cython +
the static-archive plumbing.

**Where Cython would actually pull ahead of all the other options**:
a batched API where the per-polygon loop runs *inside* the `.pyx` in
Python-ish syntax with C-level types. None of the other binding tools
let you fuse Python-side loop logic with C calls that cleanly.

```cython
def polygon_areas(list_of_verts):  # sketch — not implemented
    cdef double area
    cdef double[:, ::1] verts
    out = np.empty(len(list_of_verts))
    for i, v in enumerate(list_of_verts):
        verts = v
        sparea_polygon_area_vec3(&verts[0, 0], verts.shape[0], &area)
        out[i] = area
    return out
```

That's the killer-app pattern. cffi/nanobind/pybind11 all have to
either accept a preassembled bulk buffer or pay Python overhead per
iteration; Cython's typed memoryviews fuse the loop into compiled
code with no Python overhead between calls.

## Pointers

- PR #4 (Cython, this branch): https://github.com/ajfriend/sparea_py/pull/4
- PR #1 (nanobind, see its `branch_report.md`): https://github.com/ajfriend/sparea_py/pull/1
- PR #2 (cffi, see its `branch_report.md`): https://github.com/ajfriend/sparea_py/pull/2
- PR #3 (pybind11, see its `branch_report.md`): https://github.com/ajfriend/sparea_py/pull/3
- Build-system rationale: [Moving SciPy to Meson](https://labs.quansight.org/blog/moving-scipy-to-meson)
- Upstream tracking: zig#24370 (macOS dso_handle), zig#19672 / #18685 / #11422 (Windows MSVC).
