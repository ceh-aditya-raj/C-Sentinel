"""
src/core/parser_ast.py

Phase 4 - PLY-based Parser + AST (C99 subset)

- Consumes cleaned code string (from preprocess_c.py)
- Uses tokens defined in src/core/lexer_c.py (PLY)
- Produces an AST root (Program) suitable for CFG construction
- Logging + graceful error handling
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from .ast_printer import print_ast

from pathlib import Path
import logging
import traceback
from typing import List, Optional, Any
import sys
import ply.lex as lex
import ply.yacc as yacc

# import lexer module - uses the tokens list and token regexes defined there
from analyzer_core.core import lexer_c as lexer_module

# Ensure logs go to project-root/logs/sentinel.log
def ensure_logging():
    project_root = Path(__file__).resolve().parents[2]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "sentinel.log"
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )

ensure_logging()
logger = logging.getLogger("c_sentinel.phase4")

# AST Node Classes (simple, extendable)

class Node:
    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"
    def get_pos(self):
        """Return (lineno, lexpos) if stored, else (None, None)."""
        pos = getattr(self, "pos", None)
        if pos is None:
            return (None, None)
        return pos


class Program(Node):
    def __init__(self, external_declarations: List[Any]):
        self.external_declarations = external_declarations

class Include(Node):
    def __init__(self, text: str):
        self.text = text

class FunctionDef(Node):
    def __init__(self, return_type, name, params, body):
        self.return_type = return_type
        self.name = name
        self.params = params or []
        self.body = body

class Declaration(Node):
    def __init__(self, decl_type, declarators: List[Any], initializer=None, pos=None):
        self.decl_type = decl_type
        self.declarators = declarators  # list of (name, type_modifier)
        self.initializer = initializer
        self.pos = pos

class VarDeclarator(Node):
    def __init__(self, name, declarator_type=None, initializer=None, pos=None):
        self.name = name
        self.declarator_type = declarator_type  # e.g., pointer, array(size)
        self.initializer = initializer
        self.pos = pos

class Compound(Node):
    def __init__(self, items: List[Any]):
        self.items = items  # list of statements / declarations

class Return(Node):
    def __init__(self, expr):
        self.expr = expr

class Break(Node):
    pass

class ExprStmt(Node):
    def __init__(self, expr):
        self.expr = expr

class IfStmt(Node):
    def __init__(self, cond, then_stmt, else_stmt=None):
        self.cond = cond
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

class WhileStmt(Node):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

class ForStmt(Node):
    def __init__(self, init, cond, post, body):
        self.init = init
        self.cond = cond
        self.post = post
        self.body = body

class SwitchStmt(Node):
    def __init__(self, expr, body):
        self.expr = expr
        self.body = body

class CaseStmt(Node):
    def __init__(self, value, statement):
        self.value = value
        self.statement = statement

class DefaultStmt(Node):
    def __init__(self, statement):
        self.statement = statement

class Call(Node):
    def __init__(self, func, args):
        self.func = func
        self.args = args

class Identifier(Node):
    def __init__(self, name):
        self.name = name

class Constant(Node):
    def __init__(self, value, ctype="int"):
        self.value = value
        self.ctype = ctype

class BinaryOp(Node):
    def __init__(self, op, left, right, pos=None):
        self.op = op
        self.left = left
        self.right = right
        self.pos=pos

class UnaryOp(Node):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

class PointerDecl(Node):
    def __init__(self, pos=None, level=1):
        self.pos = pos
        self.level = level

class ArrayDecl(Node):
    def __init__(self, size=None):
        self.size = size
        
# ----------------- New AST node types (postfix & member access) -----------------
class ArrayRef(Node):
    """Represents array indexing: base[index]"""
    def __init__(self, base, index, pos=None):
        self.base = base
        self.index = index
        self.pos = pos

class MemberAccess(Node):
    """Represents struct/union member access: base.member"""
    def __init__(self, base, member, pos=None):
        # member will be an Identifier node for consistency
        self.base = base
        self.member = member if isinstance(member, Identifier) else Identifier(member)
        self.pos = pos

class PointerMemberAccess(Node):
    """Represents pointer member access: base->member"""
    def __init__(self, base, member, pos=None):
        self.base = base
        self.member = member if isinstance(member, Identifier) else Identifier(member)
        self.pos = pos
        
class PosMixin:
    def get_pos(self):
        return getattr(self, "pos", (0,0))
    
# --- AST node: Cast (insert near other AST node classes) ---
class Cast:
    def __init__(self, to_type, expr, pos=None):
        # to_type: a simple string (type_specifier) or more complex node if you extend types later
        self.to_type = to_type
        self.expr = expr
        self.pos = pos

    def get_pos(self):
        return self.pos

    def __repr__(self):
        return f"Cast(to_type={self.to_type}, expr={self.expr})"
    
class TernaryOp:
    def __init__(self, condition, true_expr, false_expr, pos=None):
        self.condition = condition
        self.true_expr = true_expr
        self.false_expr = false_expr
        self.pos = pos

    def get_pos(self):
        return self.pos

    def __repr__(self):
        return f"TernaryOp(cond={self.condition}, true={self.true_expr}, false={self.false_expr})"
    
class StructSpecifier:
    def __init__(self, name, fields, pos=None):
        self.name = name
        self.fields = fields or []
        self.pos = pos

    def get_pos(self):
        return self.pos

class StructField:
    def __init__(self, type_spec, declarators, pos=None):
        self.type_spec = type_spec
        self.declarators = declarators
        self.pos = pos

    def get_pos(self):
        return self.pos




# ---------------------Parser tokens (taken from lexer module)------------------------------
 
import importlib

# import lexer safely
try:
    lexer_module = importlib.import_module("core.lexer_c")
except ImportError:
    lexer_module = importlib.import_module("analyzer_core.core.lexer_c")

# build tokens list safely
_extra_tokens = ["DEREF", "ADDRESS", "TYPEDEF"]

tokens_list = list(getattr(lexer_module, "tokens", []))
for t in _extra_tokens:
    if t not in tokens_list:
        tokens_list.append(t)

tokens = tuple(tokens_list)
lexer = getattr(lexer_module, "lexer", None)

# --- begin precedence patch (keep names even if they are not tokens) ---
_PRECEDENCE_RAW = [
    ("left", ["OR"]),
    ("left", ["AND"]),
    ("left", ["EQ", "NEQ"]),
    ("left", ["LT", "GT", "LE", "GE"]),
    ("left", ["LSHIFT", "RSHIFT"]),
    ("left", ["PLUS", "MINUS"]),
    ("left", ["TIMES", "DIVIDE", "MOD"]),
    ("right", ["UMINUS", "UPLUS"]),  # precedence names used via %prec
]


precedence = tuple((assoc,) + tuple(names) for (assoc, names) in _PRECEDENCE_RAW)
# --- end precedence patch ---

# ---------- Position helpers (paste near top, after tokens are defined) ----------
def tokpos(tok):
    """
    Return a (lineno, lexpos) tuple for tok, tolerant to:
      - PLY LexToken (has lineno, lexpos),
      - p.slice entries (YaccSymbol) (may carry .type/.value),
      - AST nodes that already have .pos,
      - tuples that are already (lineno, lexpos).
    If nothing found, return (0, 0).
    """
    if tok is None:
        return (0, 0)

    # Direct LexToken (the usual case from the lexer)
    if hasattr(tok, "lineno") and hasattr(tok, "lexpos"):
        try:
            return (int(getattr(tok, "lineno", 0)), int(getattr(tok, "lexpos", 0)))
        except Exception:
            return (0, 0)

    # If tok is a YaccSymbol from p.slice: try tok.value, then attributes
    if hasattr(tok, "value"):
        v = tok.value
        # If value itself is an AST node with .pos
        if hasattr(v, "pos"):
            return v.pos
        # If value is a LexToken (in some configurations)
        if hasattr(v, "lineno") and hasattr(v, "lexpos"):
            try:
                return (int(getattr(v, "lineno", 0)), int(getattr(v, "lexpos", 0)))
            except Exception:
                return (0, 0)

    # If this is an AST node with .pos attribute
    if hasattr(tok, "pos"):
        pos = getattr(tok, "pos")
        if isinstance(pos, tuple) and len(pos) == 2:
            return pos
        # sometimes pos stored as two ints in list/tuple-like
        try:
            return (int(pos[0]), int(pos[1]))
        except Exception:
            pass

    # Already a (lineno, lexpos) tuple
    if isinstance(tok, tuple) and len(tok) == 2 and all(isinstance(i, int) for i in tok):
        return tok

    # Last-chance: try numeric attributes often present
    lineno = getattr(tok, "lineno", None) or getattr(tok, "lineno", None)
    lexpos = getattr(tok, "lexpos", None) or getattr(tok, "lexpos", None)
    if lineno is not None and lexpos is not None:
        try:
            return (int(lineno), int(lexpos))
        except Exception:
            pass

    return (0, 0)


# Robust position helper — replace older get_pos/tokpos variants with this
def get_pos(p, index):
    """
    Safe position getter for yacc rule p and index.
    Returns a (lineno, lexpos) pair when available, or attempts to extract .pos
    from AST nodes or token.value. Returns None if unavailable.
    """
    # protect against bad indexes
    if index is None:
        return None
    try:
        tok = p.slice[index]
    except Exception:
        return None

    # If it's a lex token with lineno/lexpos
    if hasattr(tok, "lineno"):
        lineno = getattr(tok, "lineno", None)
        lexpos = getattr(tok, "lexpos", None)
        return (lineno, lexpos)

    # If tok has .value which is an AST node with .pos
    if hasattr(tok, "value"):
        val = tok.value
        if hasattr(val, "pos"):
            return val.pos
        # sometimes value is a tuple (e.g. (IDENT, 'name'))
        if isinstance(val, tuple) and len(val) > 0 and hasattr(val[0], "pos"):
            return val[0].pos

    # If tok itself is an AST node
    if hasattr(tok, "pos"):
        return tok.pos

    return None

# ---------- end position helpers ----------

def normalize_type_spec(t):
    if isinstance(t, list):
        return " ".join(str(x) for x in t)
    return t

def normalize_type_name(t):
    if isinstance(t, tuple):
        base, ptr_level = t
        stars = "*" * int(ptr_level)
        return f"{base} {stars}".strip()
    return normalize_type_spec(t)



# --------------------Grammar rules---------------------------
def p_program(p):
    """program : external_list"""
    # external_list is already a Python list of declaration nodes
    p[0] = Program(external_declarations=p[1])

    
def p_empty(p):
    "empty :"
    p[0] = None

def p_external_list(p):
    """external_list : external_list external_declaration
                     | external_declaration"""
    if len(p) == 3:
        # p[1] is a list, p[2] is a node -> concatenate
        p[0] = p[1] + [p[2]]
    else:
        # single element list
        p[0] = [p[1]]



def p_external_declaration(p):
    """external_declaration : function_definition
                            | declaration
                            | include_directive
                            | PP_DIRECTIVE
                            | typedef_declaration
    """
    if isinstance(p[1], str):
        p[0] = Include(p[1])
    else:
        p[0] = p[1]

def p_typedef_declaration(p):
    """typedef_declaration : TYPEDEF declaration"""

    p[0] = p[2]
    


def p_header_name(p):
    """header_name : IDENTIFIER
                   | IDENTIFIER DOT IDENTIFIER"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = f"{p[1]}.{p[3]}"


def p_include_directive(p):
    """include_directive : PP_DIRECTIVE"""
    p[0] = Include(p[1])   # ← Wrap into AST node



# ---------- Declarations ----------
def p_declaration(p):
    """declaration : type_specifier_seq init_declarator_list SEMICOLON"""
    decl_type = normalize_type_spec(p[1])
    declarators = p[2]
    p[0] = Declaration(decl_type, declarators)

def p_init_declarator_list(p):
    """init_declarator_list : init_declarator_list COMMA init_declarator
                            | init_declarator"""
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_init_declarator(p):
    """init_declarator : declarator
                       | declarator ASSIGN initializer"""
    if len(p) == 2:
        p[0] = p[1]
        p[0].pos = tokpos(p.slice[1])
    else:
        decl = p[1]
        decl.pos = tokpos(p.slice[1])
        decl.initializer = p[3]
        p[0] = decl

def p_declarator(p):
    """declarator : direct_declarator
                  | pointer direct_declarator"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # pointer declaration
        name = p[2].name
        pointer_level = p[1] if isinstance(p[1], int) else 1
        decl = VarDeclarator(name, declarator_type=PointerDecl(level=pointer_level))
        decl.pos = tokpos(p.slice[2])
        p[0] = decl

def p_pointer(p):
    """pointer : TIMES
               | TIMES pointer"""
    if len(p) == 2:
        p[0] = 1
    else:
        p[0] = 1 + p[2]

def p_direct_declarator(p):
    """direct_declarator : IDENTIFIER
                         | IDENTIFIER LBRACKET INT_CONST RBRACKET
                         | IDENTIFIER LBRACKET IDENTIFIER RBRACKET
                         | IDENTIFIER LBRACKET RBRACKET"""
    if len(p) == 2:
        p[0] = VarDeclarator(p[1])
        p[0].pos = tokpos(p.slice[1])
    elif len(p) == 4:
        p[0] = VarDeclarator(p[1], declarator_type=ArrayDecl(size=None))
        p[0].pos = tokpos(p.slice[1])
    else:
        p[0] = VarDeclarator(p[1], declarator_type=ArrayDecl(size=p[3]))
        p[0].pos = tokpos(p.slice[1])

def p_initializer(p):
    """initializer : assignment_expression"""
    p[0] = p[1]
    
# ---------- Struct support----------
def p_struct_specifier(p):
    """struct_specifier : STRUCT IDENTIFIER LBRACE struct_declaration_list RBRACE
                        | STRUCT LBRACE struct_declaration_list RBRACE
                        | STRUCT IDENTIFIER"""
    if len(p) == 3:
        # struct X (no definition)
        p[0] = StructSpecifier(p[2], None, pos=get_pos(p,1))
    elif len(p) == 6:
        # struct X { ... }
        p[0] = StructSpecifier(p[2], p[4], pos=get_pos(p,1))
    else:
        # struct { ... } (anonymous) -> len(p) == 5
        p[0] = StructSpecifier(None, p[3], pos=get_pos(p,1))

def p_struct_declaration_list(p):
    """struct_declaration_list : struct_declaration_list struct_declaration
                               | struct_declaration"""
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_struct_declaration(p):
    """struct_declaration : type_specifier_seq init_declarator_list SEMICOLON"""
    p[0] = StructField(normalize_type_spec(p[1]), p[2], pos=get_pos(p,2))

def p_specifier_qualifier_list(p):
    """specifier_qualifier_list : type_specifier_seq
                                | type_specifier_seq specifier_qualifier_list"""
    # simplest behaviour: return a type_specifier or a composed list
    if len(p) == 2:
        p[0] = p[1]
    else:
        # return list to indicate qualifiers + type
        if isinstance(p[2], list):
            p[0] = [p[1]] + p[2]
        else:
            p[0] = [p[1], p[2]]

def p_type_specifier_seq(p):
    """type_specifier_seq : type_specifier_seq type_specifier
                          | type_specifier"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        left = p[1] if isinstance(p[1], list) else [p[1]]
        p[0] = left + [p[2]]

def p_type_name(p):
    """type_name : type_specifier_seq
                 | type_specifier_seq pointer"""
    if len(p) == 2:
        p[0] = normalize_type_spec(p[1])
    else:
        p[0] = (normalize_type_spec(p[1]), p[2])

# ---------- end struct support ----------
def p_type_specifier(p):
    """type_specifier : INT
                      | CHAR
                      | VOID
                      | FLOAT
                      | DOUBLE
                      | SHORT
                      | LONG
                      | SIGNED
                      | UNSIGNED
                      | BOOL
                      | CONST
                      | struct_specifier
                      | IDENTIFIER"""
    p[0] = p[1]
        
# ---------- Function definition ----------
def p_function_definition(p):
    """function_definition : type_specifier_seq IDENTIFIER LPAREN parameter_list RPAREN compound_statement
                           | type_specifier_seq IDENTIFIER LPAREN RPAREN compound_statement"""
    if len(p) == 7:
        params = p[4]
        body = p[6]
        p[0] = FunctionDef(normalize_type_spec(p[1]), p[2], params, body)
    else:
        body = p[5]
        p[0] = FunctionDef(normalize_type_spec(p[1]), p[2], [], body)

def p_parameter_list(p):
    """parameter_list : parameter_list COMMA parameter_declaration
                      | parameter_declaration"""
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_parameter_declaration(p):
    """parameter_declaration : type_specifier_seq declarator
                             | type_specifier_seq"""
    if len(p) == 3:
        p[0] = VarDeclarator(p[2].name, declarator_type=p[2].declarator_type)
    else:
        p[0] = VarDeclarator(None)

# ---------- Statements ----------
def p_compound_statement(p):
    """compound_statement : LBRACE statement_list RBRACE
                          | LBRACE RBRACE"""
    if len(p) == 4:
        p[0] = Compound(p[2])
    else:
        p[0] = Compound([])

def p_statement_list(p):
    """statement_list : statement_list statement
                      | statement"""
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_statement(p):
    """statement : expression_statement
                 | compound_statement
                 | selection_statement
                 | iteration_statement
                 | jump_statement
                 | declaration
                 | labeled_statement"""
    p[0] = p[1]

def p_labeled_statement(p):
    """labeled_statement : CASE constant_expression COLON statement
                         | DEFAULT COLON statement"""
    if len(p) == 5:
        p[0] = CaseStmt(p[2], p[4])
    else:
        p[0] = DefaultStmt(p[3])

def p_expression_statement(p):
    """expression_statement : expression SEMICOLON
                            | SEMICOLON"""
    if len(p) == 3:
        p[0] = ExprStmt(p[1])
    else:
        p[0] = ExprStmt(None)

def p_selection_statement(p):
    """selection_statement : IF LPAREN expression RPAREN statement
                           | IF LPAREN expression RPAREN statement ELSE statement
                           | SWITCH LPAREN expression RPAREN statement"""
    if len(p) == 6:
        if p[1] == 'if':
            p[0] = IfStmt(p[3], p[5], None)
        else:
            p[0] = SwitchStmt(p[3], p[5])
    else:
        p[0] = IfStmt(p[3], p[5], p[7])

def p_iteration_statement(p):
    """iteration_statement : WHILE LPAREN expression RPAREN statement
                           | FOR LPAREN expression_statement expression_statement expression RPAREN statement
                           | FOR LPAREN declaration expression_statement expression RPAREN statement
                           | FOR LPAREN expression_statement expression_statement RPAREN statement
                           | FOR LPAREN declaration expression_statement RPAREN statement"""
    if p[1] == 'while':
        p[0] = WhileStmt(p[3], p[5])
    elif len(p) == 8:
        p[0] = ForStmt(p[3], p[4], p[5], p[7])
    else:
        p[0] = ForStmt(p[3], p[4], None, p[6])

def p_jump_statement(p):
    """jump_statement : RETURN expression SEMICOLON
                      | RETURN SEMICOLON
                      | BREAK SEMICOLON"""
    if len(p) == 4:
        p[0] = Return(p[2])
    elif p[1] == 'break':
        p[0] = Break()
    else:
        p[0] = Return(None)

# ---------- Expressions ----------
def p_expression(p):
    """expression : assignment_expression
                  | expression COMMA assignment_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # represent comma as right-associative sequence -> keep last expression
        p[0] = p[3]
        
def p_assignment_expression(p):
    """
    assignment_expression : conditional_expression
                          | unary_expression assignment_operator assignment_expression
    """
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = BinaryOp(op='=', left=p[1], right=p[3], pos=get_pos(p, 2))
        p[0].op = p[2]

def p_assignment_operator(p):
    """assignment_operator : ASSIGN
                           | PLUS_ASSIGN
                           | MINUS_ASSIGN
                           | MUL_ASSIGN
                           | DIV_ASSIGN
                           | MOD_ASSIGN
                           | LSHIFT_ASSIGN
                           | RSHIFT_ASSIGN"""
    p[0] = p[1]

        
def p_constant_expression(p):
    """constant_expression : assignment_expression"""
    p[0] = p[1]

def p_logical_or_expression(p):
    """logical_or_expression : logical_or_expression OR logical_and_expression
                             | logical_and_expression"""
    if len(p) == 4:
        p[0] = BinaryOp('||', p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_logical_and_expression(p):
    """logical_and_expression : logical_and_expression AND bitwise_or_expression
                              | bitwise_or_expression"""
    if len(p) == 4:
        p[0] = BinaryOp('&&', p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_bitwise_or_expression(p):
    """bitwise_or_expression : bitwise_or_expression BOR bitwise_xor_expression
                             | bitwise_xor_expression"""
    if len(p) == 4:
        p[0] = BinaryOp('|', p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_bitwise_xor_expression(p):
    """bitwise_xor_expression : bitwise_xor_expression BXOR bitwise_and_expression
                              | bitwise_and_expression"""
    if len(p) == 4:
        p[0] = BinaryOp('^', p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_bitwise_and_expression(p):
    """bitwise_and_expression : bitwise_and_expression BAND equality_expression
                              | equality_expression"""
    if len(p) == 4:
        p[0] = BinaryOp('&', p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_equality_expression(p):
    """equality_expression : equality_expression EQ relational_expression
                           | equality_expression NEQ relational_expression
                           | relational_expression"""
    if len(p) == 4:
        p[0] = BinaryOp(p[2], p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_relational_expression(p):
    """relational_expression : relational_expression LT shift_expression
                             | relational_expression GT shift_expression
                             | relational_expression LE shift_expression
                             | relational_expression GE shift_expression
                             | shift_expression"""
    if len(p) == 4:
        p[0] = BinaryOp(p[2], p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_shift_expression(p):
    """shift_expression : shift_expression LSHIFT additive_expression
                        | shift_expression RSHIFT additive_expression
                        | additive_expression"""
    if len(p) == 4:
        p[0] = BinaryOp(p[2], p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_additive_expression(p):
    """additive_expression : additive_expression PLUS multiplicative_expression
                           | additive_expression MINUS multiplicative_expression
                           | multiplicative_expression"""
    if len(p) == 4:
        p[0] = BinaryOp(p[2], p[1], p[3])
        get_pos(p, 2)
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()

def p_multiplicative_expression(p):
    """multiplicative_expression : multiplicative_expression TIMES unary_expression
                                 | multiplicative_expression DIVIDE unary_expression
                                 | multiplicative_expression MOD unary_expression
                                 | unary_expression"""
    if len(p) == 4:
        p[0] = BinaryOp(p[2], p[1], p[3])
        get_pos(p, 2)   # operator position
    else:
        p[0] = p[1]
        p[0].pos = p[1].get_pos()       # safe fallback (no operator)

def p_cast_expression(p):
    """
    cast_expression : LPAREN type_name RPAREN cast_expression
                    | postfix_expression
    """
    if len(p) == 2:
        # postfix_expression -> fallback
        p[0] = p[1]
        # keep position if available
        if hasattr(p[1], 'get_pos'):
            p[0].pos = p[1].get_pos()
    else:
        # ( type ) cast_expression  => build Cast node
        to_type = normalize_type_name(p[2])
        expr = p[4]
        p[0] = Cast(to_type, expr, pos=get_pos(p, 1))


def p_unary_expression(p):
    """unary_expression : postfix_expression
                        | PLUS unary_expression %prec UPLUS
                        | MINUS unary_expression %prec UMINUS
                        | NOT unary_expression
                        | BAND unary_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = UnaryOp(p[1], p[2])
        get_pos(p, 2)
        
def p_unary_expression_sizeof(p):
    """unary_expression : SIZEOF LPAREN expression RPAREN
                        | SIZEOF LPAREN type_name RPAREN"""
    p[0] = UnaryOp('sizeof', p[3])
    p[0].pos = tokpos(p.slice[1])
    
def p_unary_expression_cast(p):
    """unary_expression : LPAREN type_name RPAREN unary_expression"""
    p[0] = Cast(normalize_type_name(p[2]), p[4])
    p[0].pos = tokpos(p.slice[1])

def p_conditional_expression(p):
    """conditional_expression : logical_or_expression QUESTION expression COLON conditional_expression
                              | logical_or_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = TernaryOp(
            condition=p[1],
            true_expr=p[3],
            false_expr=p[5],
            pos=get_pos(p, 2)
        )

def p_postfix_expression(p):
    r"""
    postfix_expression : primary_expression
                       | postfix_expression LBRACKET expression RBRACKET
                       | postfix_expression LPAREN argument_expression_list RPAREN
                       | postfix_expression LPAREN RPAREN
                       | postfix_expression DOT IDENTIFIER
                       | postfix_expression ARROW IDENTIFIER
                       | postfix_expression INC
                       | postfix_expression DEC
    """
    # primary
    if len(p) == 2:
        p[0] = p[1]
        return

    # array indexing: base [ index ]
    if len(p) == 5 and p[2] == '[':
        base = p[1]
        index = p[3]
        p[0] = ArrayRef(base, index)
        get_pos(p, 2)
        return

    # function call without args: base ( )
    if len(p) == 4 and p[2] == '(' and p[3] == ')':
        func = p[1]
        p[0] = Call(func, [])
        get_pos(p, 2)
        return

    # function call with args: base ( arglist )
    if len(p) == 5 and p[2] == '(':
        func = p[1]
        args = p[3]
        # ensure args is a flat list
        if not isinstance(args, list):
            args = [args]
        p[0] = Call(func, args)
        get_pos(p, 2)
        return

    # member access: dot
    if len(p) == 4 and p[2] == '.':
        base = p[1]
        member_lexeme = p[3]
        p[0] = MemberAccess(base, member_lexeme)
        get_pos(p, 2)
        return

    # pointer member access: arrow
    if len(p) == 4 and p[2] == '->':
        base = p[1]
        member_lexeme = p[3]
        p[0] = PointerMemberAccess(base, member_lexeme)
        get_pos(p, 2)
        return

    # postfix ++ / --
    if len(p) == 3 and p[2] == '++':
        p[0] = UnaryOp('POSTINC', p[1])
        get_pos(p, 2)
        return
    if len(p) == 3 and p[2] == '--':
        p[0] = UnaryOp('POSTDEC', p[1])
        get_pos(p, 2)
        return

    # fallback
    p[0] = p[1]

def p_primary_expression(p):
    """primary_expression : IDENTIFIER
                          | INT_CONST
                          | FLOAT_CONST
                          | STRING_LITERAL
                          | CHAR_CONST
                          | LPAREN expression RPAREN"""
    tok = p.slice[1]
    val = tok.value
    ttype = tok.type

    if ttype == 'IDENTIFIER':
        p[0] = Identifier(val)
        p[0].pos = tokpos(tok)
    elif ttype == 'INT_CONST':
        p[0] = Constant(val, ctype='int')
        p[0].pos = tokpos(tok)
    elif ttype == 'FLOAT_CONST':
        p[0] = Constant(val, ctype='float')
        p[0].pos = tokpos(tok)
    elif ttype == 'STRING_LITERAL':
        p[0] = Constant(val, ctype='string')
        p[0].pos = tokpos(tok)
    elif ttype == 'CHAR_CONST':
        p[0] = Constant(val, ctype='char')
        p[0].pos = tokpos(tok)
    else:
        # parenthesized expressions
        p[0] = p[2]
        p[0].pos = tokpos(tok)


def p_argument_expression_list(p):
    """argument_expression_list : argument_expression_list COMMA assignment_expression
                                | assignment_expression"""
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

# Error handling

def p_error(p):
    if p:
        msg = f"Syntax error at token {p.type} (value={p.value!r}) line={p.lineno}"
        logger.error("Phase 4: " + msg)
        # try to recover: skip the token
        p.lexer.skip(1)
    else:
        logger.error("Phase 4: Syntax error at EOF")

# Build parser
parser = yacc.yacc()

# Public API: parse_code() and parse_file()
def parse_code(code: str) -> Program:
    """
    Parse cleaned code string and return Program AST root.
    """
    logger.info("Phase 4: parse_code started")
    try:
        # Build fresh lexer instance from lexer_module definitions
        lexer = lex.lex(module=lexer_module, reflags=0) 
        parser.errorok = True
        result = parser.parse(code, lexer=lexer)
        logger.info("Phase 4: parse_code finished")
        return result
    except Exception as e:
        logger.error("Phase 4: parse_code failed: %s", e)
        logger.debug(traceback.format_exc())
        raise

def parse_file(path: str) -> Program:
    p = Path(path)
    if not p.exists():
        msg = f"Phase 4: parse_file - file not found: {path}"
        logger.error(msg)
        raise FileNotFoundError(msg)
    code = p.read_text(encoding='utf-8', errors='replace')
    return parse_code(code)
