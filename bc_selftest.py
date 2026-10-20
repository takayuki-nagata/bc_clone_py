"""Self-tests with embedded expected output, for targets without a system bc (MicroPython)."""

import gc
import io

from bc_eval import Evaluator
from bc_parser import Lexer, Parser

# (name, mathlib, program, expected stdout); expected values come from GNU bc
CASES: list[tuple[str, bool, str, str]] = [
    ("arithmetic", False, "1 + 2 * 3 - 4 / 2; (1 + 2) * 3; 7 % 3; -5 + 3; 2 ^ 10\n", "5\n9\n1\n-2\n1024\n"),
    ("scale division", False, "scale = 10; 1 / 3; 22 / 7; -7 / 2\n", ".3333333333\n3.1428571428\n-3.5000000000\n"),
    ("2^100", False, "2 ^ 100\n", "1267650600228229401496703205376\n"),
    (
        "2^300 line wrap",
        False,
        "2 ^ 300\n",
        "20370359763344860862684456884093781610514683936659362506361404493543\\\n81299763336706183397376\n",
    ),
    (
        "recursive f(20)",
        False,
        "define f(n) { if (n < 2) return (1); return (n * f(n - 1)); }\nf(20)\n",
        "2432902008176640000\n",
    ),
    ("hex to binary", False, "ibase = 16; obase = 2; FF; obase = 10; 1A\n", "11111111\n1A\n"),
    (
        "arrays and auto",
        False,
        "define g(n) { auto i, a[]; for (i = 0; i < n; i++) a[i] = i * i; return (a[n - 1]); }\ng(10)\n",
        "81\n",
    ),
    ("while loop", False, "i = 0; s = 0; while (i < 100) { i = i + 1; s = s + i }; s\n", "5050\n"),
    ("sqrt(2)", False, "scale = 30; sqrt(2)\n", "1.414213562373095048801688724209\n"),
    ("-l 4*a(1)", True, "4 * a(1)\n", "3.14159265358979323844\n"),
    ("-l e(1)", True, "e(1)\n", "2.71828182845904523536\n"),
    ("-l l(e)", True, "l(2.718281828459045)\n", ".99999999999999991341\n"),
    ("-l s(1)", True, "s(1)\n", ".84147098480789650665\n"),
    ("-l c(1)", True, "c(1)\n", ".54030230586813971740\n"),
    ("-l j(1,1)", True, "j(1, 1)\n", ".44005058574493351595\n"),
    ("-l pi scale 50", True, "scale = 50; 4 * a(1)\n", "3.14159265358979323846264338327950288419716939937508\n"),
]


def run_case(mathlib: bool, program: str) -> str:
    """Run a bc program in a fresh evaluator and return its stdout."""
    out = io.StringIO()
    evaluator = Evaluator(math_enabled=mathlib, stdout_stream=out)
    if mathlib:
        evaluator.scale = 20
    evaluator.execute(Parser(Lexer(program)).parse_program())
    return out.getvalue()


def run() -> bool:
    """Run all self-tests, print one line per case and a summary, and return True if all passed."""
    mem_alloc = getattr(gc, "mem_alloc", None)
    peak = 0
    failed = []
    for name, mathlib, program, expected in CASES:
        gc.collect()
        try:
            got = run_case(mathlib, program)
        except Exception as e:
            got = "exception: " + repr(e)
        if mem_alloc is not None:  # pragma: no cover - MicroPython only
            peak = max(peak, mem_alloc())
        if got == expected:
            print(name + " ... [PASS]")
        else:
            failed.append(name)
            print(name + " ... [FAIL]")
            print("  expected: " + repr(expected))
            print("  got:      " + repr(got))
    if mem_alloc is not None:  # pragma: no cover - MicroPython only
        print("heap after cases (max): " + str(peak) + " bytes")
    if failed:
        print("BC SELF-TESTS FAILED: " + str(len(failed)) + "/" + str(len(CASES)) + " (" + ", ".join(failed) + ")")
        return False
    print("ALL BC SELF-TESTS PASSED")
    return True
