import sys

try:  # noqa: SIM105
    from typing import TextIO
except ImportError:  # pragma: no cover - MicroPython has no typing module
    pass

from bc_math import (
    BCNum,
    bc_atan,
    bc_bessel,
    bc_cos,
    bc_exp,
    bc_ln,
    bc_sin,
    trunc_div,
)
from bc_parser import (
    ArrayAccess,
    ArrayArg,
    AssignOp,
    ASTNode,
    BinaryOp,
    Block,
    BreakStmt,
    CallExpr,
    ForStmt,
    FunctionDef,
    IfStmt,
    LengthCall,
    NumberLiteral,
    Program,
    QuitStmt,
    RegisterAccess,
    RelationalOp,
    ReturnStmt,
    ScaleCall,
    SqrtCall,
    StringLiteral,
    UnaryOp,
    UpdateOp,
    Variable,
    WhileStmt,
)


class WrappedStdout:
    """Wrapper to write output characters with POSIX-style 70-character line wrapping."""

    stream: TextIO
    col: int

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self.col = 0

    def write(self, s: str) -> None:
        for char in s:
            if char == "\n":
                self.stream.write("\n")
                self.col = 0
            else:
                if self.col >= 68:
                    self.stream.write("\\\n")
                    self.col = 0
                self.stream.write(char)
                self.col += 1

    def flush(self) -> None:
        self.stream.flush()


class Evaluator:
    """Tree-walking interpreter for bc AST nodes."""

    variables: dict[str, list[BCNum]]
    arrays: dict[str, list[dict[int, BCNum]]]
    functions: dict[str, FunctionDef]
    scale: int
    ibase: int
    obase: int
    math_enabled: bool
    stdout_writer: WrappedStdout

    break_flag: bool
    return_flag: bool
    return_value: BCNum
    quit_flag: bool

    def __init__(self, math_enabled: bool = False, stdout_stream: TextIO | None = None) -> None:
        self.scale = 0
        self.ibase = 10
        self.obase = 10
        self.math_enabled = math_enabled
        self.stdout_writer = WrappedStdout(stdout_stream)

        # Initialize variables and arrays dynamically
        self.variables = {}
        self.arrays = {}
        self.functions = {}

        self.break_flag = False
        self.return_flag = False
        self.return_value = BCNum(0, 0)
        self.quit_flag = False

    def evaluate(self, node: ASTNode) -> BCNum:
        """Evaluate an AST expression node and return a BCNum."""
        if isinstance(node, NumberLiteral):
            return BCNum.from_string(node.value, self.ibase)

        if isinstance(node, Variable):
            if node.name not in self.variables:
                self.variables[node.name] = [BCNum(0, 0)]
            return self.variables[node.name][-1]

        if isinstance(node, ArrayAccess):
            idx = self.evaluate(node.index)
            idx_val = trunc_div(idx.coeff, 10**idx.scale) if idx.scale > 0 else idx.coeff
            if node.name not in self.arrays:
                self.arrays[node.name] = [{}]
            arr = self.arrays[node.name][-1]
            return arr.get(idx_val, BCNum(0, 0))

        if isinstance(node, RegisterAccess):
            val = getattr(self, node.name)
            return BCNum(val, 0)

        if isinstance(node, UnaryOp):
            val = self.evaluate(node.expr)
            return BCNum(-val.coeff, val.scale)

        if isinstance(node, BinaryOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            if node.op == "+":
                return left.add(right)
            if node.op == "-":
                return left.sub(right)
            if node.op == "*":
                return left.mul(right, self.scale)
            if node.op == "/":
                return left.div(right, self.scale)
            if node.op == "%":
                return left.mod(right, self.scale)
            if node.op == "^":
                return left.pow(right, self.scale)

        if isinstance(node, RelationalOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            diff = left.scale - right.scale
            if diff > 0:
                coeff_l = left.coeff
                coeff_r = right.coeff * (10**diff)
            elif diff < 0:
                coeff_l = left.coeff * (10**-diff)
                coeff_r = right.coeff
            else:
                coeff_l = left.coeff
                coeff_r = right.coeff

            res = False
            if node.op == "==":
                res = coeff_l == coeff_r
            elif node.op == "<=":
                res = coeff_l <= coeff_r
            elif node.op == ">=":
                res = coeff_l >= coeff_r
            elif node.op == "!=":
                res = coeff_l != coeff_r
            elif node.op == "<":
                res = coeff_l < coeff_r
            elif node.op == ">":
                res = coeff_l > coeff_r
            return BCNum(1 if res else 0, 0)

        if isinstance(node, AssignOp):
            # Special single-digit hex assignment rule for ibase/obase
            is_base_reg = isinstance(node.target, RegisterAccess) and node.target.name in ("ibase", "obase")

            if (
                is_base_reg
                and isinstance(node.expr, NumberLiteral)
                and len(node.expr.value.replace("\\\n", "")) == 1
                and node.op == "="
            ):
                # Interpret the single character directly as hex (0-15)
                char = node.expr.value.replace("\\\n", "")
                if "0" <= char <= "9":
                    val = BCNum(ord(char) - ord("0"), 0)
                else:
                    val = BCNum(ord(char.upper()) - ord("A") + 10, 0)
            else:
                val = self.evaluate(node.expr)
                if node.op != "=":
                    old_val = self.evaluate(node.target)
                    op = node.op[:-1]
                    if op == "+":
                        val = old_val.add(val)
                    elif op == "-":
                        val = old_val.sub(val)
                    elif op == "*":
                        val = old_val.mul(val, self.scale)
                    elif op == "/":
                        val = old_val.div(val, self.scale)
                    elif op == "%":
                        val = old_val.mod(val, self.scale)
                    elif op == "^":
                        val = old_val.pow(val, self.scale)

            # Perform assignment
            if isinstance(node.target, Variable):
                if node.target.name not in self.variables:
                    self.variables[node.target.name] = [BCNum(0, 0)]
                self.variables[node.target.name][-1] = val
            elif isinstance(node.target, ArrayAccess):
                idx = self.evaluate(node.target.index)
                idx_val = trunc_div(idx.coeff, 10**idx.scale) if idx.scale > 0 else idx.coeff
                if node.target.name not in self.arrays:
                    self.arrays[node.target.name] = [{}]
                self.arrays[node.target.name][-1][idx_val] = val
            elif isinstance(node.target, RegisterAccess):
                reg_val = trunc_div(val.coeff, 10**val.scale) if val.scale > 0 else val.coeff
                if node.target.name == "scale":
                    reg_val = max(0, reg_val)
                elif node.target.name == "ibase":
                    if reg_val < 2:
                        sys.stderr.write("Runtime warning (func=(main), adr=3): ibase too small, set to 2\n")
                        reg_val = 2
                    elif reg_val > 16:
                        sys.stderr.write("Runtime warning (func=(main), adr=3): ibase too large, set to 16\n")
                        reg_val = 16
                elif node.target.name == "obase":
                    reg_val = max(2, reg_val)
                setattr(self, node.target.name, reg_val)
                val = BCNum(reg_val, 0)
            return val

        if isinstance(node, UpdateOp):
            old_val = self.evaluate(node.target)
            step = BCNum(1, 0)
            new_val = old_val.add(step) if node.op == "++" else old_val.sub(step)

            if isinstance(node.target, Variable):
                self.variables[node.target.name][-1] = new_val
            elif isinstance(node.target, ArrayAccess):
                idx = self.evaluate(node.target.index)
                idx_val = trunc_div(idx.coeff, 10**idx.scale) if idx.scale > 0 else idx.coeff
                self.arrays[node.target.name][-1][idx_val] = new_val
            elif isinstance(node.target, RegisterAccess):
                reg_val = trunc_div(new_val.coeff, 10**new_val.scale) if new_val.scale > 0 else new_val.coeff
                if node.target.name == "scale":
                    reg_val = max(0, reg_val)
                elif node.target.name == "ibase":
                    reg_val = max(2, min(16, reg_val))
                elif node.target.name == "obase":
                    reg_val = max(2, reg_val)
                setattr(self, node.target.name, reg_val)
                new_val = BCNum(reg_val, 0)

            return new_val if node.is_prefix else old_val

        if isinstance(node, CallExpr):
            if node.name in self.functions:
                func = self.functions[node.name]
                if len(node.args) != len(func.params):
                    raise RuntimeError("argument count mismatch")

                # Evaluate and prepare parameters
                evaluated_args: list[tuple[bool, str, BCNum | dict[int, BCNum]]] = []
                for i, arg in enumerate(node.args):
                    param = func.params[i]
                    if param.is_array:
                        # Should be ArrayArg
                        if not isinstance(arg, ArrayArg):
                            raise RuntimeError("expected array argument")
                        # Pass by value: copy the array
                        if arg.name not in self.arrays:
                            self.arrays[arg.name] = [{}]
                        arr_copy = dict(self.arrays[arg.name][-1])
                        evaluated_args.append((True, param.name, arr_copy))
                    else:
                        val = self.evaluate(arg)
                        evaluated_args.append((False, param.name, val))

                # Push params onto scoping stacks
                for is_arr, pname, val_or_arr in evaluated_args:
                    if is_arr:
                        assert isinstance(val_or_arr, dict)
                        if pname not in self.arrays:
                            self.arrays[pname] = []
                        self.arrays[pname].append(val_or_arr)
                    else:
                        assert isinstance(val_or_arr, BCNum)
                        if pname not in self.variables:
                            self.variables[pname] = []
                        self.variables[pname].append(val_or_arr)

                # Push autos onto stacks
                for auto in func.autos:
                    if auto.is_array:
                        if auto.name not in self.arrays:
                            self.arrays[auto.name] = []
                        self.arrays[auto.name].append({})
                    else:
                        if auto.name not in self.variables:
                            self.variables[auto.name] = []
                        self.variables[auto.name].append(BCNum(0, 0))

                # Save previous flow control states
                prev_return_flag = self.return_flag
                prev_return_value = self.return_value
                self.return_flag = False
                self.return_value = BCNum(0, 0)

                # Execute body
                for stmt in func.body:
                    self.execute(stmt)
                    if self.return_flag or self.quit_flag:
                        break

                ret_val = self.return_value

                # Restore flow control states
                self.return_flag = prev_return_flag
                self.return_value = prev_return_value

                # Pop autos
                for auto in reversed(func.autos):
                    if auto.is_array:
                        self.arrays[auto.name].pop()
                    else:
                        self.variables[auto.name].pop()

                # Pop params
                for param in reversed(func.params):
                    if param.is_array:
                        self.arrays[param.name].pop()
                    else:
                        self.variables[param.name].pop()

                return ret_val

            # Math functions
            if self.math_enabled:
                if node.name == "s" and len(node.args) == 1:
                    return bc_sin(self.evaluate(node.args[0]), self.scale)
                if node.name == "c" and len(node.args) == 1:
                    return bc_cos(self.evaluate(node.args[0]), self.scale)
                if node.name == "a" and len(node.args) == 1:
                    return bc_atan(self.evaluate(node.args[0]), self.scale)
                if node.name == "l" and len(node.args) == 1:
                    return bc_ln(self.evaluate(node.args[0]), self.scale)
                if node.name == "e" and len(node.args) == 1:
                    return bc_exp(self.evaluate(node.args[0]), self.scale)
                if node.name == "j" and len(node.args) == 2:
                    return bc_bessel(self.evaluate(node.args[0]), self.evaluate(node.args[1]), self.scale)

            raise RuntimeError(f"undefined function {node.name}")

        if isinstance(node, LengthCall):
            return self.evaluate(node.expr).length()

        if isinstance(node, SqrtCall):
            return self.evaluate(node.expr).sqrt(self.scale)

        if isinstance(node, ScaleCall):
            return self.evaluate(node.expr).scale_func()

        raise RuntimeError("unknown AST node")

    def execute(self, node: ASTNode) -> None:
        """Execute an AST statement node."""
        if self.break_flag or self.return_flag or self.quit_flag:
            return

        if isinstance(node, Program):
            for item in node.items:
                self.execute(item)
                if self.quit_flag:
                    break
            return

        if isinstance(node, Block):
            for stmt in node.stmts:
                self.execute(stmt)
                if self.break_flag or self.return_flag or self.quit_flag:
                    break
            return

        if isinstance(node, FunctionDef):
            self.functions[node.name] = node
            return

        if isinstance(node, StringLiteral):
            self.stdout_writer.write(node.value)
            self.stdout_writer.flush()
            return

        if isinstance(node, BreakStmt):
            self.break_flag = True
            return

        if isinstance(node, QuitStmt):
            self.quit_flag = True
            return

        if isinstance(node, ReturnStmt):
            if node.expr is not None:
                self.return_value = self.evaluate(node.expr)
            else:
                self.return_value = BCNum(0, 0)
            self.return_flag = True
            return

        if isinstance(node, IfStmt):
            cond = self.evaluate(node.cond)
            if not cond.is_zero():
                self.execute(node.body)
            return

        if isinstance(node, WhileStmt):
            while True:
                cond = self.evaluate(node.cond)
                if cond.is_zero() or self.quit_flag:
                    break
                self.execute(node.body)
                if self.break_flag:
                    self.break_flag = False
                    break
                if self.return_flag or self.quit_flag:
                    break
            return

        if isinstance(node, ForStmt):
            self.evaluate(node.init)
            while True:
                cond = self.evaluate(node.cond)
                if cond.is_zero() or self.quit_flag:
                    break
                self.execute(node.body)
                if self.break_flag:
                    self.break_flag = False
                    break
                if self.return_flag or self.quit_flag:
                    break
                self.evaluate(node.post)
            return

        # It's an expression statement
        # "unless the main operator is an assignment, execution of the statement shall write the value..."
        if isinstance(node, AssignOp):
            self.evaluate(node)
        else:
            val = self.evaluate(node)
            out_str = val.format_obase(self.obase)
            self.stdout_writer.write(out_str + "\n")
            self.stdout_writer.flush()
