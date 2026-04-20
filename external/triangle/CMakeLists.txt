cmake_minimum_required(VERSION 3.20)
project(triangle LANGUAGES C CXX)

# Triangle includes <sys/resource.h>, <unistd.h> which don't exist on MSVC.
# TRILIBRARY disables main-program entry; NO_TIMER disables gettimeofday();
# ANSI_DECLARATORS uses ISO C function prototypes.
# The libigl mirror ships triangle.cpp (Shewchuk's original triangle.c, renamed
# so it compiles cleanly as C++ without warnings). We build it with the C++
# compiler since that's the supported upstream path.
add_executable(triangle src/triangle.cpp)
target_compile_definitions(triangle PRIVATE TRILIBRARY ANSI_DECLARATORS)
if(MSVC)
    target_compile_definitions(triangle PRIVATE _CRT_SECURE_NO_WARNINGS NO_TIMER)
endif()

install(TARGETS triangle RUNTIME DESTINATION bin)
