cmake_minimum_required(VERSION 3.20)
project(triangle LANGUAGES C CXX)

# Triangle includes <sys/resource.h>, <unistd.h> which don't exist on MSVC.
# ANSI_DECLARATORS uses ISO C function prototypes.
# NO_TIMER disables gettimeofday() (Windows / MSVC).
# Do NOT define TRILIBRARY here: it removes the main() entry point and
# turns the source into a library-only build. StaMPS' ps_scn_filt and
# friends require the standalone `triangle` executable on PATH.
# The libigl mirror ships triangle.cpp (Shewchuk's original triangle.c, renamed
# so it compiles cleanly as C++ without warnings). We build it with the C++
# compiler since that's the supported upstream path.
add_executable(triangle src/triangle.cpp)
target_compile_definitions(triangle PRIVATE ANSI_DECLARATORS)
if(WIN32)
    target_compile_definitions(triangle PRIVATE NO_TIMER)
endif()
if(MSVC)
    target_compile_definitions(triangle PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()

# Output the executable into the bin/ subdir of the source tree so
# mt_prep_snap.bat's PATH (which prepends <STAMPS>/external/triangle/bin)
# can find it without an explicit install step.
set_target_properties(triangle PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CURRENT_SOURCE_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/bin"
)

install(TARGETS triangle RUNTIME DESTINATION bin)
