import sys

from bc_eval import Evaluator
from bc_parser import Lexer, Parser


def count_open_braces(text: str) -> int:
    """Count the number of open braces outside strings and comments."""
    count = 0
    in_string = False
    in_comment = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_comment:
            if c == "*" and i + 1 < len(text) and text[i + 1] == "/":
                in_comment = False
                i += 2
                continue
            i += 1
        elif in_string:
            if c == '"':
                in_string = False
            elif c == "\\" and i + 1 < len(text) and text[i + 1] == "\n":
                i += 2
                continue
            i += 1
        else:
            if c == "/" and i + 1 < len(text) and text[i + 1] == "*":
                in_comment = True
                i += 2
                continue
            if c == '"':
                in_string = True
                i += 1
                continue
            if c == "{":
                count += 1
            elif c == "}":
                count -= 1
            i += 1
    return count


def run_interactive(evaluator: Evaluator) -> None:
    """Read line-by-line and execute complete blocks incrementally."""
    accumulator: list[str] = []
    brace_count = 0

    while True:
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            sys.stderr.write("\n")
            accumulator.clear()
            brace_count = 0
            continue

        if not line:
            # EOF
            break

        accumulator.append(line)
        accumulated_text = "".join(accumulator)

        # Check backslash-newline
        if accumulated_text.endswith("\\\n"):
            continue

        # Check brace count
        brace_count = count_open_braces(accumulated_text)
        if brace_count > 0:
            continue

        # Attempt to parse and execute
        try:
            lexer = Lexer(accumulated_text)
            parser = Parser(lexer)
            prog = parser.parse_program()
            evaluator.execute(prog)
        except SyntaxError:
            sys.stderr.write(f"(standard_in) {lexer.line}: syntax error\n")
            # Clear buffer on syntax error to allow new statements
            accumulator.clear()
            brace_count = 0
        except ZeroDivisionError:
            sys.stderr.write("Runtime error: division by zero\n")
            accumulator.clear()
            brace_count = 0
        except ValueError as e:
            sys.stderr.write(f"Runtime error: {e}\n")
            accumulator.clear()
            brace_count = 0
        except Exception as e:
            sys.stderr.write(f"Runtime error: {e}\n")
            accumulator.clear()
            brace_count = 0
        else:
            accumulator.clear()
            brace_count = 0


def run_non_interactive(evaluator: Evaluator, content: str, filename: str) -> None:
    """Parse and execute a complete block of code from a file or stdin."""
    try:
        lexer = Lexer(content)
        parser = Parser(lexer)
        prog = parser.parse_program()
        evaluator.execute(prog)
    except SyntaxError:
        sys.stderr.write(f"{filename}: syntax error on line {lexer.line}\n")
        sys.exit(1)
    except ZeroDivisionError:
        sys.stderr.write(f"Runtime error: division by zero in {filename}\n")
        sys.exit(1)
    except ValueError as e:
        sys.stderr.write(f"Runtime error: {e} in {filename}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Runtime error: {e} in {filename}\n")
        sys.exit(1)


def _isatty(stream: object) -> bool:
    """Return whether stream is a terminal; MicroPython streams have no isatty and are consoles."""
    isatty = getattr(stream, "isatty", None)
    return True if isatty is None else bool(isatty())


def main(argv: list[str] | None = None, mathlib: bool = False) -> None:
    """Run bc with argv (default: sys.argv[1:]); mathlib=True is the same as -l."""
    math_enabled = mathlib
    files = []

    if argv is None:
        argv = sys.argv[1:]

    # Parse options manually to match POSIX style
    for arg in argv:
        if arg == "-l":
            math_enabled = True
        elif arg.startswith("-"):
            sys.stderr.write(f"bc: invalid option -- '{arg[1:]}'\n")
            sys.exit(1)
        else:
            files.append(arg)

    evaluator = Evaluator(math_enabled=math_enabled)
    if math_enabled:
        evaluator.scale = 20

    # Process files
    for filename in files:
        try:
            with open(filename, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            sys.stderr.write(f"bc: cannot open file {filename}\n")
            sys.exit(1)

        run_non_interactive(evaluator, content, filename)

    # Process standard input
    is_interactive = _isatty(sys.stdin) and _isatty(sys.stdout)
    if is_interactive:
        run_interactive(evaluator)
    else:
        run_non_interactive(evaluator, sys.stdin.read(), "standard input")


def repl(mathlib: bool = False) -> None:
    """Run bc on stdin and return on quit or EOF instead of exiting (entry point for MicroPython)."""
    try:  # noqa: SIM105
        main([], mathlib)
    except SystemExit:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
