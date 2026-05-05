# cffi prototype — branch report

**Branch**: `cffi-prototype` · **PR**: #2 · **Verdict**: marginal win;
worth keeping in mind but not enough to justify the extra runtime dep.

This branch swaps the `ctypes` binding on `main` for `cffi` ABI mode.
Companion to the `nanobind-prototype` branch (PR #1, see that
branch's `branch_report.md`) — together the two prototypes give a
fair picture of where each binding sits on the cost/benefit curve.

## What got changed

| File | Change |
|------|--------|
| `pyproject.toml` | Added `"cffi>=1.16"` to `[project].dependencies`. |
| `src/sparea/__init__.py` | ctypes → cffi ABI-mode. Same architecture (`dlopen` libsparea, dynamic dispatch); only the per-call boilerplate changes. |

No build changes. Same `hatch_build.py`, same Zig step, same wheel
layout. ABI mode doesn't compile anything at install time — it just
loads the existing `libsparea.{dylib,so,dll}` at runtime, exactly
like ctypes.

## Cross-platform results (CI, first try)

| Platform | Result |
|---|---|
| Linux x86_64 (manylinux + musllinux) | ✓ |
| Linux aarch64 (manylinux + musllinux) | ✓ |
| macOS arm64 | ✓ |
| Windows AMD64 | ✓ |
| sdist round-trip | ✓ |
| 12/12 test-workflow matrix cells | ✓ |

No platform-specific workarounds, no linker hacks, no MSVC ABI
debugging. Build behavior is byte-for-byte identical to `main`; the
only thing that changed is which Python module dispatches the call.

## Code shape — what the binding actually looks like

**Type-and-signature declaration** (the biggest readability win):

```python
# ctypes (main)                                    # cffi (this branch)
_lib.sparea_polygon_area_xyz.argtypes = [          _ffi.cdef("""
    ctypes.POINTER(ctypes.c_double),                   int sparea_polygon_area_xyz(
    ctypes.POINTER(ctypes.c_double),                       const double *xs, const double *ys,
    ctypes.POINTER(ctypes.c_double),                       const double *zs, size_t n, double *out
    ctypes.c_size_t,                                   );
    ctypes.POINTER(ctypes.c_double),               """)
]
_lib.sparea_polygon_area_xyz.restype = ctypes.c_int
```

The `cdef` form is a copy-paste from a C header. ctypes' nested
`POINTER(c_double)` list is what you write when you don't have a real
C parser; cffi has one.

**Call site:**

```python
# ctypes                                          # cffi
out = ctypes.c_double()                           out = _ffi.new("double*")
err = _lib.sparea_polygon_area_xyz(               err = _lib.sparea_polygon_area_xyz(
    xs.ctypes.data_as(POINTER(c_double)),             _ffi.from_buffer("double[]", xs),
    ys.ctypes.data_as(POINTER(c_double)),             _ffi.from_buffer("double[]", ys),
    zs.ctypes.data_as(POINTER(c_double)),             _ffi.from_buffer("double[]", zs),
    xs.size,                                          xs.size,
    ctypes.byref(out),                                out,
)                                                 )
```

Mildly cleaner. `_ffi.from_buffer("double[]", xs)` understands the
numpy buffer protocol natively, so there's no `.ctypes.data_as` cast.

**Loading the lib** — identical:

```python
# ctypes                            # cffi
ctypes.CDLL(str(lib_path))          _ffi.dlopen(str(lib_path))
```

## Numbers

| | `ctypes` (`main`) | `cffi` (this branch) |
|---|---|---|
| `__init__.py` statements | 43 | 42 |
| Other files changed | 0 | 0 |
| Build deps added | 0 | 0 |
| Runtime deps added | 0 | 1 (`cffi` + transitive `pycparser`) |
| Cross-platform CI | green | green (first try, no workarounds) |
| Per-call cost | ctypes dispatch | cffi dispatch (same magnitude — both go through Python) |

## Cost — the runtime dep

`cffi` is the visible cost here. It's about 1 MB and pulls in
`pycparser` transitively. In practice it's near-zero overhead:
- `cffi` is a quasi-standard in scientific Python
- It's already a dep of `cryptography`, `gevent`, `psycopg-c`,
  `argon2-cffi`, and many others
- Most environments where someone is `pip install sparea`-ing already
  have cffi cached / installed

But it is one more thing in the dependency tree, and ctypes is
genuinely zero-cost (stdlib).

## Verdict — when to revisit

Strictly nicer code than ctypes for the same architecture, same
per-call cost, no build/CI complications. The case for switching is
weak today only because the ergonomic gain is small (~10 nicer LOC)
and we'd be trading a stdlib-only binding for a third-party one.

**Switch from ctypes to cffi if**:
- You add a second function and the duplicated `argtypes` boilerplate
  starts hurting (the `cdef` block scales much better — you just add
  another C declaration, no nested list of POINTERs).
- You hit a real ctypes corner: ctypes can't handle some C
  constructs cleanly (variadic functions, callbacks with
  complex signatures, function-pointer fields in structs). cffi
  handles them all directly via `cdef`.
- You want to switch to API mode for the per-call speedup. (API mode
  compiles a real CPython extension at install time using the C
  declarations, eliminating Python descriptor lookups per call. Not
  prototyped here.)

**Don't switch** for the current 1-function surface. The marginal LOC
win isn't worth the dep.

## Pointers

- PR #2: https://github.com/ajfriend/sparea_py/pull/2
- Companion: PR #1 (nanobind prototype) and `branch_report.md` on
  that branch — the nanobind path took multiple platform-specific
  linker workarounds and never built on Windows; cffi just works.
- API-mode follow-up (not done): would need a build step that
  generates `_cffi_<NNN>.so` at install time. Adds ~50 LOC of build
  glue but keeps the Python wrapper essentially identical.
