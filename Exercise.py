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

    class __MathTemplate(Template):
        delimiter = "@"

    def __init__(self, md: str, params: dict = {}):
        self.md = md
        self.params = copy.deepcopy(params)

        for key in self.params:
            try:
                self.params[key] = sp.latex(self.params[key])
            except:
                Exception(
                    f"Object: {self.params[key]}, cannot be converted to latex, provide a SymPy object that can be converted to LaTeX.")

        # TODO: warning for unused params?
        self.html = self.to_html(
            self.__MathTemplate(md).substitute(self.params))

    def to_html(self, string):
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
    """        
    Contains exercise markup and answers 

    :param md: this is the first param
    """

    def __init__(self, md):
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
        self.default_feedback = self.__markup_to_html(feedback)

    def add_answer(self, expression, correct: bool, feedback):
        """        
        Add an answer to match the student answer against 

        :param expression: sympy expression (object) of answer to match against 
        :param correct: indicates whether the answer is correct
        :param feedback: feedback shown to user when answer matches
        """
        feedback = self.__markup_to_html(feedback)
        latex_answer_string = sp.latex(expression)
        answer = {
            "expression": latex_answer_string,
            "correct": correct,
            "feedback": feedback
        }
        self.answers[latex_answer_string] = answer

    def evaluate(self, expression):
        for _, answer in self.answers.items():
            if sp.simplify(process_sympy(answer["expression"])) == sp.simplify(expression):
                return answer
        return {"expression": None, "correct": False, "feedback": self.default_feedback}

    def evaluate_answer(self, expression):
        return display(HTML(self.evaluate(expression)["feedback"]))

    def display(self):
        display(HTML(self.html))

    def publish(self, url):
        j = self.data
        r = requests.post(url, json=self.data)
        if (r.status_code == 200):
            print("Published succesfully, preview at: {}".format(
                r.json()["url"]))
        else:
            print("Publishing error code: {}".format(r.status_code))

    def write(self):
        exercise = {
            "id": self.id,
            "html": self.html,
            "default_feedback": self.default_feedback,
            "answers": self.answers
        }

        self.data = exercise

        with open("../sympy_api/exercises/{id}".format(id=self.id), 'w', encoding='utf-8') as f:
            json.dump(exercise, f, ensure_ascii=False, indent=4)


class Page:
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
