import io
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import bc_clone

# Paths to the clone script
CLONE_PATH = str(Path(__file__).parent / "bc_clone.py")


def run_oracle_bc(program: str, flags: list[str] | None = None) -> tuple[int, str, str]:
    """Run the system `bc` utility and return (exit_code, stdout, stderr)."""
    if flags is None:
        flags = []
    cmd = ["bc"] + flags
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(input=program)
    return proc.returncode, stdout, stderr


def run_clone_bc(program: str, flags: list[str] | None = None) -> tuple[int, str, str]:
    """Run our Python bc clone in-process and return (exit_code, stdout, stderr)."""
    if flags is None:
        flags = []
    argv = ["bc_clone.py"] + flags
    stdin = io.StringIO(program)
    stdout = io.StringIO()
    stderr = io.StringIO()

    with patch("sys.argv", argv), patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
        try:
            bc_clone.main()
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 0
        except Exception as e:
            stderr.write(f"Exception: {e}\n")
            exit_code = 1

    return exit_code, stdout.getvalue(), stderr.getvalue()


def check_differential(program: str, flags: list[str] | None = None, match_stderr: bool = False) -> None:
    """Assert that the clone output matches the system bc output exactly."""
    if flags is None:
        flags = []
    if not program.endswith("\n"):
        program += "\n"
    oracle_code, oracle_out, oracle_err = run_oracle_bc(program, flags)
    clone_code, clone_out, clone_err = run_clone_bc(program, flags)

    # Normalize outputs (stripping trailing whitespace/newlines for minor differences)
    # but maintaining structural newline layout
    assert clone_out == oracle_out, (
        f"Stdout mismatch!\nProgram: {program!r}\nExpected:\n{oracle_out!r}\nGot:\n{clone_out!r}"
    )

    if match_stderr:
        # Standard POSIX bc stderr is implementation-dependent, but we check if both have error
        has_oracle_err = len(oracle_err.strip()) > 0
        has_clone_err = len(clone_err.strip()) > 0
        assert has_clone_err == has_oracle_err, (
            f"Stderr mismatch!\nExpected error: {has_oracle_err} ({oracle_err!r})\nGot: {has_clone_err} ({clone_err!r})"
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
    # Division and modulo by zero are errors
    check_differential("1 / 0", match_stderr=True)
    check_differential("1 % 0", match_stderr=True)
    check_differential("a = 1; a /= 0", match_stderr=True)
    check_differential("a = 1; a %= 0", match_stderr=True)


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
        "obase = 1000; scale = 6; 1/7",
        "obase = 17; scale = 5; -1/3",
        "scale = 2; obase = 25; -0.04",
        "ibase = 8; obase = 12; 10",  # obase becomes 10 (12 in base 8 is 10)
        "ibase = A; obase = A; 10",  # Single letter sets to base 10 in hex
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
        "s(4)",
        "s(-4)",
        "c(0)",
        "c(0.5)",
        "c(-0.5)",
        "c(4)",
        "c(-4)",
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
        "j(-2, 2.5)",
        # Nested math operations
        "s(c(0.5))",
        "a(s(1)/c(1))",
        "scale = 25; s(1.0)",
        "scale = 10; e(1)",
        # Large magnitudes and high scales (integer fixed-point precision)
        "e(100)",
        "e(-30)",
        "l(10^30)",
        "l(0.0000001)",
        "j(3, -7.5)",
        "j(-1, 0.5)",
        "scale = 50; 4*a(1)",
        "scale = 40; a(-123)",
        "scale = 30; c(-20)",
        "scale = 60; sqrt(2)",
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
        "a = 5 + \\\n10; a",  # Backslash-newline
        '"hello world"',
        '"hello \\\nworld"',  # Backslash-newline inside string
        "1.2\\\n34 + 1",  # Backslash-newline in number constant
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
    if (a < b) {
        if (b > 15) {
            "ok"
        }
    }
    """
    check_differential(complex_program, flags=["-l"])


def test_parser_and_evaluator_edge_cases() -> None:
    # 1. Valid edge cases
    check_differential("a = 5; a ^= 2; a")
    check_differential("a = 5; a -= 2; a")
    check_differential("5 >= 2")
    check_differential("5 != 2")
    check_differential("{ 1 }")
    check_differential("define f() { return; }; f()")
    check_differential("a")  # Default to 0
    check_differential("1.2 > 1.23")  # Comparisons with different scales
    check_differential("1.23 > 1.2")
    check_differential("++a; a")  # Increment undefined variable
    check_differential("++a[0]; a[0]")  # Increment undefined array
    check_differential("scale = 5; ++scale; scale")  # Register update
    check_differential("ibase = 10; ++ibase; ibase")
    check_differential("obase = 10; ++obase; obase")
    check_differential("define f(x[]) { return(1); }; f(a[])")  # Uninitialized array arg
    check_differential("define f() { while(1) { return(42); }; }; f()")  # Return in while loop
    check_differential("define g() { for(i=0; i<10; ++i) { return(42); }; }; g()")  # Return in for loop

    # 2. Warnings / Stderr notifications (tested directly on the clone due to implementation-dependent behavior)
    _, out_1, err_1 = run_clone_bc("ibase = 1; ibase")
    assert "warning" in err_1.lower()
    assert out_1.strip() == "2"

    _, out_17, err_17 = run_clone_bc("ibase = 17; ibase")
    assert "warning" in err_17.lower()
    assert out_17.strip() == "16"

    # 3. Syntax / Lexical / Runtime errors
    check_differential("@", match_stderr=True)
    check_differential("!", match_stderr=True)
    # For unterminated comment, oracle bc hangs on EOF, so we test the clone directly
    _, _, err = run_clone_bc("/* comment")
    assert len(err.strip()) > 0
    check_differential('"unterminated', match_stderr=True)
    check_differential("define 123() {}", match_stderr=True)
    check_differential("define f(123) {}", match_stderr=True)
    check_differential("define f() { auto a 123; }", match_stderr=True)
    check_differential("++1", match_stderr=True)
    check_differential("f(a", match_stderr=True)
    check_differential("f(a[", match_stderr=True)
    check_differential("f(a 1", match_stderr=True)
    check_differential("{ 1 2 }", match_stderr=True)
    check_differential("define g() { return (); }; g()", match_stderr=True)
    check_differential("define f(x) { return(x); }; f(1, 2)", match_stderr=True)  # Argument count mismatch
    check_differential("define f(x[]) { return(1); }; f(2)", match_stderr=True)  # Expected array argument
    check_differential("f(1)", match_stderr=True)  # Undefined function


def test_lexer_peek_token_eof() -> None:
    from bc_parser import Lexer, TokenType

    lexer = Lexer("a[")
    # Eat a
    tok1 = lexer.get_next_token()
    assert tok1.type == TokenType.LETTER
    # Peek offset 0 (should be [)
    assert lexer.peek_token(0).type == TokenType.LBRACKET
    # Peek offset 1 (should be EOF)
    assert lexer.peek_token(1).type == TokenType.EOF


def test_unknown_ast_node() -> None:
    from bc_eval import Evaluator
    from bc_parser import ASTNode

    evaluator = Evaluator()
    with pytest.raises(RuntimeError, match="unknown AST node"):
        evaluator.evaluate(ASTNode())


def test_evaluator_flags() -> None:
    from bc_eval import Evaluator
    from bc_parser import BreakStmt

    evaluator = Evaluator()
    evaluator.return_flag = True
    # Should return immediately and not crash/affect state
    evaluator.execute(BreakStmt())


def test_quit_statement() -> None:
    from bc_eval import Evaluator
    from bc_parser import Program, QuitStmt

    evaluator = Evaluator()
    prog = Program([QuitStmt(), QuitStmt()])
    evaluator.execute(prog)
    assert evaluator.quit_flag is True


def test_clone_cli_invalid_option() -> None:
    code, stdout, stderr = run_clone_bc("", flags=["-x"])
    assert code == 1
    assert "invalid option" in stderr


def test_clone_cli_files(tmp_path: Path) -> None:
    # 1. Valid file
    p = tmp_path / "test.bc"
    p.write_text("3 * 5\n")
    code, stdout, stderr = run_clone_bc("", flags=[str(p)])
    assert code == 0
    assert stdout.strip() == "15"

    # 2. Non-existent file
    code, stdout, stderr = run_clone_bc("", flags=["non_existent_file.bc"])
    assert code == 1
    assert "cannot open file" in stderr


def test_clone_cli_file_quit(tmp_path: Path) -> None:
    p = tmp_path / "quit.bc"
    p.write_text("1\nquit\n2\n")
    code, stdout, stderr = run_clone_bc("", flags=[str(p)])
    assert code == 0
    assert stdout.strip() == ""


def test_count_open_braces() -> None:
    from bc_clone import count_open_braces

    assert count_open_braces("") == 0
    assert count_open_braces("{") == 1
    assert count_open_braces("}") == -1
    assert count_open_braces("/* { */") == 0
    assert count_open_braces('"{"') == 0
    assert count_open_braces('"hello \\\nworld"') == 0
    assert count_open_braces("a = 5 \\\n {") == 1


def test_run_interactive() -> None:
    import io
    from unittest.mock import patch

    from bc_clone import run_interactive
    from bc_eval import Evaluator

    # 1. Normal execution
    stdin = io.StringIO("1 + 2\n")
    stderr = io.StringIO()
    evaluator = Evaluator()
    with patch("sys.stdin", stdin), patch("sys.stderr", stderr):
        run_interactive(evaluator)

    # 2. Syntax error handling
    stdin = io.StringIO("@\n")
    stderr = io.StringIO()
    evaluator = Evaluator()
    with patch("sys.stdin", stdin), patch("sys.stderr", stderr):
        run_interactive(evaluator)
    assert "syntax error" in stderr.getvalue()

    # 3. KeyboardInterrupt handling
    class InterruptingIO:
        def __init__(self) -> None:
            self.called = False

        def readline(self) -> str:
            if not self.called:
                self.called = True
                raise KeyboardInterrupt()
            return ""

    stdin_int = InterruptingIO()
    stderr = io.StringIO()
    evaluator = Evaluator()
    with patch("sys.stdin", stdin_int), patch("sys.stderr", stderr):
        run_interactive(evaluator)
    assert stderr.getvalue() == "\n"

    # 4. Runtime error handling
    stdin = io.StringIO("1/0\nsqrt(-1)\n")
    stderr = io.StringIO()
    evaluator = Evaluator()
    with patch("sys.stdin", stdin), patch("sys.stderr", stderr):
        run_interactive(evaluator)
    assert "Runtime error" in stderr.getvalue()

    # 5. Quit flag exit
    stdin = io.StringIO("quit\n")
    stderr = io.StringIO()
    evaluator = Evaluator()
    with patch("sys.stdin", stdin), patch("sys.stderr", stderr):
        with pytest.raises(SystemExit) as exc:
            run_interactive(evaluator)
        assert exc.value.code == 0

    # 6. Backslash-newline and braces accumulation
    stdin = io.StringIO("1 + \\\n2\nif (1) {\n3\n}\n")
    stderr = io.StringIO()
    evaluator = Evaluator()
    with patch("sys.stdin", stdin), patch("sys.stderr", stderr):
        run_interactive(evaluator)

    # 7. General exception handling
    stdin = io.StringIO("1\n")
    stderr = io.StringIO()
    evaluator = Evaluator()
    with (
        patch("sys.stdin", stdin),
        patch("sys.stderr", stderr),
        patch.object(Evaluator, "execute", side_effect=Exception("oops")),
    ):
        run_interactive(evaluator)
    assert "Runtime error: oops" in stderr.getvalue()


def test_clone_main_interactive() -> None:
    from unittest.mock import patch

    import bc_clone

    with (
        patch("sys.argv", ["bc_clone.py"]),
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout.isatty", return_value=True),
        patch("bc_clone.run_interactive") as mock_run,
    ):
        bc_clone.main()
        mock_run.assert_called_once()


def test_clone_cli_multiple_files_and_stdin(tmp_path: Path) -> None:
    # Multiple files sequentially evaluated
    p1 = tmp_path / "test1.bc"
    p1.write_text("a = 10\n")
    p2 = tmp_path / "test2.bc"
    p2.write_text("b = 20; a + b\n")
    code, stdout, stderr = run_clone_bc("", flags=[str(p1), str(p2)])
    assert code == 0
    assert stdout.strip() == "30"

    # File followed by stdin in non-interactive mode
    p = tmp_path / "test_stdin.bc"
    p.write_text("scale = 5\n")
    code, stdout, stderr = run_clone_bc("1 / 3\n", flags=[str(p)])
    assert code == 0
    assert stdout.strip() == ".33333"


def test_clone_cli_math_scale() -> None:
    # -l flag sets scale to 20 by default
    code, stdout, stderr = run_clone_bc("scale\n", flags=["-l"])
    assert code == 0
    assert stdout.strip() == "20"


def test_scale_register_preservation() -> None:
    # Scale register preservation during math function execution
    programs = [
        "scale = 5; s(0.5); scale",
        "scale = 3; c(0.2); scale",
        "scale = 7; a(1); scale",
        "scale = 2; l(2); scale",
        "scale = 4; e(1); scale",
        "scale = 6; j(1, 2); scale",
    ]
    for prog in programs:
        check_differential(prog, flags=["-l"])


def test_gnu_extension_return() -> None:
    # Test return expression without parentheses (GNU extension)
    programs = [
        "define f(x) { return x * 2; }; f(5)",
        "define f(x) { if (x == 0) return 0; return x + f(x-1); }; f(5)",
        "define f() { return; }; f()",
    ]
    for prog in programs:
        check_differential(prog)


def test_user_fib_sqrt_demo() -> None:
    demo_program = """
    scale = 5
    "--- Complex Calculation Demo ---\\n"
    "1. Fibonacci Function\\n"
    define fib(n) {
        auto a, b, c, i
        a = 0; b = 1
        if (n == 0) return a
        if (n == 1) return b
        for (i = 2; i <= n; ++i) {
            c = a + b
            a = b
            b = c
        }
        return b
    }
    "fib(12) = "
    fib(12)
    "2. Square Root\\n"
    "sqrt(fib(12)) = "
    sqrt(fib(12))
    "3. Math Library (e^1)\\n"
    "e(1) = "
    e(1)
    """
    check_differential(demo_program, flags=["-l"])
