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
    # Windows-only source patches applied once after extract:
    #   - NULLFILE "/dev/null" → "NUL" in snaphu.h
    #   - fopen mode promotion to binary ("r" → "rb" etc.) in every .c
    # Done as a CMake script so it runs identically under any host shell.
    PATCH_COMMAND ${CMAKE_COMMAND} -DSNAPHU_SRC_DIR=<SOURCE_DIR>/src
        -P ${CMAKE_CURRENT_SOURCE_DIR}/win-compat/patch_winio.cmake

    CONFIGURE_COMMAND ""
    BUILD_IN_SOURCE 1
    # snaphu's Makefile defaults CC=cc, which MinGW does not ship — override to
    # gcc. Static link removes the MinGW runtime DLL dependency, so the .exe
    # can be dropped into a clean Windows install (matches how the other 8
    # StaMPS Windows binaries are built).
    #
    # On MinGW we shim the POSIX-only <sys/wait.h> and <sys/resource.h> with
    # stub headers under win-compat/. snaphu's fork/wait/getrusage paths are
    # only hit when tile-parallel mode is requested; StaMPS never asks for it,
    # so the stubs are safe (they fail loudly if ever called).
    BUILD_COMMAND ${MAKE_EXECUTABLE} -C <SOURCE_DIR>/src
        CC=gcc
        "CFLAGS=-O3 -Wall -I${CMAKE_CURRENT_SOURCE_DIR}/win-compat -include ${CMAKE_CURRENT_SOURCE_DIR}/win-compat/snaphu_winshim.h -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration -Wno-builtin-declaration-mismatch"
        LDFLAGS=-static
        "LIBS=-lm -lkernel32 -lws2_32"

    # Copy the produced binary + README into INSTALL_DIR. On MinGW gcc
    # adds a .exe extension, so copy the whole bin/ directory contents
    # rather than a single filename — works on Linux/macOS (plain
    # 'snaphu') and Windows-MinGW ('snaphu.exe') identically.
    INSTALL_COMMAND
        ${CMAKE_COMMAND} -E make_directory <INSTALL_DIR>/bin &&
        ${CMAKE_COMMAND} -E copy_directory
            <SOURCE_DIR>/bin
            <INSTALL_DIR>/bin &&
        ${CMAKE_COMMAND} -E copy
            <SOURCE_DIR>/README
            <INSTALL_DIR>/README

    INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}
)
