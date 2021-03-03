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


