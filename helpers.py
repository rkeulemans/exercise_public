from sympy import Rational, Symbol, latex, UnevaluatedExpr
import sympy as sp
import numpy as np

u = lambda x : UnevaluatedExpr(x)

# Helper functions
def explain_add(a, b):
    assert(np.shape(a) == np.shape(b))
    rows, columns = np.shape(a)
    return sp.Matrix([[Symbol(f"({latex(u(a[i,j]))} + {latex(u(b[i,j]))})") for j in range(columns)] for i in range(rows)])

def symbolic_matrix(character, rows, columns):
    # row or column vector
    if rows == 1:
        return sp.Matrix([[Symbol(f"{{{character}}}_{{{j+1}}}") for j in range(columns)] for i in range(rows)]) 
    if columns == 1:
        return sp.Matrix([[Symbol(f"{{{character}}}_{{{i+1}}}") for j in range(columns)] for i in range(rows)]) 
    return sp.Matrix([[Symbol(f"{{{character}}}_{{{i+1}, {j+1}}}") for j in range(columns)] for i in range(rows)])

def explain_multiply(a, b):
    # #rows in b == #columns in a
    assert(np.shape(a)[1] == np.shape(b)[0])
    rows = np.shape(a)[0]
    columns = np.shape(b)[1]
    result = np.empty(shape=(rows, columns), dtype=object)
    for i in range(rows):
        row = a[i,:]
        for j in range(columns):
            column = b[:,j]
            zipped = zip(row, column)
            mapped = list(map(lambda t: f"{latex(u(t[0]))} \cdot {latex(u(t[1]))}", zipped))
            s = Symbol("") 
            result[i, j] = Symbol(" + ".join(mapped), evaluate=False)
                
    return sp.Matrix(result)