//! Builds libsparea.{a,lib}: a static archive that exposes the sparea
//! Zig package's polygon-area function via a C ABI for the Cython
//! extension to link against. The upstream sparea Zig source is
//! fetched by `zig build` from the URL pinned in build.zig.zon.

const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const sparea_mod = b.dependency("sparea", .{
        .target = target,
        .optimize = optimize,
    }).module("sparea");

    const cabi_mod = b.createModule(.{
        .root_source_file = b.path("c_api.zig"),
        .target = target,
        .optimize = optimize,
        .link_libc = true,
        // The static archive ends up linked into a Python extension
        // (.so / .pyd), which is itself a shared library — its
        // constituent objects must be position-independent.
        .pic = true,
        .imports = &.{
            .{ .name = "sparea", .module = sparea_mod },
        },
    });

    // Static lib pulled into the Cython extension at link time.
    // Avoids the Windows MSVC CRT mismatch and the macOS dylib
    // __dso_handle regression — see the nanobind/pybind11 prototype
    // branches' branch_report.md for the upstream Zig issue links.
    const lib = b.addLibrary(.{
        .name = "sparea",
        .linkage = .static,
        .root_module = cabi_mod,
    });
    b.installArtifact(lib);
}
