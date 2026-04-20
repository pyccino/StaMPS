"""csh-compat banner + blank-line printing."""
import os


def banner(prog: str, author: str) -> None:
    print(f"{os.path.basename(prog)} {author}")
    blank_line()


def blank_line() -> None:
    print(" ")
