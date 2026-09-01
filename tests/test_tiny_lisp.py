import os
import subprocess
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import tiny_lisp as tl  # noqa: E402


class TestTokenizeAndParse(unittest.TestCase):
    def test_tokenize_simple(self):
        self.assertEqual(tl.tokenize("(+ 1 2)"), ["(", "+", "1", "2", ")"])

    def test_tokenize_strips_comments(self):
        self.assertEqual(
            tl.tokenize("(+ 1 2) ; add them\n(* 3 4)"),
            ["(", "+", "1", "2", ")", "(", "*", "3", "4", ")"],
        )

    def test_parse_simple(self):
        self.assertEqual(tl.parse("(+ 1 2)"), ["+", 1, 2])

    def test_parse_nested_expressions(self):
        self.assertEqual(
            tl.parse("(+ 1 (* 2 3) (- 5 1))"),
            ["+", 1, ["*", 2, 3], ["-", 5, 1]],
        )

    def test_parse_float_and_symbol(self):
        self.assertEqual(tl.parse("(+ 1.5 x)"), ["+", 1.5, "x"])

    def test_parse_all_multiple_expressions(self):
        exps = tl.parse_all("(+ 1 2) (* 3 4)")
        self.assertEqual(exps, [["+", 1, 2], ["*", 3, 4]])

    def test_unmatched_open_paren(self):
        with self.assertRaises(tl.ParseError):
            tl.parse("(+ 1 2")

    def test_unmatched_close_paren(self):
        with self.assertRaises(tl.ParseError):
            tl.parse("(+ 1 2))")


class TestEval(unittest.TestCase):
    def setUp(self):
        self.env = tl.standard_env()

    def ev(self, source):
        result = None
        for expr in tl.parse_all(source):
            result = tl.eval_exp(expr, self.env)
        return result

    def test_arithmetic(self):
        self.assertEqual(self.ev("(+ 1 2)"), 3)
        self.assertEqual(self.ev("(* 3 4)"), 12)
        self.assertEqual(self.ev("(- 10 4)"), 6)
        self.assertEqual(self.ev("(/ 10 2)"), 5)
        self.assertEqual(self.ev("(+ 1 2 3 4)"), 10)

    def test_division_by_zero(self):
        with self.assertRaises(tl.LispError):
            self.ev("(/ 1 0)")

    def test_comparisons(self):
        self.assertTrue(self.ev("(> 5 3)"))
        self.assertFalse(self.ev("(> 3 5)"))
        self.assertTrue(self.ev("(< 1 2)"))
        self.assertTrue(self.ev("(>= 5 5)"))
        self.assertTrue(self.ev("(<= 3 3 4)"))
        self.assertTrue(self.ev("(= 3 3)"))
        self.assertFalse(self.ev("(= 3 4)"))

    def test_define_and_symbol_lookup(self):
        self.assertEqual(self.ev("(define x 10)"), 10)
        self.assertEqual(self.ev("x"), 10)
        self.assertEqual(self.ev("(+ x 5)"), 15)

    def test_undefined_symbol(self):
        with self.assertRaises(tl.LispError):
            self.ev("y")

    def test_if(self):
        self.ev("(define x 10)")
        self.assertEqual(self.ev("(if (> x 5) 100 0)"), 100)
        self.assertEqual(self.ev("(if (< x 5) 100 0)"), 0)

    def test_lambda_and_function_call(self):
        self.assertEqual(self.ev("((lambda (x) (* x x)) 5)"), 25)

    def test_define_function_and_call(self):
        self.ev("(define square (lambda (x) (* x x)))")
        self.assertEqual(self.ev("(square 12)"), 144)

    def test_lexical_closures(self):
        self.ev(
            """
            (define make-adder
              (lambda (x)
                (lambda (y)
                  (+ x y))))
            """
        )
        self.ev("(define add10 (make-adder 10))")
        self.assertEqual(self.ev("(add10 7)"), 17)
        # a second closure must not share state with the first
        self.ev("(define add100 (make-adder 100))")
        self.assertEqual(self.ev("(add100 1)"), 101)
        self.assertEqual(self.ev("(add10 1)"), 11)

    def test_recursion_factorial(self):
        self.ev(
            """
            (define factorial
              (lambda (n)
                (if (= n 0)
                    1
                    (* n (factorial (- n 1))))))
            """
        )
        self.assertEqual(self.ev("(factorial 10)"), 3628800)

    def test_begin(self):
        self.assertEqual(self.ev("(begin (define x 10) (* x 5))"), 50)

    def test_incorrect_lambda_arguments(self):
        self.ev("(define f (lambda (x y) (+ x y)))")
        with self.assertRaises(tl.LispError):
            self.ev("(f 1)")

    def test_calling_non_function(self):
        self.ev("(define x 5)")
        with self.assertRaises(tl.LispError):
            self.ev("(x 1 2)")

    def test_malformed_define(self):
        with self.assertRaises(tl.LispError):
            self.ev("(define x)")

    def test_malformed_if(self):
        with self.assertRaises(tl.LispError):
            self.ev("(if 1 2)")

    def test_malformed_lambda(self):
        with self.assertRaises(tl.LispError):
            self.ev("(lambda x (+ x 1))")

    def test_quote_flat_list(self):
        self.assertEqual(self.ev("(quote (1 2 3))"), [1, 2, 3])

    def test_quote_nested_list(self):
        self.assertEqual(
            self.ev("(quote (1 (2 3) (+ 4 5)))"),
            [1, [2, 3], ["+", 4, 5]],
        )

    def test_quote_does_not_evaluate(self):
        # (+ 1 2) inside quote must stay an unevaluated list, not become 3.
        self.assertEqual(self.ev("(quote (+ 1 2))"), ["+", 1, 2])

    def test_quote_does_not_look_up_undefined_symbol(self):
        # `x` is never defined in this environment; quoting it must not
        # trigger a symbol lookup.
        self.assertEqual(self.ev("(quote x)"), "x")

    def test_quote_empty_list(self):
        self.assertEqual(self.ev("(quote ())"), [])

    def test_malformed_quote_no_args(self):
        with self.assertRaises(tl.LispError):
            self.ev("(quote)")

    def test_malformed_quote_too_many_args(self):
        with self.assertRaises(tl.LispError):
            self.ev("(quote 1 2)")


class TestCLI(unittest.TestCase):
    def run_cli(self, args=None, input_text=None):
        cmd = [sys.executable, os.path.join(ROOT_DIR, "tiny_lisp.py")]
        if args:
            cmd += args
        return subprocess.run(
            cmd, input=input_text, capture_output=True, text=True, timeout=10
        )

    def test_eval_flag(self):
        result = self.run_cli(["-e", "(+ 40 2)"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "42")

    def test_eval_flag_lambda(self):
        result = self.run_cli(["-e", "((lambda (x) (* x x)) 12)"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "144")

    def test_stdin_input(self):
        result = self.run_cli(input_text="(* 6 7)\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "42")

    def test_file_execution(self):
        demo = os.path.join(ROOT_DIR, "examples", "demo.lisp")
        result = self.run_cli([demo])
        self.assertEqual(result.returncode, 0)
        self.assertIn("3628800", result.stdout.split())

    def test_error_exit_code_undefined_symbol(self):
        result = self.run_cli(["-e", "(+ y 1)"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error", result.stderr)

    def test_error_exit_code_unmatched_paren(self):
        result = self.run_cli(["-e", "(+ 1 2"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error", result.stderr)


if __name__ == "__main__":
    unittest.main()
