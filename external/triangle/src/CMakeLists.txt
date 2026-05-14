cmake_minimum_required(VERSION 3.5)
project(triangle)

option(BUILD_EXECUTABLE "Build triangle executable" ON)
option(BUILD_LIBRARY    "Build libtriangle library" ON)

# Triangle's debug-only printf statements cast pointers to `unsigned long`,
# which is 32-bit on LLP64 mingw64. GCC >= 14 promotes the resulting
# truncation warning to an error. Triangle is upstream code we don't want
# to patch line-by-line, so demote it back to a warning here.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  add_compile_options(-fpermissive)
endif()

if(BUILD_LIBRARY)
  add_library(triangle STATIC triangle.cpp)
  target_compile_definitions(triangle PRIVATE -DTRILIBRARY -DANSI_DECLARATORS)
  if(WIN32)
    target_compile_definitions(triangle PRIVATE -DNO_TIMER)
  endif()
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(triangle PRIVATE -fpermissive)
  endif()
  # Generate position independent code
  set_target_properties(triangle PROPERTIES POSITION_INDEPENDENT_CODE ON)
endif()


if(BUILD_EXECUTABLE)
  add_executable(triangle_exec triangle.cpp)
  target_compile_definitions(triangle_exec PRIVATE -DANSI_DECLARATORS)
  if(WIN32)
    target_compile_definitions(triangle_exec PRIVATE -DNO_TIMER)
  endif()
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(triangle_exec PRIVATE -fpermissive)
  endif()
  set_target_properties(triangle_exec PROPERTIES OUTPUT_NAME triangle)
endif()
