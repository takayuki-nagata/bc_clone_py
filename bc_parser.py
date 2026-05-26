import sys
from dataclasses import dataclass
from enum import Enum
from enum import auto as enum_auto
from typing import NoReturn


class TokenType(Enum):
    EOF = enum_auto()
    NEWLINE = enum_auto()
    SEMICOLON = enum_auto()
    COMMA = enum_auto()
    LPAREN = enum_auto()
    RPAREN = enum_auto()
    LBRACKET = enum_auto()
    RBRACKET = enum_auto()
    LBRACE = enum_auto()
    RBRACE = enum_auto()

    # Operators
    PLUS = enum_auto()
    MINUS = enum_auto()
    EXP = enum_auto()  # ^
    MUL_OP = enum_auto()  # *, /, %
    REL_OP = enum_auto()  # ==, <=, >=, !=, <, >
    INCR_DECR = enum_auto()  # ++, --
    ASSIGN_OP = enum_auto()  # =, +=, -=, *=, /=, %=, ^=

    # Literals & Identifiers
    LETTER = enum_auto()  # lowercase letter a-z
    NUMBER = enum_auto()  # number constant
    STRING = enum_auto()  # string constant

    # Keywords
    AUTO = enum_auto()
    BREAK = enum_auto()
    DEFINE = enum_auto()
    IBASE = enum_auto()
    IF = enum_auto()
    FOR = enum_auto()
    LENGTH = enum_auto()
    OBASE = enum_auto()
    QUIT = enum_auto()
    RETURN = enum_auto()
    SCALE = enum_auto()
    SQRT = enum_auto()
    WHILE = enum_auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int


class Lexer:
    """Incremental lexical analyzer for bc."""

    text: str
    pos: int
    line: int
    buffer: list[Token]

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.line = 1
        self.buffer = []

    def error(self, msg: str) -> NoReturn:
        raise SyntaxError(f"Lexical error on line {self.line}: {msg}")

    def peek_char(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= len(self.text):
            return ""
        return self.text[idx]

    def advance_char(self, steps: int = 1) -> None:
        for _ in range(steps):
            if self.pos < len(self.text):
                if self.text[self.pos] == "\n":
                    self.line += 1
                self.pos += 1

    def skip_whitespace_and_comments(self) -> None:
        while True:
            c = self.peek_char()
            if c in (" ", "\t"):
                self.advance_char()
            elif c == "\\" and self.peek_char(1) == "\n":
                self.advance_char(2)
            elif c == "/" and self.peek_char(1) == "*":
                self.advance_char(2)
                while True:
                    cc = self.peek_char()
                    if cc == "":
                        self.error("unterminated comment")
                    if cc == "*" and self.peek_char(1) == "/":
                        self.advance_char(2)
                        break
                    self.advance_char()
            else:
                break

    def _scan_token(self) -> Token:  # noqa: RET503
        self.skip_whitespace_and_comments()
        c = self.peek_char()
        if c == "":
            return Token(TokenType.EOF, "", self.line)

        if c == "\n":
            self.advance_char()
            return Token(TokenType.NEWLINE, "\n", self.line - 1)

        if c == ";":
            self.advance_char()
            return Token(TokenType.SEMICOLON, ";", self.line)
        if c == ",":
            self.advance_char()
            return Token(TokenType.COMMA, ",", self.line)
        if c == "(":
            self.advance_char()
            return Token(TokenType.LPAREN, "(", self.line)
        if c == ")":
            self.advance_char()
            return Token(TokenType.RPAREN, ")", self.line)
        if c == "[":
            self.advance_char()
            return Token(TokenType.LBRACKET, "[", self.line)
        if c == "]":
            self.advance_char()
            return Token(TokenType.RBRACKET, "]", self.line)
        if c == "{":
            self.advance_char()
            return Token(TokenType.LBRACE, "{", self.line)
        if c == "}":
            self.advance_char()
            return Token(TokenType.RBRACE, "}", self.line)

        if c == "^":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.ASSIGN_OP, "^=", self.line)
            self.advance_char()
            return Token(TokenType.EXP, "^", self.line)

        if c == "+":
            if self.peek_char(1) == "+":
                self.advance_char(2)
                return Token(TokenType.INCR_DECR, "++", self.line)
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.ASSIGN_OP, "+=", self.line)
            self.advance_char()
            return Token(TokenType.PLUS, "+", self.line)

        if c == "-":
            if self.peek_char(1) == "-":
                self.advance_char(2)
                return Token(TokenType.INCR_DECR, "--", self.line)
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.ASSIGN_OP, "-=", self.line)
            self.advance_char()
            return Token(TokenType.MINUS, "-", self.line)

        if c == "*":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.ASSIGN_OP, "*=", self.line)
            self.advance_char()
            return Token(TokenType.MUL_OP, "*", self.line)

        if c == "/":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.ASSIGN_OP, "/=", self.line)
            self.advance_char()
            return Token(TokenType.MUL_OP, "/", self.line)

        if c == "%":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.ASSIGN_OP, "%=", self.line)
            self.advance_char()
            return Token(TokenType.MUL_OP, "%", self.line)

        if c == "=":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.REL_OP, "==", self.line)
            self.advance_char()
            return Token(TokenType.ASSIGN_OP, "=", self.line)

        if c == "<":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.REL_OP, "<=", self.line)
            self.advance_char()
            return Token(TokenType.REL_OP, "<", self.line)

        if c == ">":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.REL_OP, ">=", self.line)
            self.advance_char()
            return Token(TokenType.REL_OP, ">", self.line)

        if c == "!":
            if self.peek_char(1) == "=":
                self.advance_char(2)
                return Token(TokenType.REL_OP, "!=", self.line)
            self.error("unexpected character '!'")

        if c == '"':
            self.advance_char()
            val_chars = []
            while True:
                cc = self.peek_char()
                if cc == "":
                    self.error("unterminated string")
                if cc == '"':
                    self.advance_char()
                    break
                if cc == "\\" and self.peek_char(1) == "\n":
                    val_chars.append("\\")
                    val_chars.append("\n")
                    self.advance_char(2)
                else:
                    val_chars.append(cc)
                    self.advance_char()
            return Token(TokenType.STRING, "".join(val_chars), self.line)

        def is_digit(ch: str) -> bool:
            return ("0" <= ch <= "9") or ("A" <= ch <= "F")

        if is_digit(c) or (c == "." and is_digit(self.peek_char(1))):
            val_chars = []
            has_dot = False
            while True:
                cc = self.peek_char()
                if is_digit(cc):
                    val_chars.append(cc)
                    self.advance_char()
                elif cc == "." and not has_dot:
                    has_dot = True
                    val_chars.append(cc)
                    self.advance_char()
                elif cc == "\\" and self.peek_char(1) == "\n":
                    self.advance_char(2)
                else:
                    break
            return Token(TokenType.NUMBER, "".join(val_chars), self.line)

        if "a" <= c <= "z":
            letters = [c]
            self.advance_char()
            while ("a" <= self.peek_char() <= "z") or ("0" <= self.peek_char() <= "9") or (self.peek_char() == "_"):
                letters.append(self.peek_char())
                self.advance_char()
            word = "".join(letters)

            keywords = {
                "auto": TokenType.AUTO,
                "break": TokenType.BREAK,
                "define": TokenType.DEFINE,
                "ibase": TokenType.IBASE,
                "if": TokenType.IF,
                "for": TokenType.FOR,
                "length": TokenType.LENGTH,
                "obase": TokenType.OBASE,
                "quit": TokenType.QUIT,
                "return": TokenType.RETURN,
                "scale": TokenType.SCALE,
                "sqrt": TokenType.SQRT,
                "while": TokenType.WHILE,
            }
            if word in keywords:
                return Token(keywords[word], word, self.line)
            return Token(TokenType.LETTER, word, self.line)

        self.error(f"unexpected character {c!r}")

    def get_next_token(self) -> Token:
        if self.buffer:
            return self.buffer.pop(0)
        return self._scan_token()

    def peek_token(self, offset: int = 0) -> Token:
        while len(self.buffer) <= offset:
            tok = self._scan_token()
            self.buffer.append(tok)
            if tok.type == TokenType.EOF:
                break
        return self.buffer[offset]


# --- AST Nodes ---


class ASTNode:
    pass


@dataclass
class Program(ASTNode):
    items: list[ASTNode]


@dataclass
class StringLiteral(ASTNode):
    value: str


@dataclass
class BreakStmt(ASTNode):
    pass


@dataclass
class QuitStmt(ASTNode):
    pass


@dataclass
class ReturnStmt(ASTNode):
    expr: ASTNode | None


@dataclass
class ForStmt(ASTNode):
    init: ASTNode
    cond: ASTNode
    post: ASTNode
    body: ASTNode


@dataclass
class IfStmt(ASTNode):
    cond: ASTNode
    body: ASTNode


@dataclass
class WhileStmt(ASTNode):
    cond: ASTNode
    body: ASTNode


@dataclass
class Block(ASTNode):
    stmts: list[ASTNode]


@dataclass
class Param:
    name: str
    is_array: bool


@dataclass
class FunctionDef(ASTNode):
    name: str
    params: list[Param]
    autos: list[Param]
    body: list[ASTNode]


@dataclass
class NumberLiteral(ASTNode):
    value: str


@dataclass
class Variable(ASTNode):
    name: str


@dataclass
class ArrayAccess(ASTNode):
    name: str
    index: ASTNode


@dataclass
class RegisterAccess(ASTNode):
    name: str  # 'scale', 'ibase', 'obase'


@dataclass
class CallExpr(ASTNode):
    name: str
    args: list[ASTNode]  # Expr or ArrayArg


@dataclass
class ArrayArg(ASTNode):
    name: str


@dataclass
class UnaryOp(ASTNode):
    op: str  # '-'
    expr: ASTNode


@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode


@dataclass
class RelationalOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode


@dataclass
class UpdateOp(ASTNode):
    op: str  # '++', '--'
    is_prefix: bool
    target: ASTNode


@dataclass
class AssignOp(ASTNode):
    op: str
    target: ASTNode
    expr: ASTNode


@dataclass
class LengthCall(ASTNode):
    expr: ASTNode


@dataclass
class SqrtCall(ASTNode):
    expr: ASTNode


@dataclass
class ScaleCall(ASTNode):
    expr: ASTNode


# --- Parser ---


class Parser:
    """Recursive descent parser with operator precedence support for bc."""

    lexer: Lexer
    current_token: Token

    def __init__(self, lexer: Lexer) -> None:
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def error(self, msg: str) -> NoReturn:
        raise SyntaxError(f"Parser error on line {self.current_token.line}: {msg}")

    def eat(self, token_type: TokenType) -> None:
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"expected {token_type}, got {self.current_token.type}")

    def peek_token_type(self, offset: int = 0) -> TokenType:
        return self.lexer.peek_token(offset).type

    def parse_program(self) -> Program:
        items = []
        while self.current_token.type != TokenType.EOF:
            item = self.parse_input_item()
            if item is not None:
                items.append(item)
        return Program(items)

    def parse_input_item(self) -> ASTNode | None:
        if self.current_token.type == TokenType.DEFINE:
            return self.parse_function()

        lst = self.parse_semicolon_list()
        if self.current_token.type == TokenType.NEWLINE:
            self.eat(TokenType.NEWLINE)
        else:
            self.eat(TokenType.EOF)
        return Block(lst) if lst else None

    def parse_semicolon_list(self) -> list[ASTNode]:
        stmts = []
        while True:
            if self.current_token.type in (TokenType.NEWLINE, TokenType.EOF, TokenType.RBRACE):
                break
            if self.current_token.type == TokenType.SEMICOLON:
                self.eat(TokenType.SEMICOLON)
                continue

            stmt = self.parse_statement()
            stmts.append(stmt)

            curr_type: TokenType = self.current_token.type
            if curr_type == TokenType.SEMICOLON:
                self.eat(TokenType.SEMICOLON)
            else:
                break
        return stmts

    def parse_statement_list(self) -> list[ASTNode]:
        stmts = []
        while True:
            self.skip_newlines()
            if self.current_token.type in (TokenType.EOF, TokenType.RBRACE):
                break

            stmt = self.parse_statement()
            stmts.append(stmt)

            if self.current_token.type == TokenType.SEMICOLON:
                self.eat(TokenType.SEMICOLON)
            elif self.current_token.type == TokenType.NEWLINE:
                self.eat(TokenType.NEWLINE)
            elif self.current_token.type == TokenType.RBRACE:
                pass
            else:
                if self.current_token.type not in (TokenType.EOF, TokenType.RBRACE):
                    self.error(f"expected separator, got {self.current_token.type}")
        return stmts

    def skip_newlines(self) -> None:
        while self.current_token.type == TokenType.NEWLINE:
            self.eat(TokenType.NEWLINE)

    def parse_statement(self) -> ASTNode:
        t = self.current_token.type
        if t == TokenType.STRING:
            val = self.current_token.value
            self.eat(TokenType.STRING)
            return StringLiteral(val)
        if t == TokenType.BREAK:
            self.eat(TokenType.BREAK)
            return BreakStmt()
        if t == TokenType.QUIT:
            self.eat(TokenType.QUIT)
            sys.exit(0)
        if t == TokenType.RETURN:
            self.eat(TokenType.RETURN)
            if self.current_token.type == TokenType.LPAREN:
                self.eat(TokenType.LPAREN)
                expr = self.parse_expression()
                self.eat(TokenType.RPAREN)
                return ReturnStmt(expr)
            # GNU extension: return without parentheses
            if self.current_token.type not in (
                TokenType.NEWLINE,
                TokenType.SEMICOLON,
                TokenType.RBRACE,
                TokenType.EOF,
            ):
                expr = self.parse_expression()
                return ReturnStmt(expr)
            return ReturnStmt(None)
        if t == TokenType.FOR:
            self.eat(TokenType.FOR)
            self.eat(TokenType.LPAREN)
            init = self.parse_expression()
            self.eat(TokenType.SEMICOLON)
            cond = self.parse_relational_expression()
            self.eat(TokenType.SEMICOLON)
            post = self.parse_expression()
            self.eat(TokenType.RPAREN)
            body = self.parse_statement()
            return ForStmt(init, cond, post, body)
        if t == TokenType.IF:
            self.eat(TokenType.IF)
            self.eat(TokenType.LPAREN)
            cond = self.parse_relational_expression()
            self.eat(TokenType.RPAREN)
            body = self.parse_statement()
            return IfStmt(cond, body)
        if t == TokenType.WHILE:
            self.eat(TokenType.WHILE)
            self.eat(TokenType.LPAREN)
            cond = self.parse_relational_expression()
            self.eat(TokenType.RPAREN)
            body = self.parse_statement()
            return WhileStmt(cond, body)
        if t == TokenType.LBRACE:
            self.eat(TokenType.LBRACE)
            stmts = self.parse_statement_list()
            self.eat(TokenType.RBRACE)
            return Block(stmts)

        return self.parse_relational_expression()

    def parse_function(self) -> FunctionDef:
        self.eat(TokenType.DEFINE)
        if self.current_token.type != TokenType.LETTER:
            self.error("expected function name (letter)")
        name = self.current_token.value
        self.eat(TokenType.LETTER)

        self.eat(TokenType.LPAREN)
        params = self.parse_opt_define_list()
        self.eat(TokenType.RPAREN)

        self.eat(TokenType.LBRACE)
        self.skip_newlines()

        autos = self.parse_opt_auto_define_list()
        body = self.parse_statement_list()
        self.eat(TokenType.RBRACE)

        return FunctionDef(name, params, autos, body)

    def parse_opt_define_list(self) -> list[Param]:
        if self.current_token.type == TokenType.RPAREN:
            return []
        return self.parse_define_list()

    def parse_define_list(self) -> list[Param]:
        lst = []
        while True:
            if self.current_token.type != TokenType.LETTER:
                self.error("expected parameter name (letter)")
            pname = self.current_token.value
            self.eat(TokenType.LETTER)
            is_arr = False
            curr_type: TokenType = self.current_token.type
            if curr_type == TokenType.LBRACKET:
                self.eat(TokenType.LBRACKET)
                self.eat(TokenType.RBRACKET)
                is_arr = True
            lst.append(Param(pname, is_arr))

            curr_type_comma: TokenType = self.current_token.type
            if curr_type_comma == TokenType.COMMA:
                self.eat(TokenType.COMMA)
            else:
                break
        return lst

    def parse_opt_auto_define_list(self) -> list[Param]:
        if self.current_token.type != TokenType.AUTO:
            return []
        self.eat(TokenType.AUTO)
        lst = self.parse_define_list()
        curr_type: TokenType = self.current_token.type
        if curr_type == TokenType.NEWLINE:
            self.eat(TokenType.NEWLINE)
        elif curr_type == TokenType.SEMICOLON:
            self.eat(TokenType.SEMICOLON)
        else:
            self.error("expected newline or semicolon after auto declaration")
        return lst

    def parse_relational_expression(self) -> ASTNode:
        left = self.parse_expression()
        if self.current_token.type == TokenType.REL_OP:
            op = self.current_token.value
            self.eat(TokenType.REL_OP)
            right = self.parse_expression()
            return RelationalOp(op, left, right)
        return left

    def parse_expression(self) -> ASTNode:
        return self.parse_expr_precedence(0)

    def parse_expr_precedence(self, min_prec: int) -> ASTNode:
        left = self.parse_prefix()
        while True:
            op_prec, op_class, right_assoc = self.get_infix_info(self.current_token)
            if op_prec < min_prec:
                break

            op_val = self.current_token.value
            self.eat(self.current_token.type)

            next_min_prec = op_prec if right_assoc else op_prec + 1
            right = self.parse_expr_precedence(next_min_prec)

            left = AssignOp(op_val, left, right) if op_class == "ASSIGN" else BinaryOp(op_val, left, right)

        return left

    def get_infix_info(self, token: Token) -> tuple[int, str, bool]:
        t = token.type
        if t == TokenType.ASSIGN_OP:
            return (1, "ASSIGN", True)
        if t in (TokenType.PLUS, TokenType.MINUS):
            return (2, "BINARY", False)
        if t == TokenType.MUL_OP:
            return (3, "BINARY", False)
        if t == TokenType.EXP:
            return (4, "BINARY", True)
        return (-1, "", False)

    def parse_prefix(self) -> ASTNode:
        t = self.current_token.type
        if t == TokenType.MINUS:
            self.eat(TokenType.MINUS)
            expr = self.parse_expr_precedence(5)  # unary has high priority
            return UnaryOp("-", expr)
        if t == TokenType.INCR_DECR:
            op = self.current_token.value
            self.eat(TokenType.INCR_DECR)
            target = self.parse_named_expression()
            return UpdateOp(op, True, target)

        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        t = self.current_token.type
        if t == TokenType.NUMBER:
            val = self.current_token.value
            self.eat(TokenType.NUMBER)
            return NumberLiteral(val)
        if t == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            expr = self.parse_expression()
            self.eat(TokenType.RPAREN)
            return expr
        if t == TokenType.LENGTH:
            self.eat(TokenType.LENGTH)
            self.eat(TokenType.LPAREN)
            expr = self.parse_expression()
            self.eat(TokenType.RPAREN)
            return LengthCall(expr)
        if t == TokenType.SQRT:
            self.eat(TokenType.SQRT)
            self.eat(TokenType.LPAREN)
            expr = self.parse_expression()
            self.eat(TokenType.RPAREN)
            return SqrtCall(expr)
        if t == TokenType.SCALE and self.peek_token_type() == TokenType.LPAREN:
            self.eat(TokenType.SCALE)
            self.eat(TokenType.LPAREN)
            expr = self.parse_expression()
            self.eat(TokenType.RPAREN)
            return ScaleCall(expr)

        if t == TokenType.LETTER and self.peek_token_type() == TokenType.LPAREN:
            name = self.current_token.value
            self.eat(TokenType.LETTER)
            self.eat(TokenType.LPAREN)
            args = self.parse_opt_argument_list()
            self.eat(TokenType.RPAREN)
            return CallExpr(name, args)

        target = self.parse_named_expression()
        if self.current_token.type == TokenType.INCR_DECR:
            op = self.current_token.value
            self.eat(TokenType.INCR_DECR)
            return UpdateOp(op, False, target)
        return target

    def parse_named_expression(self) -> ASTNode:  # noqa: RET503
        t = self.current_token.type
        if t == TokenType.SCALE:
            self.eat(TokenType.SCALE)
            return RegisterAccess("scale")
        if t == TokenType.IBASE:
            self.eat(TokenType.IBASE)
            return RegisterAccess("ibase")
        if t == TokenType.OBASE:
            self.eat(TokenType.OBASE)
            return RegisterAccess("obase")
        if t == TokenType.LETTER:
            name = self.current_token.value
            self.eat(TokenType.LETTER)
            if self.current_token.type == TokenType.LBRACKET:
                self.eat(TokenType.LBRACKET)
                idx = self.parse_expression()
                self.eat(TokenType.RBRACKET)
                return ArrayAccess(name, idx)
            return Variable(name)

        self.error(f"expected named expression, got {t}")

    def parse_opt_argument_list(self) -> list[ASTNode]:
        if self.current_token.type == TokenType.RPAREN:
            return []
        return self.parse_argument_list()

    def parse_argument_list(self) -> list[ASTNode]:
        args: list[ASTNode] = []
        while True:
            # Check for whole array argument: LETTER []
            if (
                self.current_token.type == TokenType.LETTER
                and self.peek_token_type(0) == TokenType.LBRACKET
                and self.peek_token_type(1) == TokenType.RBRACKET
            ):
                name = self.current_token.value
                self.eat(TokenType.LETTER)
                self.eat(TokenType.LBRACKET)
                self.eat(TokenType.RBRACKET)
                args.append(ArrayArg(name))
            else:
                args.append(self.parse_expression())

            if self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
            else:
                break
        return args
