# bc-clone

> [!NOTE]
> This project was fully designed, implemented, verified, and documented by an AI coding agent.

A robust, pure Python (Standard Library only), POSIX-compliant clone of the classic `bc` arbitrary-precision calculator language. 

Designed to serve as a production-grade, zero-dependency utility, this implementation complies with the IEEE Std 1003.1-2008 (POSIX) specification for `bc`. It is verified using a differential testing harness against the system `bc` as an oracle, and maintains **100% statement and branch coverage** across all modules.

---

## Features

- **Arbitrary-Precision Arithmetic**: Implements basic arithmetic (`+`, `-`, `*`, `/`, `%`, `^`) with dynamic `scale` behavior conforming strictly to POSIX guidelines.
- **Base Conversion**: Dynamic input and output radix conversion supporting `ibase` and `obase` (base 2 through 16).
- **POSIX Control Structures**: Supports `if`, `while`, `for`, `break`, `continue`, functions with parameters and local `auto` variables, and one-dimensional arrays.
- **Math Library (`-l`)**: Complete implementation of standard `bc` math library functions (`s` for sine, `c` for cosine, `e` for exponential, `l` for natural logarithm, `a` for arctangent, and `j` for bessel) computed to arbitrary precision using Taylor series expansions.
- **Interactive REPL**: A responsive read-eval-print loop with standard error handling and formatting.
- **Zero Runtime Dependencies**: Written entirely using Python's standard library. Fully typed (`mypy --strict`) and formatted (`ruff`).
- **GNU Extensions Support**: Supports `return expression` without enclosing parentheses (in addition to standard POSIX `return (expression)`).

---

## Architecture

The project is structured into modular components:

```
├── pyproject.toml         # Development dependencies and tool configurations
├── bc_clone.py            # CLI entry point, stream handler, and interactive REPL
├── bc_parser.py           # Lexer, Parser, and AST definitions
├── bc_math.py             # Custom arbitrary-precision decimal number (BCNum) and Math Library
├── bc_eval.py             # AST Evaluator, environment manager (dynamic scope), and output formatter
├── test_bc.py             # Differential test suite executing cases on both clone and system bc
└── .github/workflows/     # CI pipeline running linting, type checks, and 100% coverage verification
```

### Module Roles

1. **`bc_math.py`**:
   Implements `BCNum` which represents arbitrary-precision decimals as integer coefficients paired with an exponent. It defines all arithmetic operations and handles the math library functions (`s`, `c`, `e`, `l`, `a`, `j`) from scratch without external dependencies.
2. **`bc_parser.py`**:
   Contains the lexical analyzer (Lexer) and recursive descent parser (Parser) that parses POSIX `bc` source into a structured Abstract Syntax Tree (AST).
3. **`bc_eval.py`**:
   Maintains the runtime state (registers like `scale`, `ibase`, `obase`, variables, arrays, and function registries). It walks the AST to evaluate expressions using POSIX dynamic scoping rules.
4. **`bc_clone.py`**:
   Handles argument parsing (`-l` or files) and coordinates the execution loop. It supports interactive sessions, file reading, and piped input.

---

## Installation & Setup

This project uses `uv` for python environment management.

To set up the development environment:
```bash
# Clone the repository
git clone <repository-url>
cd bc-clone

# Install dependencies and sync virtual environment
uv sync
```

---

## Usage

You can run the clone directly using the CLI:

### Interactive REPL
```bash
uv run python bc_clone.py
```

### Math Library Enabled
```bash
uv run python bc_clone.py -l
```

### Running files
```bash
uv run python bc_clone.py script.bc
```

---

## Development and Verification

### Running the Test Suite
The test suite utilizes the host system `bc` utility as an oracle for differential validation, executing identical inputs through both systems and verifying match outcomes.

```bash
# Run pytest with full coverage reporting
uv run pytest --cov=bc_clone --cov=bc_math --cov=bc_parser --cov=bc_eval --cov-report=term-missing test_bc.py
```

### Static Analysis & Quality Controls

To ensure production-grade code quality, the repository enforces strict linting, formatting, and typing rules:

```bash
# Run strict Mypy checks
uv run mypy .

# Run Ruff linter checks
uv run ruff check .

# Run Ruff formatting verification
uv run ruff format --check .
```
