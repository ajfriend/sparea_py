//! C ABI shim for the sparea Python bindings. Marshals between C
//! scalars and the upstream `Options` struct; all real work happens
//! in `sparea.polygon_area`.

const std = @import("std");
const sparea = @import("sparea");

const Vec3 = sparea.Vec3;

// Cast `[*]const f64` directly to `[*]const Vec3` to skip the
// per-call alloc + element-wise copy. Asserted at comptime so any
// future Vec3 layout change in the upstream package fails loud here
// rather than producing silently wrong areas.
comptime {
    std.debug.assert(@sizeOf(Vec3) == 3 * @sizeOf(f64));
    std.debug.assert(@alignOf(Vec3) == @alignOf(f64));
    std.debug.assert(@offsetOf(Vec3, "x") == 0);
    std.debug.assert(@offsetOf(Vec3, "y") == @sizeOf(f64));
    std.debug.assert(@offsetOf(Vec3, "z") == 2 * @sizeOf(f64));
}

pub const SPAREA_OK: c_int = 0;
pub const SPAREA_ANTIPODAL_EDGE: c_int = 1;
pub const SPAREA_TOO_FEW_VERTICES: c_int = 2;
pub const SPAREA_BAD_ALGO: c_int = 3;

/// C ABI: area in steradians of a spherical polygon. `verts_buf` is
/// an interleaved `(N, 3)` row-major buffer `[x0, y0, z0, ...]` —
/// what numpy gives us directly for a `(N, 3)` array. `algo` selects
/// the kernel (0=auto, 1=cross, 2=angle); `signed` selects the
/// output convention (0 = fold into `[0, 4π)`, non-zero = raw signed
/// kernel value). Result is written to `*out` on success; return
/// value is an error code (0 = success).
pub export fn sparea_polygon_area_vec3(
    verts_buf: [*]const f64,
    n: usize,
    algo: c_int,
    signed: c_int,
    out: *f64,
) c_int {
    const verts: []const Vec3 = @as([*]const Vec3, @ptrCast(@alignCast(verts_buf)))[0..n];
    const opts: sparea.Options = .{
        .algo = switch (algo) {
            0 => .auto,
            1 => .cross,
            2 => .angle,
            else => return SPAREA_BAD_ALGO,
        },
        .signed = signed != 0,
    };
    out.* = sparea.polygon_area(verts, opts) catch |err| switch (err) {
        error.AntipodalEdge => return SPAREA_ANTIPODAL_EDGE,
        error.TooFewVertices => return SPAREA_TOO_FEW_VERTICES,
    };
    return SPAREA_OK;
}
