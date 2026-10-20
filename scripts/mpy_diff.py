"""Run the differential programs of test_bc.py on MicroPython and compare with system bc.

Usage: python scripts/mpy_diff.py [path/to/micropython]
The default interpreter is the unix port built by scripts/fetch_micropython.sh.
"""

import contextlib
import inspect
import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MICROPYTHON = ROOT / ".cache/micropython-1.29.0/ports/unix/build-standard/micropython"

# Reads the whole program from stdin like `bc [-l] < file` (MicroPython streams have no isatty)
DRIVER = """
import sys
import bc_clone
from bc_eval import Evaluator
evaluator = Evaluator(math_enabled={mathlib})
if {mathlib}:
    evaluator.scale = 20
bc_clone.run_non_interactive(evaluator, sys.stdin.read(), "standard input")
"""


def collect_programs() -> list[tuple[str, list[str]]]:
    """Collect (program, flags) from every check_differential call in test_bc.py."""
    sys.path.insert(0, str(ROOT))
    import test_bc

    programs: list[tuple[str, list[str]]] = []

    def record(program: str, flags: list[str] | None = None, match_stderr: bool = False) -> None:  # noqa: ARG001 - same signature as check_differential
        if not program.endswith("\n"):
            program += "\n"
        programs.append((program, flags or []))

    with patch.object(test_bc, "check_differential", record), contextlib.redirect_stdout(io.StringIO()):
        for name, func in inspect.getmembers(test_bc, inspect.isfunction):
            if name.startswith("test_") and not inspect.signature(func).parameters:
                func()
    return programs


def run(cmd: list[str], program: str, env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, input=program, capture_output=True, text=True, env=env, timeout=60)
    return proc.returncode, proc.stdout


def main() -> int:
    micropython = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_MICROPYTHON)
    env = dict(os.environ, MICROPYPATH=str(ROOT))
    programs = collect_programs()
    failures = 0
    for program, flags in programs:
        mathlib = "-l" in flags
        _, expected = run(["bc", *flags], program)
        _, got = run([micropython, "-c", DRIVER.format(mathlib=mathlib)], program, env)
        if got != expected:
            failures += 1
            print(f"MISMATCH flags={flags} program={program!r}\n  bc:          {expected!r}\n  micropython: {got!r}")
    print(f"{len(programs) - failures}/{len(programs)} programs match system bc")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
