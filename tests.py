import pytest
import numpy as np
import sympy as sp
from Exercise import MarkdownBlock, Exercise


def test_markdownblock_param_failure_no_substitution_supplied():
    with pytest.raises(Exception):
        MarkdownBlock("@a")


def test_markdownblock_param_success_sympy_matrix():
    m = MarkdownBlock("@a", {"a": sp.Matrix([1])})
    assert m.html == r"<p>\left[\begin{matrix}1\end{matrix}\right]</p>"


def test_markdownblock_param_success_integer():
    m = MarkdownBlock("@a", {"a": 1})
    assert m.html == "<p>1</p>"


def test_non_parameterized_exercise_integer_addition():
    e = Exercise("What is $1 + 1$?")
    ans = sp.simplify(2)
    e.add_answer(ans, True, "Correct!")
    # Check if the answer is stored correctly
    assert e.evaluate(ans)["correct"] == True
    # Check if false on faulty answer
    assert e.evaluate(sp.simplify(0))["correct"] == False


def test_parameterized_exercise_integer_addition():
    s = "What is $@a + @b$?"
    params = {}
    params["a"] = sp.simplify(5)
    params["b"] = sp.simplify(10)

    ans = params["a"] + params["b"]

    e = Exercise(MarkdownBlock("What is $@a + @b$?", params))

    e.add_answer(ans, True, "Correct!")
    # Check if the answer is stored correctly
    assert e.evaluate(ans)["correct"] == True
    # Check if false on faulty answer
    assert e.evaluate(sp.simplify(0))["correct"] == False


def test_parameterized_exercise_integer_addition():
    s = "What is $@a + @b$?"
    params = {}
    params["a"] = sp.Matrix([1, 1, 1])
    params["b"] = sp.Matrix([1, 1, 1])

    ans = params["a"] + params["b"]

    e = Exercise(MarkdownBlock("What is $@a + @b$?", params))

    e.add_answer(ans, True, "Correct!")
    # Check if the answer is stored correctly
    assert e.evaluate(ans)["correct"] == True
    # Check if false on faulty answer
    assert e.evaluate(sp.simplify(0))["correct"] == False
