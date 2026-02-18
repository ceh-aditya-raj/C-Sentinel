"""
Phase 3 - PLY-based Lexer (C99-level)

- Input: cleaned C code string (from preprocess_file)
- Output: list of Token objects: Token(type, value, line, column)
- Uses PLY (lex) for tokenization
- Full logging to project-root/logs/sentinel.log
- Robust numeric literal support (decimal, hex, octal, binary, floats with exponent, suffixes)
- String/char literal handling (with escapes)
- Keywords mapped to token types
"""

import logging
import traceback
from pathlib import Path
from typing import List, Tuple, NamedTuple, Optional
import ply.lex as lex
import re

#-----LOGGING------
def ensure_logging():
    project_root = Path(__file__).resolve().parents[2]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents = True, exist_ok = True)
    log_file = logs_dir / "sentinel.log"
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )

ensure_logging()
logger = logging.getLogger("c_sentinel.phase3")

#------TOKEN OBJECT------
class TokenObj(NamedTuple):
    type: str
    value: str
    line: int
    column: int
    end_line: int
    end_column: int

#------RESERVED KEYWORD------
_reserved = {
    'auto': 'AUTO', 'break': 'BREAK', 'case': 'CASE', 'char': 'CHAR', 'const': 'CONST',
    'continue': 'CONTINUE', 'default': 'DEFAULT', 'do': 'DO', 'double': 'DOUBLE',
    'else': 'ELSE', 'enum': 'ENUM', 'extern': 'EXTERN', 'float': 'FLOAT', 'for': 'FOR',
    'goto': 'GOTO', 'if': 'IF', 'inline': 'INLINE', 'int': 'INT', 'long': 'LONG',
    'register': 'REGISTER', 'restrict': 'RESTRICT', 'return': 'RETURN', 'short': 'SHORT',
    'signed': 'SIGNED', 'sizeof': 'SIZEOF', 'static': 'STATIC', 'struct': 'STRUCT',
    'switch': 'SWITCH', 'typedef': 'TYPEDEF', 'union': 'UNION', 'unsigned': 'UNSIGNED',
    'void': 'VOID', 'volatile': 'VOLATILE', 'while': 'WHILE', '_Bool': 'BOOL',
    '_Complex': 'COMPLEX', '_Atomic': 'ATOMIC', '_Generic': 'GENERIC', '_Imaginary':'IMAGINARY',
    '_Static_assert': 'STATIC_ASSERT', '_Thread_local': 'THREAD_LOCAL'
}

#-----Token names required by PLY------
tokens = [
    #IDENTIFIER AND LITERALS
    'IDENTIFIER', 'INT_CONST', 'FLOAT_CONST', 'CHAR_CONST', 'STRING_LITERAL',
    
    #OPERATORS
    'PLUS','MINUS','TIMES','DIVIDE','MOD',
    'INC','DEC',
    'ASSIGN','PLUS_ASSIGN','MINUS_ASSIGN','MUL_ASSIGN','DIV_ASSIGN','MOD_ASSIGN',
    'EQ','NEQ','LT','GT','LE','GE',
    'AND','OR','NOT',
    'BAND','BOR','BXOR','BNOT',
    'LSHIFT','RSHIFT','LSHIFT_ASSIGN','RSHIFT_ASSIGN',
    'ARROW','DOT',
    
    #PREPROCESSOR DIRECTIVES FOR FUNCTION AT 142
    'PP_DIRECTIVE',
    
    #PUNCTUATORS
    'LPAREN','RPAREN','LBRACE','RBRACE','LBRACKET','RBRACKET',
    'SEMICOLON','COMMA','COLON','QUESTION','HASH',
    
] + list(_reserved.values())

#-------SIMPLE TOKEN REGEXES--------
t_PLUS = r'\+'
t_MINUS = r'\-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_MOD = r'%'

t_INC = r'\+\+'
t_DEC = r'--'

t_ASSIGN = r'='
t_PLUS_ASSIGN = r'\+='
t_MINUS_ASSIGN = r'-='
t_MUL_ASSIGN = r'\*='
t_DIV_ASSIGN = r'/='
t_MOD_ASSIGN = r'%='

t_EQ = r'=='
t_NEQ = r'!='
t_LT = r'<'
t_GT = r'>'
t_LE = r'<='
t_GE = r'>='

t_AND = r'&&'
t_OR = r'\|\|'
t_NOT = r'!'

t_BAND = r'&'
t_BOR = r'\|'
t_BXOR = r'\^'
t_BNOT = r'~'

t_LSHIFT = r'<<'
t_RSHIFT = r'>>'
t_LSHIFT_ASSIGN = r'<<='
t_RSHIFT_ASSIGN = r'>>='

t_ARROW = r'->'
t_DOT = r'\.'

t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'

t_SEMICOLON = r';'
t_COMMA = r','
t_COLON = r':'
t_QUESTION = r'\?'
t_HASH = r'\#'

#----IGNEORED CHARS (SPACES/TABS)-----
t_ignore = ' \t\r'

# ---------------- Complex tokens: order matters ----------------

def t_PP_DIRECTIVE(t):
    r'\#[^\n]*'
    t.type = 'PP_DIRECTIVE'
    return t

# String literal (double-quoted) - includes escape sequences
def t_STRING_LITERAL(t):
    r'"([^\\\n]|\\.)*"'
    if "\n" in t.value:
        logger.warning(f"Possible unterminated string literal at line {t.lineno}")
    return t

#-----------CHARACTER CONSTANT----------
def t_CHAR_CONST(t):
    r"'([^\\\n]|\\.)'"
    if "\n" in t.value:
        logger.warning(f"Possible unterminated char literal at line {t.lineno}")
    return t


float_suffix = r'([fFlL])?'

# Floating point constants (function → higher priority than simple int regex)
def t_FLOAT_CONST(t):
    r'((\d+\.\d*|\.\d+)([eE][+-]?\d+)?[fFlL]?|\d+[eE][+-]?\d+[fFlL]?)'
    # keep raw value; parser will interpret suffixes if needed
    t.value = t.value
    return t


#HEXADECIMAL integer literal
def t_INT_CONST_HEX(t):
    r'0[xX][0-9a-fA-F]+[uUlL]*'
    t.type = 'INT_CONST'
    t.value = t.value
    return t

#BINARY literal (GCC EXTENSION)
def t_INT_CONST_BIN(t):
    r'0[bB][01]+[uUlL]*'
    t.type = 'INT_CONST'
    t.value = t.value
    return t

#OCTAL literal
def t_INT_CONST_OCT(t):
    r'0[0-7]+[uUlL]*'    
    t.type = 'INT_CONST'
    t.value = t.value
    return t

#DECIMAL integer
def t_INT_CONST_DEC(t):
    r'\d+[uUlL]*'
    t.type = 'INT_CONST'
    t.value = t.value
    return t

#IDENTIFIER and KEYWORDS
def t_IDENTIFIER(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    val = t.value
    if val in _reserved:
        t.type = _reserved[val]
    else:
        t.type = 'IDENTIFIER'
    return t

#NWELINE (track line numbers)
def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

#COMMENTS SHOULD NOT APPEAR (preprocessor removed them). If present, skip safely.
def t_comment_single(t):
    r'//.*'
    t.lexer.lineno += t.value.count("\n")
    pass

def t_comment_multi(t):
    r'/\*[\s\S]*?\*/'
    t.lexer.lineno += t.value.count("\n")
    #skip comment
    pass

#ERROR HANDLING RULE
def t_error(t):
    bad_char = t.value[0]
    #compute column
    last_cr = t.lexer.lexdata.rfind('\n', 0, t.lexpos)
    col = t.lexpos - last_cr
    logger.warning(f"PHASE 3: Illegal character {bad_char!r} at line {t.lineno} col {col}")
    #create an ERROR token and return it so parser can see it if desired
    t.type = 'ERROR'
    t.value = bad_char
    #advance 1 char and return the token (allow parser to handle or ignore)
    t.lexer.skip(1)
    return t

#---------HELPER: compute column------------
def _find_column(input_text: str, token) -> int:
    # token.lexpos gives position in the whole input text
    last_cr = input_text.rfind('\n', 0, token.lexpos)
    if last_cr < 0:
        last_cr = -1
        
    return token.lexpos - last_cr

#-------MAIN API: LEXCODE--------

def build_lexer():
    #build a fresh lexer instance based on this module's rules
    from core import lexer_c
    return lex.lex(module=lexer_c, reflags=re.UNICODE)

def lex_code(cleaned_code: str) -> List[TokenObj]:
    """
    Tokenize cleaned_code and return a list of TokenObj(type, value, line, column).

    """
    logger.info("Phase 3: lex_code started")
    try:
        #build fresh lexer instance to avoid state carryover
        lexer = build_lexer()
        
        lexer.input(cleaned_code)
        tokens: List[TokenObj] = []
        for tok in lexer:
            #compute column
            col = _find_column(cleaned_code, tok)
            val = str(tok.value)
            if "\n" in val:
                #multi-line literal (rare, but possible if malformed strings)
                lines = val.splitlines()
                end_line = tok.lineno + len(lines) - 1
                end_col = len(lines[-1]) + 1
            else:
                end_line = tok.lineno
                end_col = col + len(val)
            token_obj = TokenObj(tok.type, tok.value, tok.lineno, col, end_line, end_col)
            tokens.append(token_obj)
            logger.debug(
                f"Phase 3: token {token_obj.type} "
                f"val = {token_obj.value!r}"
                f"start = ({token_obj.line}, {token_obj.column})"
                f"end = ({token_obj.end_line}, {token_obj.end_column})"
            )
        logger.info(f"Phase 3: lex_code finished, tokens = {len(tokens)}")
        return tokens
    except Exception as e:
        logger.error("Phase 3: lex_code failed: %s", e)
        logger.debug(traceback.format_exc())
        raise
    
# ---------------- Convenience: lex_file (for tests, not main pipeline) ----------------
def lex_file(path: str) -> List[TokenObj]:
    logger.info(f"Phase 3: lex_file called: {path}")
    p = Path(path)
    if not p.exists():
        msg = f"Phase 3: file not found: {path}"
        logger.error(msg)
        raise FileNotFoundError(msg)
    code = p.read_text(encoding='utf-8', errors='replace')
    return lex_code(code)
   
   
# ==================================================
# GLOBAL LEXER INSTANCE REQUIRED BY parser_ast.py
# ==================================================

import sys

def build_lexer():
    # Build lexer using the current module object
    return lex.lex(module=sys.modules[__name__])

# ---- THIS IS THE REQUIRED GLOBAL VARIABLE ----
lexer = build_lexer()
