; demo.lisp - a short tour of tiny_lisp features
; run with: python tiny_lisp.py examples/demo.lisp

; --- define and arithmetic ---
(define x 10)
(+ x 5)
(* 3 4)
(- 10 4)
(/ 10 2)

; --- lambda and function calls ---
(define square (lambda (x) (* x x)))
(square 12)

; --- closures ---
(define make-adder
  (lambda (x)
    (lambda (y)
      (+ x y))))
(define add10 (make-adder 10))
(add10 7)

; --- if ---
(if (> x 5) 100 0)

; --- recursion ---
(define factorial
  (lambda (n)
    (if (= n 0)
        1
        (* n (factorial (- n 1))))))
(factorial 10)
