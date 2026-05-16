/* Windows/MinGW compat stub for <sys/wait.h>.
 *
 * snaphu links fork/wait/kill only on the tile-parallel code path.
 * StaMPS invokes snaphu without tiling, so these symbols are linked but never
 * executed. We provide inline stubs that fail loudly if someone ever calls
 * them on Windows. */
#ifndef SNAPHU_WIN_COMPAT_SYS_WAIT_H
#define SNAPHU_WIN_COMPAT_SYS_WAIT_H

#include <sys/types.h>
#include <errno.h>

#ifndef WIFEXITED
#define WIFEXITED(status)   (((status) & 0x7f) == 0)
#endif
#ifndef WEXITSTATUS
#define WEXITSTATUS(status) (((status) >> 8) & 0xff)
#endif
#ifndef WIFSIGNALED
#define WIFSIGNALED(status) (((status) & 0x7f) != 0 && ((status) & 0x7f) != 0x7f)
#endif
#ifndef WTERMSIG
#define WTERMSIG(status)    ((status) & 0x7f)
#endif

#ifndef SIGKILL
#define SIGKILL 9
#endif

/* sleep() and getpid() are already provided by MinGW's <unistd.h>/<process.h>. */
static inline pid_t fork(void) { errno = ENOSYS; return (pid_t)-1; }
static inline pid_t wait(int *status) { (void)status; errno = ECHILD; return (pid_t)-1; }
static inline pid_t waitpid(pid_t pid, int *status, int options) {
    (void)pid; (void)status; (void)options; errno = ECHILD; return (pid_t)-1;
}
static inline int kill(pid_t pid, int sig) {
    (void)pid; (void)sig; errno = ESRCH; return -1;
}

#endif
