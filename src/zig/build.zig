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
        .imports = &.{
            .{ .name = "sparea", .module = sparea_mod },
        },
    });

    const lib = b.addLibrary(.{
        .name = "sparea",
        .linkage = .dynamic,
        .root_module = cabi_mod,
    });
    b.installArtifact(lib);
}
