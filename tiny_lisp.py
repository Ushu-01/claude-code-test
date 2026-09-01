#!/usr/bin/env python3
"""tiny_lisp.py - a small educational Lisp interpreter.

Supports numbers, symbols, S-expressions, basic arithmetic and
comparison operators, and the special forms `define`, `if`, `lambda`,
`begin` and `quote` (including the `'expr` reader shorthand for
`(quote expr)`). Implemented with only the Python standard library.
"""

import sys


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class LispError(Exception):
    """Base class for all errors raised by the interpreter."""


class ParseError(LispError):
    """Raised for tokenizer/parser problems, e.g. unmatched parentheses."""


class EvalError(LispError):
    """Raised for problems found while evaluating an expression."""


Symbol = str


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def tokenize(source):
    """Turn a Lisp source string into a flat list of token strings."""
    lines = (line.split(";", 1)[0] for line in source.split("\n"))
    source = "\n".join(lines)
    source = source.replace("(", " ( ").replace(")", " ) ").replace("'", " ' ")
    return source.split()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse(source):
    """Parse a string containing exactly one top-level expression."""
    tokens = tokenize(source)
    if not tokens:
        raise ParseError("unexpected EOF while parsing")
    exp, rest = read_from_tokens(tokens)
    if rest:
        raise ParseError(f"unexpected token(s) after expression: {rest}")
    return exp


def parse_all(source):
    """Parse a string containing zero or more top-level expressions."""
    tokens = tokenize(source)
    exps = []
    while tokens:
        exp, tokens = read_from_tokens(tokens)
        exps.append(exp)
    return exps


def read_from_tokens(tokens):
    if not tokens:
        raise ParseError("unexpected EOF while parsing (missing closing ')')")
    token, tokens = tokens[0], tokens[1:]
    if token == "'":
        if not tokens:
            raise ParseError("unexpected EOF after quote (\"'\")")
        expr, tokens = read_from_tokens(tokens)
        return ["quote", expr], tokens
    if token == "(":
        items = []
        while tokens and tokens[0] != ")":
            item, tokens = read_from_tokens(tokens)
            items.append(item)
        if not tokens:
            raise ParseError("unexpected EOF while parsing (missing closing ')')")
        return items, tokens[1:]  # drop the matching ')'
    if token == ")":
        raise ParseError("unexpected ')'")
    return to_atom(token), tokens


def to_atom(token):
    """Convert a single token into an int, float, or Symbol."""
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return Symbol(token)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class Env(dict):
    """A mapping of {symbol: value}, chained to an outer environment."""

    def __init__(self, params=(), args=(), outer=None):
        super().__init__()
        if len(params) != len(args):
            raise EvalError(
                f"expected {len(params)} argument(s), got {len(args)}"
            )
        self.update(zip(params, args))
        self.outer = outer

    def find(self, symbol):
        """Return the innermost Env in which `symbol` is bound."""
        if symbol in self:
            return self
        if self.outer is None:
            raise EvalError(f"undefined symbol: {symbol}")
        return self.outer.find(symbol)


# ---------------------------------------------------------------------------
# Procedure / closure representation
# ---------------------------------------------------------------------------

class Procedure:
    """A user-defined procedure created by `lambda`, closing over `env`."""

    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        local_env = Env(self.params, args, self.env)
        return eval_exp(self.body, local_env)


# ---------------------------------------------------------------------------
# Standard environment
# ---------------------------------------------------------------------------

def _add(*args):
    return sum(args)


def _sub(*args):
    if not args:
        raise EvalError("'-' needs at least 1 argument")
    if len(args) == 1:
        return -args[0]
    result = args[0]
    for a in args[1:]:
        result -= a
    return result


def _mul(*args):
    result = 1
    for a in args:
        result *= a
    return result


def _div(*args):
    if not args:
        raise EvalError("'/' needs at least 1 argument")
    if len(args) == 1:
        args = (1,) + tuple(args)
    result = args[0]
    for a in args[1:]:
        if a == 0:
            raise EvalError("division by zero")
        result = result / a
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return result


def _chain(comparator):
    """Build a variadic comparison, e.g. (< 1 2 3) -> 1<2 and 2<3."""

    def compare(*args):
        return all(comparator(a, b) for a, b in zip(args, args[1:]))

    return compare


def standard_env():
    """Create a fresh global environment with the built-in procedures."""
    env = Env()
    env.update(
        {
            "+": _add,
            "-": _sub,
            "*": _mul,
            "/": _div,
            ">": _chain(lambda a, b: a > b),
            "<": _chain(lambda a, b: a < b),
            ">=": _chain(lambda a, b: a >= b),
            "<=": _chain(lambda a, b: a <= b),
            "=": _chain(lambda a, b: a == b),
        }
    )
    return env


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

def eval_exp(x, env):
    """Evaluate a parsed expression `x` in environment `env`."""
    if isinstance(x, Symbol):
        return env.find(x)[x]

    if not isinstance(x, list):
        return x  # numbers are self-evaluating

    if len(x) == 0:
        raise EvalError("cannot evaluate an empty list ()")

    op, *args = x

    if op == "quote":
        if len(args) != 1:
            raise EvalError("malformed 'quote': expected (quote expr)")
        return args[0]

    if op == "define":
        if len(args) != 2 or not isinstance(args[0], Symbol):
            raise EvalError("malformed 'define': expected (define symbol expr)")
        symbol, expr = args
        value = eval_exp(expr, env)
        env[symbol] = value
        return value

    if op == "if":
        if len(args) != 3:
            raise EvalError("malformed 'if': expected (if test conseq alt)")
        test, conseq, alt = args
        branch = conseq if eval_exp(test, env) else alt
        return eval_exp(branch, env)

    if op == "lambda":
        if len(args) != 2 or not isinstance(args[0], list):
            raise EvalError(
                "malformed 'lambda': expected (lambda (params...) body)"
            )
        params, body = args
        if not all(isinstance(p, Symbol) for p in params):
            raise EvalError("lambda parameters must be symbols")
        return Procedure(params, body, env)

    if op == "begin":
        if not args:
            raise EvalError("malformed 'begin': expected at least one expression")
        result = None
        for expr in args:
            result = eval_exp(expr, env)
        return result

    # Function application: evaluate the operator and operands, then call.
    proc = eval_exp(op, env)
    if not callable(proc):
        raise EvalError(f"'{stringify(proc)}' is not callable")
    values = [eval_exp(a, env) for a in args]
    try:
        return proc(*values)
    except LispError:
        raise
    except ZeroDivisionError:
        raise EvalError("division by zero")
    except TypeError as exc:
        raise EvalError(f"error calling procedure: {exc}")


def stringify(exp):
    """Render an evaluated value the way the REPL prints it."""
    if isinstance(exp, bool):
        return "#t" if exp else "#f"
    if isinstance(exp, list):
        return "(" + " ".join(stringify(e) for e in exp) + ")"
    if isinstance(exp, Procedure) or callable(exp):
        return "#<procedure>"
    return str(exp)


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------

def run_source(source, env):
    """Parse and evaluate every top-level expression in `source`.

    Prints the result of each expression to stdout. Returns a process
    exit code: 0 on success, 1 if a LispError occurred.
    """
    try:
        expressions = parse_all(source)
        for expr in expressions:
            value = eval_exp(expr, env)
            print(stringify(value))
    except LispError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def run_repl(env):
    """Run an interactive read-eval-print loop over `env`."""
    while True:
        try:
            line = input("tinylisp> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        line = line.strip()
        if line in ("quit", "exit"):
            return
        if not line:
            continue
        try:
            for expr in parse_all(line):
                value = eval_exp(expr, env)
                print(stringify(value))
        except LispError as exc:
            print(f"Error: {exc}", file=sys.stderr)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    env = standard_env()

    if argv and argv[0] == "-e":
        if len(argv) < 2:
            print("Error: -e requires a Lisp expression", file=sys.stderr)
            return 1
        return run_source(argv[1], env)

    if argv:
        path = argv[0]
        try:
            with open(path, encoding="utf-8") as f:
                source = f.read()
        except OSError as exc:
            print(f"Error: could not read file '{path}': {exc}", file=sys.stderr)
            return 1
        return run_source(source, env)

    if not sys.stdin.isatty():
        source = sys.stdin.read()
        if not source.strip():
            return 0
        return run_source(source, env)

    run_repl(env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
