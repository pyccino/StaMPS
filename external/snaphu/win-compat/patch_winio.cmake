# Windows/MinGW build patches for snaphu, applied once via ExternalProject_Add
# PATCH_COMMAND.
#
# (1) NULLFILE: "/dev/null" → "NUL" in snaphu.h.
# (2) fopen mode: promote "r"/"w"/"a" to "rb"/"wb"/"ab" in every snaphu .c
#     file so Windows doesn't do CR/LF translation on raw binary I/O
#     (COMPLEX_DATA, FLOAT_DATA, ALT_LINE_DATA, dump files).
#     Exception: snaphu's config file is parsed with sscanf("%s %s"), which
#     would leave trailing \r in str2 on a "rb" read of a CRLF file and
#     break string comparisons. Preserve fopen(conffile,"r").
if(NOT WIN32)
    return()
endif()
if(NOT EXISTS "${SNAPHU_SRC_DIR}")
    message(FATAL_ERROR "patch_winio: ${SNAPHU_SRC_DIR} not found")
endif()

# (1) snaphu.h: NULLFILE → "NUL"
set(_header "${SNAPHU_SRC_DIR}/snaphu.h")
if(EXISTS "${_header}")
    file(READ "${_header}" _content)
    string(REPLACE "\"/dev/null\"" "\"NUL\"" _content "${_content}")
    file(WRITE "${_header}" "${_content}")
    message(STATUS "snaphu winio patch: NULLFILE → NUL in snaphu.h")
endif()

# (2) Every .c: promote fopen modes to binary
file(GLOB _sources "${SNAPHU_SRC_DIR}/*.c")
set(_PRESERVE "_SNAPHU_TEXT_MODE_PRESERVE_")
foreach(_src IN LISTS _sources)
    file(READ "${_src}" _content)

    # Stash the conffile fopen so the blanket regex doesn't catch it.
    string(REPLACE
        "fopen(conffile,\"r\")"
        "fopen(conffile,\"${_PRESERVE}\")"
        _content "${_content}")

    # Promote all remaining fopen modes. Match any single-letter mode string
    # so we don't mangle already-binary "rb"/"wb"/"ab" if the upstream ever
    # adds them.
    string(REGEX REPLACE
        "fopen\\(([^)]+),\"r\"\\)"
        "fopen(\\1,\"rb\")"
        _content "${_content}")
    string(REGEX REPLACE
        "fopen\\(([^)]+),\"w\"\\)"
        "fopen(\\1,\"wb\")"
        _content "${_content}")
    string(REGEX REPLACE
        "fopen\\(([^)]+),\"a\"\\)"
        "fopen(\\1,\"ab\")"
        _content "${_content}")

    # Restore preserved conffile.
    string(REPLACE
        "fopen(conffile,\"${_PRESERVE}\")"
        "fopen(conffile,\"r\")"
        _content "${_content}")

    file(WRITE "${_src}" "${_content}")
endforeach()
message(STATUS "snaphu winio patch: fopen modes → binary in ${SNAPHU_SRC_DIR}")
