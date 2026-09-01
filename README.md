# claude-code-test
Claudeからの作業

## tiny_lisp.py — a small educational Lisp interpreter

`tiny_lisp.py` is a small, readable Lisp interpreter written from scratch
using only the Python standard library (no existing Lisp/Scheme library is
used). It is organized into clearly separated pieces: a tokenizer, a
parser, atom conversion, an environment, an evaluator, a procedure/closure
representation, a standard environment of built-ins, and a command-line
interface with a REPL.

### Language features

- **Numbers**: integers and floating-point numbers.
- **Symbols** and **S-expressions** (nested lists).
- **Arithmetic**: `+` `-` `*` `/` (variadic, e.g. `(+ 1 2 3)`).
- **Comparisons**: `>` `<` `>=` `<=` `=` (chainable, e.g. `(< 1 2 3)`).
- **Special forms**: `define`, `if`, `lambda`, `begin`, `quote`.
- **Function application**, **lexical environments/closures**, and
  **recursion**.

### Running it

There are four ways to run the interpreter.

**1. Interactive REPL** — maintains one environment across commands:

```
$ python tiny_lisp.py
tinylisp> (+ 1 2)
3
tinylisp> (define x 10)
10
tinylisp> (* x 5)
50
tinylisp> quit
```

**2. Evaluate an expression from the command line:**

```
$ python tiny_lisp.py -e "(+ 40 2)"
42
```

**3. Execute a Lisp source file** (expressions run sequentially, sharing
one environment; see `examples/demo.lisp`):

```
$ python tiny_lisp.py examples/demo.lisp
```

**4. Read from standard input / a pipe:**

```
$ echo "(* 6 7)" | python tiny_lisp.py
42
```

### Examples

```lisp
(+ 1 2)                  ; => 3
(* 3 4)                  ; => 12

(define x 10)
(+ x 5)                  ; => 15

(if (> x 5) 100 0)       ; => 100

((lambda (x) (* x x)) 5) ; => 25

(define square (lambda (x) (* x x)))
(square 12)               ; => 144

(quote (1 2 3))            ; => (1 2 3)
(quote x)                  ; => x, even if x is undefined
```

Closures:

```lisp
(define make-adder
  (lambda (x)
    (lambda (y)
      (+ x y))))

(define add10 (make-adder 10))
(add10 7)                 ; => 17
```

Recursion:

```lisp
(define factorial
  (lambda (n)
    (if (= n 0)
        1
        (* n (factorial (- n 1))))))

(factorial 10)             ; => 3628800
```

### Error handling

Errors (unmatched parentheses, undefined symbols, wrong number of lambda
arguments, calling a non-function, division by zero, malformed special
forms) are all raised as `LispError` subclasses. In `-e`/file/stdin mode
they are printed to stderr and the process exits with a non-zero status;
in the REPL they are reported to stderr and the REPL keeps running.

### Tests

Tests use Python's standard `unittest` framework and cover tokenizing,
parsing, arithmetic, `define`/lookup, `if`, `lambda`, closures, recursion,
error cases, and the command-line interface (`-e`, stdin, exit codes).

```
python -m unittest discover -s tests -v
```
