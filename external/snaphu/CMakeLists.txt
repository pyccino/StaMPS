cmake_minimum_required(VERSION 3.20)
project(snaphu_external LANGUAGES C)
include(ExternalProject)

set(SNAPHU_VERSION "v2.0.6")
# SHA256 computed at plan-execution time (2026-04-20) from:
#   curl -sL https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/snaphu-v2.0.6.tar.gz | sha256sum
set(SNAPHU_SHA256 "ce481c8d8d4c1e8fffeb5a9052a68bf48e6dd955293a30f6769d5bbb4df7a998")

ExternalProject_Add(snaphu
    URL "https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/snaphu-${SNAPHU_VERSION}.tar.gz"
    URL_HASH SHA256=${SNAPHU_SHA256}
    # Stanford's URL is occasionally down; fallback mirror (also SHA-pinned):
    # URL "https://github.com/nasa-jpl/snaphu/archive/refs/tags/${SNAPHU_VERSION}.tar.gz"
    SOURCE_SUBDIR src
    CMAKE_ARGS
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
    # snaphu has POSIX-isms (getopt.h, unistd.h); apply patches for MSVC:
    PATCH_COMMAND
        ${CMAKE_COMMAND} -E copy
            ${CMAKE_CURRENT_SOURCE_DIR}/snaphu-msvc.patch
            <SOURCE_DIR>/snaphu-msvc.patch &&
        cd <SOURCE_DIR> && patch -p1 -N < snaphu-msvc.patch || true
    INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}
)
