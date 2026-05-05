//! Builds libsparea.{dylib,so,dll}: a shared library that exposes the
//! sparea Zig package's polygon-area function via a C ABI for the
//! Python ctypes wrapper. The upstream sparea Zig source is fetched
//! by `zig build` from the URL pinned in build.zig.zon.

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
        // c_api.zig uses std.heap.c_allocator, which requires libc to
        // be explicitly linked on Linux/Windows (macOS gets it for free).
        .link_libc = true,
        // The static archive ends up linked into a Python extension
        // (.so / .pyd), which is itself a shared library — its
        // constituent objects must be position-independent.
        .pic = true,
        .imports = &.{
            .{ .name = "sparea", .module = sparea_mod },
        },
    });

    // Static lib: gets pulled into the C++ extension at link time.
    // Avoids the Windows MSVC CRT mismatch you get when mixing a Zig
    // DLL with a separately-compiled MSVC C++ extension (zig#19672,
    // #18685, #11422), and sidesteps the macOS dylib `__dso_handle`
    // regression (zig#24370).
    const lib = b.addLibrary(.{
        .name = "sparea",
        .linkage = .static,
        .root_module = cabi_mod,
    });
    b.installArtifact(lib);
}
