from IPython.display import display, Math, Latex, Markdown, HTML
import sympy as sp
from process_latex import process_sympy
from string import Template
import json
import markdown
import uuid
import copy
import requests


class MarkdownBlock:
    """Encapsulates a Markdown string

    The Markdown string can contain parameters using the `@param` notation.
    A substitution for each parameter should be supplied in a dictionary with keys corresponding to the parameters and values being SymPy objects.

    Attributes:
        md: A (parameterized) Markdown string.
        params: A dictionary containing the substitutions. 
    """

    class __MathTemplate(Template):
        delimiter = "@"

    def __init__(self, md: str, params: dict = {}):
        """Inits MarkdownBlock class with a markdown string and a dictionary with substitutions if used"""
        self.md = md
        self.params = copy.deepcopy(params)

        for key in self.params:
            self.params[key] = sp.latex(self.params[key])

        self.html = self.to_html(
            self.__MathTemplate(md).substitute(self.params))

    def to_html(self, string):
        """"Converts a Markdown string to html,
        given the fixed configuration defined below.
        Should not be required in typical use-cases,
        can be used for debugging purposes.

        Attributes:
            string: A Markdown string.
        """

        # b64 is used for images to avoid static hosting of images on server (so we only need the JSON)
        extensions = ['pymdownx.arithmatex', 'pymdownx.b64', 'toc']
        extension_config = {
            "pymdownx.arithmatex": {
                "generic": True,
                "tex_inline_wrap": ['$', '$'],
                "tex_block_wrap": ['[', ']'],
            }
        }
        return markdown.markdown(string, extensions=extensions, extension_configs=extension_config)


class Exercise:
    """Contains logic and data defining an exercise.

    Attributes:
        md: A string containing Markdown or a MarkdownBlock object
    """

    def __init__(self, md):
        """Inits Exercise class with a string containing Markdown or a MarkdownBlock"""
        self.html = self.__markup_to_html(md)
        self.answers = {}
        self.default_feedback = "Incorrect, no specific feedback provided matching your answer"
        self.id = str(uuid.uuid4())
        self.data = None

    def __markup_to_html(self, md) -> str:
        if isinstance(md, str):
            return MarkdownBlock(md).html
        elif isinstance(md, MarkdownBlock):
            return md.html
        else:
            Exception(
                "Supplied input markup must be either a string or MarkdownBlock")

    def add_default_feedback(self, feedback):
        """Sets default feedback shown to the user when a wrong answer is supplied not matching any answer rule

        Attributes:
            feedback: A string containing Markdown or a MarkdownBlock object
        """
        self.default_feedback = self.__markup_to_html(feedback)

    def add_answer(self, expression, correct: bool, feedback):
        """Add an answer to match the student answer against 

        Attributes:
            expression: SymPy object expression of the answer
            correct: boolean indicating whether the answer is correct or not 
            feedback: A string containing Markdown or a MarkdownBlock object
        """
        feedback = self.__markup_to_html(feedback)
        latex_answer_string = sp.latex(expression)
        answer = {
            "expression": latex_answer_string,
            "correct": correct,
            "feedback": feedback
        }
        self.answers[latex_answer_string] = answer

    def __evaluate(self, expression):
        for _, answer in self.answers.items():
            if sp.simplify(process_sympy(answer["expression"])) == sp.simplify(expression):
                return answer
        return {"expression": None, "correct": False, "feedback": self.default_feedback}

    def evaluate_answer(self, expression):
        """Evaluates given expression against existing answers and displays the feedback for that answer

        Attributes:  
            expression: SymPy object expression of the answer
        """
        return display(HTML(self.__evaluate(expression)["feedback"]))

    def display(self):
        """Show rendered exercise content in jupyter-notebook"""
        display(HTML(self.html))

    def publish(self, url):
        """Publishes the exercise at the provided url so it can be 'played'

        Note: exercises should be written by calling e.write() prior to publishing!

        Attributes:
            url: the url to publish the exercise
        """
        if self.data == None:
            Exception(
                "Write the exercise by callin `e.write()` prior to calling `e.publish()`")
        j = self.data
        r = requests.post(url, json=self.data)
        if (r.status_code == 200):
            print("Published succesfully, preview at: {}".format(
                r.json()["url"]))
        else:
            print("Publishing error code: {}".format(r.status_code))

    def write(self):
        """Prepares JSON representation of exercise for network-transport"""
        exercise = {
            "id": self.id,
            "html": self.html,
            "default_feedback": self.default_feedback,
            "answers": self.answers
        }

        self.data = exercise

        # Used for local authoring only
        try:
            with open("../sympy_api/exercises/{id}".format(id=self.id), 'w', encoding='utf-8') as f:
                json.dump(exercise, f, ensure_ascii=False, indent=4)
        except Exception:
            pass


class Page:
    """Page class to aid writing complete interactive lecture note pages with embedded exercise-blocks"""

    def __init__(self, structure: list = []):
        self.structure = structure

    def append(self, t):
        self.structure.append(t)

    def reset(self):
        self.structure = []

    def __markup_to_html(self, md) -> str:
        if isinstance(md, str):
            return MarkdownBlock(md).html
        elif isinstance(md, MarkdownBlock):
            return md.html
        else:
            Exception(
                "Supplied input markup must be either a string or MarkdownBlock")

    def write(self):
        tuples = []
        for element in self.structure:
            html = self.__markup_to_html(element[0])
            exercises = element[1]
            tuples.append({
                "html": html,
                "exercises": [e.data for e in exercises]
            })

        article = {
            # TODO: index separate
            "id": str(uuid.uuid4()),
            "tuples": tuples
        }

        with open("../sympy_api/full_page.json", 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=4)

        print("Data written succesfully.")
