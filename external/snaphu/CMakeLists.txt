cmake_minimum_required(VERSION 3.20)
project(snaphu_external LANGUAGES C)
include(ExternalProject)

set(SNAPHU_VERSION "v2.0.6")
# SHA256 computed from:
#   curl -sL https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/snaphu-v2.0.6.tar.gz | sha256sum
set(SNAPHU_SHA256 "ce481c8d8d4c1e8fffeb5a9052a68bf48e6dd955293a30f6769d5bbb4df7a998")

# snaphu relies on POSIX primitives (fork, getrusage, unistd.h) that MSVC
# CRT does not ship. Full MSVC port is out of scope. Users on Windows
# should build under MSYS2/MinGW (where snaphu's stock Makefile works) or
# obtain a pre-built snaphu binary. The Windows release artifact bundles
# the MinGW-built snaphu.
if(MSVC)
    message(STATUS
        "snaphu: MSVC toolchain detected. snaphu cannot be built with "
        "MSVC (requires POSIX fork/getrusage). Build under MSYS2/MinGW "
        "or install a pre-built snaphu binary into external/snaphu/bin/.")
    return()
endif()

find_program(MAKE_EXECUTABLE NAMES gmake make mingw32-make REQUIRED)

ExternalProject_Add(snaphu
    URL "https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/snaphu-${SNAPHU_VERSION}.tar.gz"
    URL_HASH SHA256=${SNAPHU_SHA256}

    # snaphu ships a plain GNU Makefile under src/, no CMakeLists.txt — so
    # drive its own build system directly. BINDIR=../bin keeps the binary
    # inside <SOURCE_DIR>/bin/, which INSTALL_COMMAND copies to our
    # install prefix.
    CONFIGURE_COMMAND ""
    BUILD_IN_SOURCE 1
    BUILD_COMMAND ${MAKE_EXECUTABLE} -C <SOURCE_DIR>/src

    # Copy the produced binary + LICENSE + man page into INSTALL_DIR.
    # Using CMake's portable copy primitives keeps this working on
    # Linux, macOS, and MinGW without shell-dependent install targets.
    INSTALL_COMMAND
        ${CMAKE_COMMAND} -E make_directory <INSTALL_DIR>/bin &&
        ${CMAKE_COMMAND} -E copy
            <SOURCE_DIR>/bin/snaphu
            <INSTALL_DIR>/bin/snaphu &&
        ${CMAKE_COMMAND} -E copy
            <SOURCE_DIR>/README
            <INSTALL_DIR>/README

    INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}
)
