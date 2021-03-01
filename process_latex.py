import sympy
import antlr4
from antlr4.error.ErrorListener import ErrorListener
from sympy.core.operations import AssocOp

try:
    from gen.PSParser import PSParser
    from gen.PSLexer import PSLexer
    from gen.PSListener import PSListener
except:
    from .gen.PSParser import PSParser
    from .gen.PSLexer import PSLexer
    from .gen.PSListener import PSListener

from sympy.printing.str import StrPrinter

from sympy.parsing.sympy_parser import parse_expr

import hashlib

# default process normal algebra
PLACEHOLDER_VALUES = {}


def process_sympy(sympy, placeholder_values={}):

    # placeholder values
    global PLACEHOLDER_VALUES
    if len(placeholder_values) > 0:
        PLACEHOLDER_VALUES = placeholder_values
    else:
        PLACEHOLDER_VALUES = {}

    # setup listener
    matherror = MathErrorListener(sympy)

    # stream input
    stream = antlr4.InputStream(sympy)
    lex    = PSLexer(stream)
    lex.removeErrorListeners()
    lex.addErrorListener(matherror)

    tokens = antlr4.CommonTokenStream(lex)
    parser = PSParser(tokens)

    # remove default console error listener
    parser.removeErrorListeners()
    parser.addErrorListener(matherror)

    # process the input
    return_data = None
    math = parser.math()

    # if a list
    if math.relation_list():
        return_data = []

        # go over list items
        relation_list = math.relation_list().relation_list_content()
        for list_item in relation_list.relation():
            expr = convert_relation(list_item)
            return_data.append(expr)

    # if not, do default
    else:
        relation = math.relation()
        return_data = convert_relation(relation)

    return return_data


class MathErrorListener(ErrorListener):
    def __init__(self, src):
        super(ErrorListener, self).__init__()
        self.src = src

    def syntaxError(self, recog, symbol, line, col, msg, e):
        fmt = "%s\n%s\n%s"
        marker = "~" * col + "^"

        if msg.startswith("missing"):
            err = fmt % (msg, self.src, marker)
        elif msg.startswith("no viable"):
            err = fmt % ("I expected something else here", self.src, marker)
        elif msg.startswith("mismatched"):
            names = PSParser.literalNames
            expected = [names[i] for i in e.getExpectedTokens() if i < len(names)]
            if len(expected) < 10:
                expected = " ".join(expected)
                err = (fmt % ("I expected one of these: " + expected,
                    self.src, marker))
            else:
                err = (fmt % ("I expected something else here", self.src, marker))
        else:
            err = fmt % ("I don't understand this", self.src, marker)
        raise Exception(err)

def convert_relation(rel):
    if rel.expr():
        return convert_expr(rel.expr())

    lh = convert_relation(rel.relation(0))
    rh = convert_relation(rel.relation(1))
    if rel.LT():
        return sympy.StrictLessThan(lh, rh, evaluate=False)
    elif rel.LTE():
        return sympy.LessThan(lh, rh, evaluate=False)
    elif rel.GT():
        return sympy.StrictGreaterThan(lh, rh, evaluate=False)
    elif rel.GTE():
        return sympy.GreaterThan(lh, rh, evaluate=False)
    elif rel.EQUAL():
        return sympy.Eq(lh, rh, evaluate=False)
    elif rel.UNEQUAL():
        return sympy.Ne(lh, rh, evaluate=False)

def convert_expr(expr):
    if expr.additive():
        return convert_add(expr.additive())

def convert_matrix(matrix):

    # build matrix
    row = matrix.matrix_row()
    tmp = []
    rows = 0;
    for r in row:
        tmp.append([]);
        for expr in r.expr():
            tmp[rows].append(convert_expr(expr))
        rows = rows + 1

    #return the matrix
    return sympy.Matrix(tmp)


def convert_add(add):
    if add.ADD():
        lh = convert_add(add.additive(0))
        rh = convert_add(add.additive(1))

        if lh.is_Matrix or rh.is_Matrix:
            return sympy.MatAdd(lh, rh, evaluate=False)
        else:
            return sympy.Add(lh, rh, evaluate=False)
    elif add.SUB():
        lh = convert_add(add.additive(0))
        rh = convert_add(add.additive(1))

        if lh.is_Matrix or rh.is_Matrix:
            return sympy.MatAdd(lh, sympy.MatMul(-1, rh, evaluate=False), evaluate=False)
        else:
            # If we want to force ordering for variables this should be:
            # return Sub(lh, rh, evaluate=False)
            if not rh.is_Matrix and rh.func.is_Number:
                rh = -rh
            else:
                rh = sympy.Mul(-1, rh, evaluate=False)
            return sympy.Add(lh, rh, evaluate=False)
    else:
        return convert_mp(add.mp())


def convert_mp(mp):
    if hasattr(mp, 'mp'):
        mp_left = mp.mp(0)
        mp_right = mp.mp(1)
    else:
        mp_left = mp.mp_nofunc(0)
        mp_right = mp.mp_nofunc(1)

    if mp.MUL() or mp.CMD_TIMES() or mp.CMD_CDOT():
        lh = convert_mp(mp_left)
        rh = convert_mp(mp_right)

        if lh.is_Matrix or rh.is_Matrix:
            return sympy.MatMul(lh, rh, evaluate=False)
        else:
            return sympy.Mul(lh, rh, evaluate=False)
    elif mp.DIV() or mp.CMD_DIV() or mp.COLON():
        lh = convert_mp(mp_left)
        rh = convert_mp(mp_right)
        if lh.is_Matrix or rh.is_Matrix:
            return sympy.MatMul(lh, sympy.Pow(rh, -1, evaluate=False), evaluate=False)
        else:
            return Div(lh, rh, in_parsing=True, evaluate=False)
    else:
        if hasattr(mp, 'unary'):
            return convert_unary(mp.unary())
        else:
            return convert_unary(mp.unary_nofunc())


def convert_unary(unary):
    if hasattr(unary, 'unary'):
        nested_unary = unary.unary()
    else:
        nested_unary = unary.unary_nofunc()
    if hasattr(unary, 'postfix_nofunc'):
        first = unary.postfix()
        tail = unary.postfix_nofunc()
        postfix = [first] + tail
    else:
        postfix = unary.postfix()

    if unary.ADD():
        return convert_unary(nested_unary)
    elif unary.SUB():
        tmp_convert_nested_unary = convert_unary(nested_unary)
        if tmp_convert_nested_unary.is_Matrix:
            return sympy.MatMul(-1, tmp_convert_nested_unary, evaluate=False)
        else:
            if tmp_convert_nested_unary.func.is_Number:
                return -tmp_convert_nested_unary
            else:
                return sympy.Mul(-1, tmp_convert_nested_unary, evaluate=False)
    elif postfix:
        return convert_postfix_list(postfix)

def convert_postfix_list(arr, i=0):
    if i >= len(arr):
        raise Exception("Index out of bounds")

    res = convert_postfix(arr[i])
    if isinstance(res, sympy.Expr) or isinstance(res, sympy.Matrix):
        if i == len(arr) - 1:
            return res # nothing to multiply by
        else:
            # multiply by next
            rh = convert_postfix_list(arr, i + 1)
            if res.is_Matrix or rh.is_Matrix:
                return sympy.MatMul(res, rh, evaluate=False)
            else:
                return sympy.Mul(res, rh, evaluate=False)
    else: # must be derivative
        wrt = res[0]
        if i == len(arr) - 1:
            raise Exception("Expected expression for derivative")
        else:
            expr = convert_postfix_list(arr, i + 1)
            return sympy.Derivative(expr, wrt)

def do_subs(expr, at):
    if at.expr():
        at_expr = convert_expr(at.expr())
        syms = at_expr.atoms(sympy.Symbol)
        if len(syms) == 0:
            return expr
        elif len(syms) > 0:
            sym = next(iter(syms))
            return expr.subs(sym, at_expr)
    elif at.equality():
        lh = convert_expr(at.equality().expr(0))
        rh = convert_expr(at.equality().expr(1))
        return expr.subs(lh, rh)

def convert_postfix(postfix):
    if hasattr(postfix, 'exp'):
        exp_nested = postfix.exp()
    else:
        exp_nested = postfix.exp_nofunc()

    exp = convert_exp(exp_nested)
    for op in postfix.postfix_op():
        if op.BANG():
            if isinstance(exp, list):
                raise Exception("Cannot apply postfix to derivative")
            exp = sympy.factorial(exp, evaluate=False)
        elif op.eval_at():
            ev = op.eval_at()
            at_b = None
            at_a = None
            if ev.eval_at_sup():
                at_b = do_subs(exp, ev.eval_at_sup())
            if ev.eval_at_sub():
                at_a = do_subs(exp, ev.eval_at_sub())
            if at_b != None and at_a != None:
                exp = Sub(at_b, at_a, evaluate=False)
            elif at_b != None:
                exp = at_b
            elif at_a != None:
                exp = at_a

    return exp

def convert_exp(exp):
    if hasattr(exp, 'exp'):
        exp_nested = exp.exp()
    else:
        exp_nested = exp.exp_nofunc()

    if exp_nested:
        base = convert_exp(exp_nested)
        if isinstance(base, list):
            raise Exception("Cannot raise derivative to power")
        if exp.atom():
            exponent = convert_atom(exp.atom())
        elif exp.expr():
            exponent = convert_expr(exp.expr())
        return sympy.Pow(base, exponent, evaluate=False)
    else:
        if hasattr(exp, 'comp'):
            return convert_comp(exp.comp())
        else:
            return convert_comp(exp.comp_nofunc())

def convert_comp(comp):
    if comp.group():
        return convert_expr(comp.group().expr())
    elif comp.abs_group():
        return sympy.Abs(convert_expr(comp.abs_group().expr()), evaluate=False)
    elif comp.atom():
        return convert_atom(comp.atom())
    elif comp.frac():
        return convert_frac(comp.frac())
    elif comp.binom():
        return convert_binom(comp.binom())
    elif comp.matrix():
        return convert_matrix(comp.matrix())
    elif comp.func():
        return convert_func(comp.func())

def convert_atom(atom):
    if atom.LETTER():
        subscriptName = ''
        s = atom.LETTER().getText()
        if s == "I":
            return sympy.I
        if atom.subexpr():
            subscript = None
            if atom.subexpr().expr():           # subscript is expr
                subscript = convert_expr(atom.subexpr().expr())
            else:                               # subscript is atom
                subscript = convert_atom(atom.subexpr().atom())
            subscriptName = '_{' + StrPrinter().doprint(subscript) + '}'
        return sympy.Symbol(atom.LETTER().getText() + subscriptName, real=True)
    elif atom.SYMBOL():
        s = atom.SYMBOL().getText()[1:]
        if s == "infty":
            return sympy.oo
        elif s == 'pi':
            return sympy.pi
        else:
            if atom.subexpr():
                subscript = None
                if atom.subexpr().expr():           # subscript is expr
                    subscript = convert_expr(atom.subexpr().expr())
                else:                               # subscript is atom
                    subscript = convert_atom(atom.subexpr().atom())
                subscriptName = StrPrinter().doprint(subscript)
                s += '_{' + subscriptName + '}'
            return sympy.Symbol(s, real=True)
    elif atom.accent():
        # get name for accent
        name = atom.accent().start.text[1:]
        # exception: check if bar or overline which are treated both as bar
        if name in ["bar", "overline"]:
            name = "bar"
        # get the base (variable)
        base = atom.accent().base.getText()
        # set string to base+name
        s = base+name
        if atom.subexpr():
            subscript = None
            if atom.subexpr().expr():           # subscript is expr
                subscript = convert_expr(atom.subexpr().expr())
            else:                               # subscript is atom
                subscript = convert_atom(atom.subexpr().atom())
            subscriptName = StrPrinter().doprint(subscript)
            s += '_{' + subscriptName + '}'
        return sympy.Symbol(s, real=True)
    elif atom.NUMBER():
        s = atom.NUMBER().getText().replace(",", "")
        try:
            sr = sympy.Rational(s)
            return sr
        except e:
            return sympy.Number(s)
    elif atom.DIFFERENTIAL():
        var = get_differential_var(atom.DIFFERENTIAL())
        return sympy.Symbol('d' + var.name, real=True)
    elif atom.mathit():
        text = rule2text(atom.mathit().mathit_text())
        return sympy.Symbol(text, real=True)
    elif atom.PLACEHOLDER():
        name = atom.PLACEHOLDER().getText()[2:]
        name = name[0:len(name)-2]

        # add hash to distinguish from regular symbols
        hash = hashlib.md5(name.encode()).hexdigest()
        symbol_name = name+hash

        # replace the placeholder for already known placeholder values
        if name in PLACEHOLDER_VALUES:
            # if a sympy class
            if isinstance(PLACEHOLDER_VALUES[name], tuple(sympy.core.all_classes)):
                symbol = PLACEHOLDER_VALUES[name]

            # if NOT a sympy class
            else:
                symbol = parse_expr(str(PLACEHOLDER_VALUES[name]))
        else:
            symbol = sympy.Symbol(symbol_name, real=True)

        # return the symbol
        return symbol

def rule2text(ctx):
    stream = ctx.start.getInputStream()
    # starting index of starting token
    startIdx = ctx.start.start
    # stopping index of stopping token
    stopIdx = ctx.stop.stop

    return stream.getText(startIdx, stopIdx)


def convert_frac(frac):
    diff_op = False
    partial_op = False
    lower_itv = frac.lower.getSourceInterval()
    lower_itv_len = lower_itv[1] - lower_itv[0] + 1
    if (frac.lower.start == frac.lower.stop and
        frac.lower.start.type == PSLexer.DIFFERENTIAL):
        wrt = get_differential_var_str(frac.lower.start.text)
        diff_op = True
    elif (lower_itv_len == 2 and
        frac.lower.start.type == PSLexer.SYMBOL and
        frac.lower.start.text == '\\partial' and
        (frac.lower.stop.type == PSLexer.LETTER or frac.lower.stop.type == PSLexer.SYMBOL)):
        partial_op = True
        wrt = frac.lower.stop.text
        if frac.lower.stop.type == PSLexer.SYMBOL:
            wrt = wrt[1:]

    if diff_op or partial_op:
        wrt = sympy.Symbol(wrt, real=True)
        if (diff_op and frac.upper.start == frac.upper.stop and
            frac.upper.start.type == PSLexer.LETTER and
            frac.upper.start.text == 'd'):
            return [wrt]
        elif (partial_op and frac.upper.start == frac.upper.stop and
            frac.upper.start.type == PSLexer.SYMBOL and
            frac.upper.start.text == '\\partial'):
            return [wrt]
        upper_text = rule2text(frac.upper)

        expr_top = None
        if diff_op and upper_text.startswith('d'):
            expr_top = process_sympy(upper_text[1:])
        elif partial_op and frac.upper.start.text == '\\partial':
            expr_top = process_sympy(upper_text[len('\\partial'):])
        if expr_top:
            return sympy.Derivative(expr_top, wrt)

    expr_top = convert_expr(frac.upper)
    expr_bot = convert_expr(frac.lower)
    if expr_top.is_Matrix or expr_bot.is_Matrix:
        return sympy.MatMul(expr_top, sympy.Pow(expr_bot, -1, evaluate=False), evaluate=False)
    else:
        return Div(expr_top, expr_bot, in_parsing=True, evaluate=False)


def convert_binom(binom):
    expr_top = convert_expr(binom.upper)
    expr_bot = convert_expr(binom.lower)
    return sympy.binomial(expr_top, expr_bot)


def convert_func(func):
    if func.func_normal():
        if func.L_PAREN(): # function called with parenthesis
            arg = convert_func_arg(func.func_arg())
        else:
            arg = convert_func_arg(func.func_arg_noparens())

        name = func.func_normal().start.text[1:]

        # change arc<trig> -> a<trig>
        if name in ["arcsin", "arccos", "arctan", "arccsc", "arcsec",
        "arccot"]:
            name = "a" + name[3:]
            expr = getattr(sympy.functions, name)(arg, evaluate=False)
        if name in ["arsinh", "arcosh", "artanh"]:
            name = "a" + name[2:]
            expr = getattr(sympy.functions, name)(arg, evaluate=False)
        if name in ["arcsinh", "arccosh", "arctanh"]:
            name = "a" + name[3:]
            expr = getattr(sympy.functions, name)(arg, evaluate=False)

        if name == "operatorname":
            operatorname = func.func_normal().func_operator_name.getText()
            if operatorname in ["arsinh", "arcosh", "artanh"]:
                operatorname = "a" + operatorname[2:]
                expr = getattr(sympy.functions, operatorname)(arg, evaluate=False)
            if operatorname in ["arcsinh", "arccosh", "arctanh"]:
                operatorname = "a" + operatorname[3:]
                expr = getattr(sympy.functions, operatorname)(arg, evaluate=False)

        if (name=="log" or name=="ln"):
            if func.subexpr():
                if func.subexpr().atom():
                    base = convert_atom(func.subexpr().atom())
                else:
                    base = convert_expr(func.subexpr().expr())
            elif name == "log":
                base = 10
            elif name == "ln":
                base = sympy.E
            expr = sympy.log(arg, base, evaluate=False)

        func_pow = None
        should_pow = True
        if func.supexpr():
            if func.supexpr().expr():
                func_pow = convert_expr(func.supexpr().expr())
            else:
                func_pow = convert_atom(func.supexpr().atom())

        if name in ["sin", "cos", "tan", "csc", "sec", "cot", "sinh", "cosh", "tanh"]:
                if func_pow == -1:
                    name = "a" + name
                    should_pow = False
                expr = getattr(sympy.functions, name)(arg, evaluate=False)


        if func_pow and should_pow:
            expr = sympy.Pow(expr, func_pow, evaluate=False)

        return expr
    # elif func.LETTER() or func.SYMBOL():
    #     print('LETTER or symbol')
    #     if func.LETTER():
    #         fname = func.LETTER().getText()
    #     elif func.SYMBOL():
    #         fname = func.SYMBOL().getText()[1:]
    #     fname = str(fname) # can't be unicode
    #     if func.subexpr():
    #         subscript = None
    #         if func.subexpr().expr():                   # subscript is expr
    #             subscript = convert_expr(func.subexpr().expr())
    #         else:                                       # subscript is atom
    #             subscript = convert_atom(func.subexpr().atom())
    #         subscriptName = StrPrinter().doprint(subscript)
    #         fname += '_{' + subscriptName + '}'
    #     input_args = func.args()
    #     output_args = []
    #     while input_args.args():                        # handle multiple arguments to function
    #         output_args.append(convert_expr(input_args.expr()))
    #         input_args = input_args.args()
    #     output_args.append(convert_expr(input_args.expr()))
    #     return sympy.Function(fname)(*output_args)
    elif func.FUNC_INT():
        return handle_integral(func)
    elif func.FUNC_SQRT():
        expr = convert_expr(func.base)
        if func.root:
            r = convert_expr(func.root)
            return Root(expr, 1 / r, evaluate=False)
        else:
            return Root(expr, sympy.S.Half, evaluate=False)
    elif func.FUNC_SUM():
        return handle_sum_or_prod(func, "summation")
    elif func.FUNC_PROD():
        return handle_sum_or_prod(func, "product")
    elif func.FUNC_LIM():
        return handle_limit(func)
    elif func.FUNC_EXP():
        return handle_exp(func)

def convert_func_arg(arg):
    if hasattr(arg, 'expr'):
        return convert_expr(arg.expr())
    else:
        return convert_mp(arg.mp_nofunc())

def handle_integral(func):
    if func.additive():
        integrand = convert_add(func.additive())
    elif func.frac():
        integrand = convert_frac(func.frac())
    else:
        integrand = 1

    int_var = None
    if func.DIFFERENTIAL():
        int_var = get_differential_var(func.DIFFERENTIAL())
    else:
        for sym in integrand.atoms(sympy.Symbol):
            s = str(sym)
            if len(s) > 1 and s[0] == 'd':
                if s[1] == '\\':
                    int_var = sympy.Symbol(s[2:], real=True)
                else:
                    int_var = sympy.Symbol(s[1:], real=True)
                int_sym = sym
        if int_var:
            if integrand.func == Div:
                integrand = sympy.Mul(*integrand.args, evaluate=False)

            integrand = integrand.subs(int_sym, 1)
        else:
            # Assume dx by default
            int_var = sympy.Symbol('x', real=True)

    if func.subexpr():
        if func.subexpr().atom():
            lower = convert_atom(func.subexpr().atom())
        else:
            lower = convert_expr(func.subexpr().expr())
        if func.supexpr().atom():
            upper = convert_atom(func.supexpr().atom())
        else:
            upper = convert_expr(func.supexpr().expr())
        return sympy.Integral(integrand, (int_var, lower, upper))
    else:
        return sympy.Integral(integrand, int_var)

def handle_sum_or_prod(func, name):
    val      = convert_mp(func.mp())
    iter_var = convert_expr(func.subeq().equality().expr(0))
    start    = convert_expr(func.subeq().equality().expr(1))
    if func.supexpr().expr(): # ^{expr}
        end = convert_expr(func.supexpr().expr())
    else: # ^atom
        end = convert_atom(func.supexpr().atom())


    if name == "summation":
        return sympy.Sum(val, (iter_var, start, end))
    elif name == "product":
        return sympy.Product(val, (iter_var, start, end))

def handle_limit(func):
    sub = func.limit_sub()
    if sub.LETTER():
        var = sympy.Symbol(sub.LETTER().getText(), real=True)
    elif sub.SYMBOL():
        var = sympy.Symbol(sub.SYMBOL().getText()[1:], real=True)
    else:
        var = sympy.Symbol('x', real=True)
    if sub.SUB():
        direction = "-"
    else:
        direction = "+"
    approaching = convert_expr(sub.expr())
    content     = convert_mp(func.mp())

    return sympy.Limit(content, var, approaching, direction)

def handle_exp(func):
    if func.supexpr():
        if func.supexpr().expr(): # ^{expr}
            exp_arg = convert_expr(func.supexpr().expr())
        else: # ^atom
            exp_arg = convert_atom(func.supexpr().atom())
    else:
        exp_arg = 1
    return sympy.exp(exp_arg)

def get_differential_var(d):
    text = get_differential_var_str(d.getText())
    return sympy.Symbol(text, real=True)

def get_differential_var_str(text):
    for i in range(1, len(text)):
        c = text[i]
        if not (c == " " or c == "\r" or c == "\n" or c == "\t"):
            idx = i
            break
    text = text[idx:]
    if text[0] == "\\":
        text = text[1:]
    return text


class Div(sympy.Mul):

    def __new__(cls, *args, in_parsing=False, **options):
        if in_parsing:
            args = (args[0], sympy.Pow(args[1], -1, evaluate=False))
        return super().__new__(Div, *args, **options)

    def _sympyrepr(self, expr, order=None):
        return "Div(%s)" % ",".join(map(sympy.srepr, self.args))


class Root(sympy.Pow):

    def __new__(cls, *args, **options):
        return super().__new__(Root, *args, **options)

    def _sympyrepr(self, expr, order=None):
        return "Root(%s)" % ",".join(map(sympy.srepr, self.args))


class Sub(sympy.Add):

    def __new__(cls, *args, in_parsing=False, **options):
        if in_parsing:
            args = (args[0], sympy.Mul(-1, args[1], evaluate=False))
        return super().__new__(Sub, *args, **options)

    def _sympyrepr(self, expr, order=None):
        return "Sub(%s)" % ",".join(map(sympy.srepr, self.args))


def test_sympy():
    print(process_sympy("e^{(45 + 2)}"))
    print(process_sympy("e + 5"))
    print(process_sympy("5 + e"))
    print(process_sympy("e"))
    print(process_sympy("\\frac{dx}{dy} \\int y x^2 dy"))
    print(process_sympy("\\frac{dx}{dy} 5"))
    print(process_sympy("\\frac{d}{dx} \\int x^2 dx"))
    print(process_sympy("\\frac{dx}{dy} \\int x^2 dx"))
    print(process_sympy("\\frac{d}{dy} x^2 + x y = 0"))
    print(process_sympy("\\frac{d}{dy} x^2 + x y = 2"))
    print(process_sympy("\\frac{d x^3}{dy}"))
    print(process_sympy("\\frac{d x^3}{dy} + x^3"))
    print(process_sympy("\\int^{5x}_{2} x^2 dy"))
    print(process_sympy("\\int_{5x}^{2} x^2 dx"))
    print(process_sympy("\\int x^2 dx"))
    print(process_sympy("2 4 5 - 2 3 1"))

if __name__ == "__main__":
    test_sympy()
