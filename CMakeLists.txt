cmake_minimum_required(VERSION 3.20)

cmake_policy(SET CMP0091 NEW)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")

if(APPLE AND NOT DEFINED CMAKE_OSX_DEPLOYMENT_TARGET)
    if(DEFINED ENV{MACOSX_DEPLOYMENT_TARGET})
        set(CMAKE_OSX_DEPLOYMENT_TARGET "$ENV{MACOSX_DEPLOYMENT_TARGET}")
    else()
        set(CMAKE_OSX_DEPLOYMENT_TARGET "11.0")
    endif()
endif()

project(sparea LANGUAGES C)

# ----- 1. Build libsparea as a static archive via Zig ----------------

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

add_library(libsparea STATIC IMPORTED)
set_target_properties(libsparea PROPERTIES IMPORTED_LOCATION "${ZIG_OUT_LIB}")
add_dependencies(libsparea libsparea_build)

# ----- 2. Cythonize binding.pyx → binding.c, build the extension -----

set(CYTHON_PYX "${CMAKE_SOURCE_DIR}/src/cython/_cy.pyx")
set(CYTHON_C "${CMAKE_BINARY_DIR}/_cy.c")

add_custom_command(
    OUTPUT "${CYTHON_C}"
    COMMAND ${Python_EXECUTABLE} -m cython -3 --output-file "${CYTHON_C}" "${CYTHON_PYX}"
    DEPENDS "${CYTHON_PYX}"
    COMMENT "Cythonizing binding.pyx"
    VERBATIM
)

Python_add_library(_cy MODULE WITH_SOABI "${CYTHON_C}")
target_link_libraries(_cy PRIVATE libsparea)

# ----- 3. Install into the wheel package dir -------------------------

install(TARGETS _cy LIBRARY DESTINATION sparea)
