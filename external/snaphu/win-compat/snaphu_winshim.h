/* Force-included via gcc -include on Windows/MinGW builds of snaphu.
 * Centralises Windows ↔ POSIX shims that need preprocessor-level rewrites
 * (e.g. mkdir's signature mismatch) so they can't be tripped by shell
 * quoting from CMake/Make. */
#ifndef SNAPHU_WIN_SHIM_H
#define SNAPHU_WIN_SHIM_H

#include <io.h>
#include <direct.h>

/* POSIX mkdir takes (path, mode); Windows' takes (path). Discard mode. */
#define mkdir(path, mode) _mkdir(path)

/* POSIX signals absent on Windows. snaphu installs handlers for clean exit;
 * Windows never delivers these so the values are placeholders that
 * signal()/raise() will accept without effect. */
#ifndef SIGHUP
#define SIGHUP 1
#endif
#ifndef SIGQUIT
#define SIGQUIT 3
#endif
#ifndef SIGPIPE
#define SIGPIPE 13
#endif
#ifndef SIGALRM
#define SIGALRM 14
#endif
#ifndef SIGBUS
#define SIGBUS 7
#endif

#endif
