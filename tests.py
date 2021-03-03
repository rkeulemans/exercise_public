import pytest
import numpy as np
from Exercise import MarkdownBlock, Exercise

@pytest.mark.xfail(raises=KeyError)
def test_markdownblock_param_failure():
	MarkdownBlock("@a")

@pytest.mark.xfail(raises=KeyError)
def text_markdownblock_param_that_cannot_be_converted_to_latex():
	MarkdownBlock("@a", {"a": np.arange(10)})

def test_markdownblock_param_success():
	m = MarkdownBlock("@a", {"a": 1})
	assert m.html == "<p>1</p>"


