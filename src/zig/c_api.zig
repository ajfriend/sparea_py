//! C ABI shim for the sparea Python bindings. Lives here (in the
//! Python repo) rather than in the upstream sparea Zig package
//! because the only consumer is `sparea/__init__.py`'s ctypes call.

const std = @import("std");
const sparea = @import("sparea");

const Vec3 = sparea.Vec3;

pub const SPAREA_OK: c_int = 0;
pub const SPAREA_ANTIPODAL_EDGE: c_int = 1;
pub const SPAREA_TOO_FEW_VERTICES: c_int = 2;
pub const SPAREA_OOM: c_int = 3;

/// C ABI: area in steradians of a spherical polygon, in `[0, 4π)`.
/// Vertices are passed as three parallel f64 arrays of unit-vector
/// components. Result is written to `*out` on success; return value
/// is an error code (0 = success).
pub export fn sparea_polygon_area_xyz(
    xs: [*]const f64,
    ys: [*]const f64,
    zs: [*]const f64,
    n: usize,
    out: *f64,
) c_int {
    const allocator = std.heap.c_allocator;
    const verts = allocator.alloc(Vec3, n) catch return SPAREA_OOM;
    defer allocator.free(verts);
    for (0..n) |i| verts[i] = Vec3.init(xs[i], ys[i], zs[i]);

    out.* = sparea.polygon_area(f64, verts) catch |err| switch (err) {
        error.AntipodalEdge => return SPAREA_ANTIPODAL_EDGE,
        error.TooFewVertices => return SPAREA_TOO_FEW_VERTICES,
    };
    return SPAREA_OK;
}

/// C ABI: same as sparea_polygon_area_xyz, but takes an interleaved
/// `(N, 3)` row-major buffer `[x0, y0, z0, x1, y1, z1, ...]`. This
/// is the layout numpy gives you directly for a `(N, 3)` array with
/// no per-column copy — matches the C++ binding's input.
pub export fn sparea_polygon_area_vec3(
    verts_buf: [*]const f64,
    n: usize,
    out: *f64,
) c_int {
    const allocator = std.heap.c_allocator;
    const verts = allocator.alloc(Vec3, n) catch return SPAREA_OOM;
    defer allocator.free(verts);
    for (0..n) |i| {
        const base = i * 3;
        verts[i] = Vec3.init(verts_buf[base], verts_buf[base + 1], verts_buf[base + 2]);
    }

    out.* = sparea.polygon_area(f64, verts) catch |err| switch (err) {
        error.AntipodalEdge => return SPAREA_ANTIPODAL_EDGE,
        error.TooFewVertices => return SPAREA_TOO_FEW_VERTICES,
    };
    return SPAREA_OK;
}
