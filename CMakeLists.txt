cmake_minimum_required(VERSION 3.20)

# Match Python's MACOSX_DEPLOYMENT_TARGET so the extension links cleanly
# against nanobind's static lib. cibuildwheel sets the env var; locally
# we default to 11.0 (Python's own minimum). Must be set before project().
if(APPLE AND NOT DEFINED CMAKE_OSX_DEPLOYMENT_TARGET)
    if(DEFINED ENV{MACOSX_DEPLOYMENT_TARGET})
        set(CMAKE_OSX_DEPLOYMENT_TARGET "$ENV{MACOSX_DEPLOYMENT_TARGET}")
    else()
        set(CMAKE_OSX_DEPLOYMENT_TARGET "11.0")
    endif()
endif()


project(sparea LANGUAGES CXX)

# ----- 1. Build libsparea via the upstream Zig project ---------------
# We don't ask CMake to compile Zig itself; we shell out to ziglang
# (a build-system requirement, see pyproject.toml). The output is a
# shared library that the nanobind extension links against.

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

# `python -m ziglang` ships with the `ziglang` PyPI wheel.
set(ZIG_CMD ${Python_EXECUTABLE} -m ziglang build -Doptimize=ReleaseFast)

# Pin macOS deployment target — Zig defaults to host SDK, which is
# newer than the wheel's claimed minimum and trips delocate-wheel.
if(APPLE)
    if(NOT DEFINED ENV{MACOSX_DEPLOYMENT_TARGET})
        set(ENV{MACOSX_DEPLOYMENT_TARGET} "11.0")
    endif()
    if(CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
        list(APPEND ZIG_CMD -Dtarget=aarch64-macos.$ENV{MACOSX_DEPLOYMENT_TARGET})
    else()
        list(APPEND ZIG_CMD -Dtarget=x86_64-macos.$ENV{MACOSX_DEPLOYMENT_TARGET})
    endif()
endif()

# Per-platform layout for Zig's output and for what the loader expects
# at runtime. On Windows Zig writes `sparea.dll` (no `lib` prefix);
# we rename to `libsparea.dll` for one consistent name across OSes.
if(WIN32)
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/bin/sparea.dll")
    set(STAGED_LIB_NAME "libsparea.dll")
    set(STAGED_LINK_NAME "${STAGED_LIB_NAME}")
elseif(APPLE)
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib/libsparea.dylib")
    set(STAGED_LIB_NAME "libsparea.dylib")
    set(STAGED_LINK_NAME "${STAGED_LIB_NAME}")
else()
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib/libsparea.so")
    set(STAGED_LIB_NAME "libsparea.so")
    set(STAGED_LINK_NAME "${STAGED_LIB_NAME}")
endif()

set(STAGED_LIB "${CMAKE_BINARY_DIR}/sparea/${STAGED_LIB_NAME}")

add_custom_command(
    OUTPUT "${STAGED_LIB}"
    COMMAND ${ZIG_CMD}
    COMMAND ${CMAKE_COMMAND} -E copy "${ZIG_OUT_LIB}" "${STAGED_LIB}"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}/src/zig"
    COMMENT "Building libsparea via Zig"
    VERBATIM
)
add_custom_target(libsparea ALL DEPENDS "${STAGED_LIB}")

# ----- 2. Build the nanobind extension -------------------------------

find_package(nanobind CONFIG REQUIRED)

nanobind_add_module(_nb src/cpp/binding.cpp)
add_dependencies(_nb libsparea)

# Tell the extension where to find libsparea at link time and at
# runtime. @loader_path / $ORIGIN make the rpath relative to the
# extension itself, so the wheel-install layout works.
# On Windows the linker needs the import library `sparea.lib`, which
# Zig writes to zig-out/lib/ (alongside its archive output) — the .dll
# itself is in zig-out/bin/ and we copy it into CMAKE_BINARY_DIR/sparea.
if(WIN32)
    target_link_directories(_nb PRIVATE "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib")
    # __std_exception_copy lives in modern vcruntime; Zig's import lib
    # for libsparea drags in CRT references the linker doesn't auto-pull.
    target_link_libraries(_nb PRIVATE sparea vcruntime)
else()
    target_link_directories(_nb PRIVATE "${CMAKE_BINARY_DIR}/sparea")
    target_link_libraries(_nb PRIVATE sparea)
endif()

if(APPLE)
    set_target_properties(_nb PROPERTIES
        BUILD_RPATH "@loader_path"
        INSTALL_RPATH "@loader_path"
    )
elseif(UNIX)
    set_target_properties(_nb PROPERTIES
        BUILD_RPATH "$ORIGIN"
        INSTALL_RPATH "$ORIGIN"
    )
endif()

# ----- 3. Install both into the wheel package dir --------------------

install(TARGETS _nb LIBRARY DESTINATION sparea)
install(FILES "${STAGED_LIB}" DESTINATION sparea)
