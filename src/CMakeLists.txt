# StaMPS core binaries — CMake build system (authoritative).
# Makefile kept alongside as deprecated.
#
# Usage:
#   cmake -S src -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build --config Release
#
# Produces 7 executables into <repo>/bin/ (matching StaMPS_CONFIG PATH).

cmake_minimum_required(VERSION 3.20)
project(StaMPS_tools LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Install dir matches Makefile's INSTALL_DIR=../bin
set(STAMPS_BIN_DIR "${CMAKE_SOURCE_DIR}/../bin"
    CACHE PATH "StaMPS binary install directory")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${STAMPS_BIN_DIR}")
# Match for every multi-config generator (MSVC etc.)
foreach(_cfg IN ITEMS Debug Release RelWithDebInfo MinSizeRel)
    string(TOUPPER "${_cfg}" _CFG)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${_CFG} "${STAMPS_BIN_DIR}")
endforeach()

# Compiler flags
if(MSVC)
    add_compile_options(/W3 /permissive- /wd5033)   # /wd5033 = 'register' deprecated
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
    # Static CRT so release .exe has no VC++ Redist dependency.
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
else()
    add_compile_options(-O3 -Wall -Wno-deprecated-register)
    # Workaround GCC >= 10 selpsc/selsbc segfault (see Task 1.5).
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        add_compile_options(-fno-strict-aliasing)
    endif()
endif()

# Core binaries (portable, built on all platforms)
set(CORE_TARGETS
    calamp cpxsum
    pscphase pscdem psclonlat
    selpsc_patch selsbc_patch
)
foreach(tgt IN LISTS CORE_TARGETS)
    add_executable(${tgt} ${tgt}.cpp)
    target_include_directories(${tgt} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
endforeach()

# dismph: Linux/macOS (X11 + Motif); NOT MinGW (no X11 on MinGW).
# macOS builds work if XQuartz + Motif (Homebrew `motif`) are installed.
option(BUILD_DISMPH "Build the X11/Motif display tool (Unix only)" OFF)
if(BUILD_DISMPH AND UNIX AND NOT MINGW)
    find_package(X11 REQUIRED)
    find_library(MOTIF_LIB Xm)
    if(NOT MOTIF_LIB)
        message(FATAL_ERROR
            "BUILD_DISMPH=ON but libXm not found. "
            "Install libmotif-dev (Debian/Ubuntu) or motif-devel (Fedora/RHEL).")
    endif()
    add_executable(dismph
        dismph.cpp CDisp.cpp CDispComp.cpp CGetData.cpp XInfo.cpp bytescale.cpp)
    target_include_directories(dismph PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${X11_INCLUDE_DIR})
    target_link_libraries(dismph PRIVATE
        ${X11_LIBRARIES} ${MOTIF_LIB} Xt Xp Xext)
endif()

install(TARGETS ${CORE_TARGETS} RUNTIME DESTINATION "${STAMPS_BIN_DIR}")

enable_testing()
# Usage-path smoke tests: run each binary with no args and assert it produces
# output. Most binaries also exit nonzero on the usage path (WILL_FAIL catches
# that), but cpxsum exits 0 — for it, we only assert a non-empty stdout/stderr
# via PASS_REGULAR_EXPRESSION on the banner. Changing cpxsum's exit code is a
# behavioral change for csh pipelines that depend on it.
foreach(tgt IN LISTS CORE_TARGETS)
    add_test(NAME ${tgt}_usage COMMAND ${tgt})
endforeach()
# All binaries EXCEPT cpxsum exit nonzero on no-args; mark those WILL_FAIL.
set_tests_properties(
    calamp_usage pscphase_usage pscdem_usage psclonlat_usage
    selpsc_patch_usage selsbc_patch_usage
    PROPERTIES WILL_FAIL TRUE)
# cpxsum exits 0 but prints its usage banner. Assert the banner text is seen.
set_tests_properties(cpxsum_usage PROPERTIES
    PASS_REGULAR_EXPRESSION "usage: cpxsum")
