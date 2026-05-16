/* Windows/MinGW compat stub for <sys/resource.h>.
 *
 * Only consumed by snaphu_util.c's GetTimers/GetCPUTime routines. We return
 * zeroed rusage so cumulative-CPU stats print as 0.00s on Windows. */
#ifndef SNAPHU_WIN_COMPAT_SYS_RESOURCE_H
#define SNAPHU_WIN_COMPAT_SYS_RESOURCE_H

#include <sys/types.h>
#include <sys/time.h>
#include <string.h>

#define RUSAGE_SELF     0
#define RUSAGE_CHILDREN (-1)

#define PRIO_PROCESS 0
#define PRIO_PGRP    1
#define PRIO_USER    2

struct rusage {
    struct timeval ru_utime;
    struct timeval ru_stime;
    long ru_maxrss, ru_ixrss, ru_idrss, ru_isrss;
    long ru_minflt, ru_majflt, ru_nswap;
    long ru_inblock, ru_oublock;
    long ru_msgsnd, ru_msgrcv;
    long ru_nsignals, ru_nvcsw, ru_nivcsw;
};

static inline int getrusage(int who, struct rusage *usage) {
    (void)who;
    if (usage) memset(usage, 0, sizeof(*usage));
    return 0;
}
static inline int setpriority(int which, int who, int prio) {
    (void)which; (void)who; (void)prio; return 0;
}

#endif
