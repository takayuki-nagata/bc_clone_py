import subprocess
import sys
from pathlib import Path
import pytest

# Paths to the clone script
CLONE_PATH = str(Path(__file__).parent / "bc_clone.py")

def run_oracle_bc(program: str, flags: list[str] = []) -> tuple[int, str, str]:
    """Run the system `bc` utility and return (exit_code, stdout, stderr)."""
    cmd = ["bc"] + flags
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=program)
    return proc.returncode, stdout, stderr

def run_clone_bc(program: str, flags: list[str] = []) -> tuple[int, str, str]:
    """Run our Python bc clone and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, CLONE_PATH] + flags
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=program)
    return proc.returncode, stdout, stderr

def check_differential(program: str, flags: list[str] = [], match_stderr: bool = False) -> None:
    """Assert that the clone output matches the system bc output exactly."""
    if not program.endswith("\n"):
        program += "\n"
    oracle_code, oracle_out, oracle_err = run_oracle_bc(program, flags)
    clone_code, clone_out, clone_err = run_clone_bc(program, flags)

    # Normalize outputs (stripping trailing whitespace/newlines for minor differences)
    # but maintaining structural newline layout
    assert clone_out == oracle_out, (
        f"Stdout mismatch!\n"
        f"Program: {program!r}\n"
        f"Expected:\n{oracle_out!r}\n"
        f"Got:\n{clone_out!r}"
    )

    if match_stderr:
        # Standard POSIX bc stderr is implementation-dependent, but we check if both have error
        has_oracle_err = len(oracle_err.strip()) > 0
        has_clone_err = len(clone_err.strip()) > 0
        assert has_clone_err == has_oracle_err, (
            f"Stderr mismatch!\n"
            f"Expected error: {has_oracle_err} ({oracle_err!r})\n"
            f"Got: {has_clone_err} ({clone_err!r})"
        )

# --- 1. Basic Arithmetic Tests ---

def test_basic_arithmetic() -> None:
    programs = [
        "1 + 2",
        "5 - 3",
        "4 * 3",
        "10 / 3",
        "10 % 3",
        "-5 + 3",
        "3 * -2",
        "2^3",
        "2^0",
        "2.5^2",
        "2.5^0",
        "2.5^-2",
        "1.2345 + 5.6789",
        "10.000 - 0.001",
        "0.1234 * 0.5678",
        "1 / 7",
        "1.0 / 7",
        "3.2 % 1",
        "0 % 5",
        "2^-3",
    ]
    for prog in programs:
        check_differential(prog)

# --- 2. Operator Precedence and Associativity Tests ---

def test_precedence_and_associativity() -> None:
    programs = [
        "2 + 3 * 4",
        "2 * 3 + 4",
        "10 - 4 - 3",
        "2 ^ 3 ^ 2",  # Right-to-left
        "(2 + 3) * 4",
        "2 * (3 + 4)",
        "2 + 3 * 4 ^ 2",
        "2 * 3 ^ 2 + 4",
        "a = 3; b = 4; a + b",
        "a = b = 5; a * b",  # Right-to-left assignment
        "a = 2; b = 3; c = 4; a += b *= c; a; b; c",
    ]
    for prog in programs:
        check_differential(prog)

# --- 3. Increment / Decrement Tests ---

def test_incr_decr() -> None:
    programs = [
        "a = 5; ++a",
        "a = 5; a++",
        "a = 5; --a",
        "a = 5; a--",
        "a = 5; b = ++a; a; b",
        "a = 5; b = a++; a; b",
        "a = 5; b = --a; a; b",
        "a = 5; b = a--; a; b",
        "a = 5; ++a + a++",
        "a = 5; a[0] = 10; ++a[0]; a[0]++",
        "scale = 5; a = 2.5; ++a; a++",
    ]
    for prog in programs:
        check_differential(prog)

# --- 4. Scale Rules Tests ---

def test_scale_propagation() -> None:
    programs = [
        "scale = 5; 3 / 2",
        "scale = 0; 3 / 2",
        "scale = 10; 1 / 3",
        "scale = 2; a = 1.23; b = 4.567; a + b",
        "scale = 2; a = 1.23; b = 4.567; a - b",
        "scale = 2; a = 1.23; b = 4.567; a * b",
        "scale = 2; a = 1.23; b = 4.567; a / b",
        "scale = 2; a = 1.23; b = 4.567; a % b",
        "scale = 5; 2.5 ^ 3",
        "scale = 5; 2.5 ^ -3",
        "scale = 2; scale",
        "scale = 3; a = scale = 5; scale; a",
    ]
    for prog in programs:
        check_differential(prog)

# --- 5. Built-in Functions Tests ---

def test_builtin_functions() -> None:
    programs = [
        "length(123.45)",
        "length(0.0012)",
        "length(0)",
        "length(-12.34)",
        "length(001.20)",
        "length(0.000)",
        "length(100.00)",
        "scale(123.45)",
        "scale(0.0012)",
        "scale(0)",
        "scale(-12.34)",
        "scale(001.20)",
        "sqrt(2)",
        "scale = 5; sqrt(2)",
        "scale = 2; sqrt(0.04)",
        "scale = 1; sqrt(0.04)",
        "sqrt(0)",
        "sqrt(100)",
        "length(sqrt(2))",
        "scale(sqrt(2))",
    ]
    for prog in programs:
        check_differential(prog)

def test_builtin_errors() -> None:
    # Negative sqrt is an error
    check_differential("sqrt(-2)", match_stderr=True)

# --- 6. Variables, Arrays and Scoping Tests ---

def test_variables_and_arrays() -> None:
    programs = [
        "a = 5; a",
        "z = 10; z",
        "a[0] = 5; a[0]",
        "a[10] = 20; a[10]",
        "a[1.9] = 15; a[1]",  # Truncates index
        "a[0]; a[1]; a[100]",  # Defaults to 0
        "scale = 2; a[5.5] = 2.5; a[5]; scale(a[5])",
        "a = 2; a[2] = 5; a; a[2]",  # Distinct variable and array spaces
    ]
    for prog in programs:
        check_differential(prog)

# --- 7. Input / Output Base Conversions Tests ---

def test_bases() -> None:
    programs = [
        "ibase = 8; 10",
        "ibase = 16; A",
        "ibase = 16; FF",
        "ibase = 16; 1A.8",
        "obase = 2; 10",
        "obase = 8; 10",
        "obase = 16; 255",
        "obase = 25; 1024",
        "obase = 125; 1024",
        "scale = 2; obase = 8; 0.15",
        "scale = 2; obase = 16; 0.5/1",
        "scale = 2; obase = 25; 1.04",
        "scale = 2; obase = 25; 0.00",
        "scale = 2; obase = 25; 0.04",
        "scale = 2; obase = 25; -0.04",
        "ibase = 8; obase = 12; 10",  # obase becomes 10 (12 in base 8 is 10)
        "ibase = A; obase = A; 10",   # Single letter sets to base 10 in hex
        "ibase = 16; a = FF; obase = 10; a",
    ]
    for prog in programs:
        check_differential(prog)

# --- 8. Line Wrapping Tests ---

def test_line_wrapping() -> None:
    programs = [
        "2^300",
        "obase=25; 2^150",
        '"12345678901234567890123456789012345678901234567890123456789012345678901234567890"',
    ]
    for prog in programs:
        check_differential(prog)

# --- 9. Control Flow Tests ---

def test_control_flow() -> None:
    programs = [
        "if (1 == 1) 5",
        "if (1 == 0) 5",
        "if (1 < 2) 10",
        "a = 0; while (a < 5) a = a + 1; a",
        "a = 0; for (i = 0; i < 5; ++i) a = a + i; a; i",
        "a = 0; while (1) { a = a + 1; if (a == 3) break; }; a",
        "a = 0; for (i = 0; 1; ++i) { a = a + i; if (i == 4) break; }; a; i",
        "1; quit; 2",
        "if (1 == 1) { 10; 20; }",
        "a = 1; if (a) 5",  # POSIX relational check: 0 is false, non-zero is true
    ]
    for prog in programs:
        check_differential(prog)

# --- 10. Functions and Dynamic Scoping Tests ---

def test_functions_and_scoping() -> None:
    programs = [
        # Basic function definition and return
        "define f(x) { return (x * 2); }; f(5)",
        # Function returning 0 implicitly
        "define f() { a = 10; }; f()",
        # Auto variables (dynamic scoping)
        "a = 100;\ndefine f() { auto a; a = 5; g(); };\ndefine g() { a; };\nf(); a",
        # Auto arrays
        "a[0] = 100;\ndefine f() { auto a[]; a[0] = 5; g(); };\ndefine g() { a[0]; };\nf(); a[0]",
        # Array parameters (pass by value)
        "define f(x[]) { x[0] = 99; return(x[0]); };\na[0] = 5;\nf(a[]); a[0]",
        # Recursion (Factorial)
        "define f(x) { if (x <= 1) return(1); return (x * f(x-1)); }; f(5)",
        # Recursion (Fibonacci)
        "define fib(n) { if (n <= 1) return(n); return (fib(n-1) + fib(n-2)); }; fib(8)",
        # Redefining function
        "define f() { return (1); }; f(); define f() { return (2); }; f()",
    ]
    for prog in programs:
        check_differential(prog)

# --- 11. Math Library (-l) Tests ---

def test_math_library() -> None:
    flags = ["-l"]
    programs = [
        "s(0)",
        "s(0.5)",
        "s(-0.5)",
        "c(0)",
        "c(0.5)",
        "c(-0.5)",
        "a(0)",
        "a(1)",
        "a(-1)",
        "a(0.5)",
        "l(1)",
        "l(2)",
        "l(0.5)",
        "e(0)",
        "e(1)",
        "e(-1)",
        "e(0.5)",
        "j(0, 0)",
        "j(0, 1.5)",
        "j(1, 2.0)",
        "j(2, 2.5)",
        # Nested math operations
        "s(c(0.5))",
        "a(s(1)/c(1))",
        "scale = 25; s(1.0)",
        "scale = 10; e(1)",
    ]
    for prog in programs:
        check_differential(prog, flags=flags)

def test_math_library_errors() -> None:
    flags = ["-l"]
    # Domain error: log of negative number
    check_differential("l(-1)", flags=flags, match_stderr=True)
    check_differential("l(0)", flags=flags, match_stderr=True)

# --- 12. Lexical Rules and Comments Tests ---

def test_lexical_rules() -> None:
    programs = [
        "1 /* comment */ + 2",
        "1 /* multi-line\ncomment */ + 2",
        "a = 5\n b = 10\n a + b",
        "a = 5\\\n+ 10; a",  # Backslash-newline
        "\"hello world\"",
        "\"hello \\\nworld\"",  # Backslash-newline inside string
        "1.2\\\n34 + 1",      # Backslash-newline in number constant
    ]
    for prog in programs:
        check_differential(prog)

# --- 13. End-to-End (E2E) Highly Complex Calculations ---

def test_e2e_complex_calculations() -> None:
    # A highly complex program testing:
    # - scale adjustments
    # - ibase and obase switches
    # - recursive functions with auto variables and arrays
    # - loops, conditionals, and math functions
    complex_program = """
    scale = 15
    define pi() {
        return (4 * a(1))
    }
    
    define taylor_sin(x, n) {
        auto sum, term, i
        sum = 0
        term = x
        for (i = 1; i <= n; ++i) {
            sum = sum + term
            term = -term * x * x / ((2*i) * (2*i + 1))
        }
        return (sum)
    }

    /* Compute values */
    p = pi()
    p
    s(p/6)  /* sin(pi/6) = 0.5 */
    taylor_sin(p/6, 10)

    /* Test base conversions and dynamic arrays */
    obase = 16
    "pi in base 16: "
    p
    
    obase = 10
    define test_scoping(n) {
        auto val[], i
        for (i = 0; i < n; ++i) {
            val[i] = i * i
        }
        return (sum_array(val[], n))
    }
    
    define sum_array(arr[], size) {
        auto i, s
        s = 0
        for (i = 0; i < size; ++i) {
            s = s + arr[i]
        }
        return (s)
    }
    
    test_scoping(10)
    
    /* Nesting and relational ops */
    a = 10
    b = 20
    if (a < b && b > 15) {
        "ok"
    }
    """
    check_differential(complex_program, flags=["-l"])
