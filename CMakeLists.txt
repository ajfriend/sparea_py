cmake_minimum_required(VERSION 3.20)

# Force the dynamic MSVC runtime (/MD), which is what Python extensions
# expect. Must be set before project().
cmake_policy(SET CMP0091 NEW)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")

# Match Python's MACOSX_DEPLOYMENT_TARGET so the extension links cleanly.
if(APPLE AND NOT DEFINED CMAKE_OSX_DEPLOYMENT_TARGET)
    if(DEFINED ENV{MACOSX_DEPLOYMENT_TARGET})
        set(CMAKE_OSX_DEPLOYMENT_TARGET "$ENV{MACOSX_DEPLOYMENT_TARGET}")
    else()
        set(CMAKE_OSX_DEPLOYMENT_TARGET "11.0")
    endif()
endif()

project(sparea LANGUAGES CXX)

# ----- 1. Build libsparea as a static archive via Zig ----------------
# The .a / .lib gets pulled into the C++ extension at link time, so
# there's no runtime DLL/dylib to ship and no CRT-mode mismatch on
# Windows.

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

set(ZIG_CMD ${Python_EXECUTABLE} -m ziglang build -Doptimize=ReleaseFast)

if(APPLE)
    if(CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
        list(APPEND ZIG_CMD -Dtarget=aarch64-macos.${CMAKE_OSX_DEPLOYMENT_TARGET})
    else()
        list(APPEND ZIG_CMD -Dtarget=x86_64-macos.${CMAKE_OSX_DEPLOYMENT_TARGET})
    endif()
endif()

if(WIN32)
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib/sparea.lib")
else()
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib/libsparea.a")
endif()

add_custom_command(
    OUTPUT "${ZIG_OUT_LIB}"
    COMMAND ${ZIG_CMD}
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}/src/zig"
    COMMENT "Building libsparea static archive via Zig"
    VERBATIM
)
add_custom_target(libsparea_build DEPENDS "${ZIG_OUT_LIB}")

# Wrap the prebuilt static archive as an IMPORTED target so the C++
# extension can link against it via target_link_libraries.
add_library(libsparea STATIC IMPORTED)
set_target_properties(libsparea PROPERTIES IMPORTED_LOCATION "${ZIG_OUT_LIB}")
add_dependencies(libsparea libsparea_build)

# ----- 2. Build the pybind11 extension -------------------------------

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_pb src/cpp/binding.cpp)
target_link_libraries(_pb PRIVATE libsparea)

# ----- 3. Install into the wheel package dir -------------------------

install(TARGETS _pb LIBRARY DESTINATION sparea)
