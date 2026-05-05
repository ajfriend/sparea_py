cmake_minimum_required(VERSION 3.20)

# Force the dynamic MSVC runtime (/MD), which is what Python extensions
# expect.
cmake_policy(SET CMP0091 NEW)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")

# Match Python's MACOSX_DEPLOYMENT_TARGET so the extension links cleanly.
# Must be set before project().
if(APPLE AND NOT DEFINED CMAKE_OSX_DEPLOYMENT_TARGET)
    if(DEFINED ENV{MACOSX_DEPLOYMENT_TARGET})
        set(CMAKE_OSX_DEPLOYMENT_TARGET "$ENV{MACOSX_DEPLOYMENT_TARGET}")
    else()
        set(CMAKE_OSX_DEPLOYMENT_TARGET "11.0")
    endif()
endif()

project(sparea LANGUAGES CXX)

# ----- 1. Build libsparea via the upstream Zig project ---------------

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
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/bin/sparea.dll")
    set(STAGED_LIB_NAME "libsparea.dll")
elseif(APPLE)
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib/libsparea.dylib")
    set(STAGED_LIB_NAME "libsparea.dylib")
else()
    set(ZIG_OUT_LIB "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib/libsparea.so")
    set(STAGED_LIB_NAME "libsparea.so")
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

# ----- 2. Build the pybind11 extension -------------------------------

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_pb src/cpp/binding.cpp)
add_dependencies(_pb libsparea)

if(WIN32)
    target_link_directories(_pb PRIVATE "${CMAKE_SOURCE_DIR}/src/zig/zig-out/lib")
else()
    target_link_directories(_pb PRIVATE "${CMAKE_BINARY_DIR}/sparea")
endif()
target_link_libraries(_pb PRIVATE sparea)

if(APPLE)
    set_target_properties(_pb PROPERTIES
        BUILD_RPATH "@loader_path"
        INSTALL_RPATH "@loader_path"
    )
elseif(UNIX)
    set_target_properties(_pb PROPERTIES
        BUILD_RPATH "$ORIGIN"
        INSTALL_RPATH "$ORIGIN"
    )
endif()

# ----- 3. Install both into the wheel package dir --------------------

install(TARGETS _pb LIBRARY DESTINATION sparea)
install(FILES "${STAGED_LIB}" DESTINATION sparea)
