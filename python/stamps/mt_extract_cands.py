"""Stub for python/stamps/mt_extract_cands.

The authoritative implementation is delivered by Task 2b.2 on a sibling
branch. `mt_prep_snap` imports `mt_extract_cands.main` after it has
finished writing its own artifacts, so the tests in this task only need
the name to exist.  A minimal noop keeps the import graph intact.
"""
from __future__ import annotations


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    # Real implementation arrives with Task 2b.2.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
