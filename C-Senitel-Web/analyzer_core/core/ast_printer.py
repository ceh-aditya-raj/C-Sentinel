# ==========================================================
# AST PRINTER — HIGH-VISIBILITY TERMINAL EDITION
# ==========================================================

import os
import platform

# ---------------- ANSI COLOR DEFINITIONS ------------------
class Colors:
    RESET = ''
    BOLD  = ''
    LIME_GREEN   = ''
    ELECTRIC_BLUE= ''
    HOT_PINK     = ''
    GOLD         = ''
    PURPLE       = ''
    NEON_CYAN    = ''
    PURE_GREEN   = ''
    WHITE        = ''

# Enable colors only if not on Windows or if explicitly enabled
if platform.system() != 'Windows' or os.getenv('ANSICON'):
    class Colors:
        RESET = '\033[0m'
        BOLD  = '\033[1m'
        LIME_GREEN   = '\033[38;5;118m'
        ELECTRIC_BLUE= '\033[38;5;39m'
        HOT_PINK     = '\033[38;5;198m'
        GOLD         = '\033[38;5;220m'
        PURPLE       = '\033[38;5;129m'
        NEON_CYAN    = '\033[38;5;51m'
        PURE_GREEN   = '\033[38;5;46m'
        WHITE        = '\033[97m'


# ---------------- AST NODE → COLOR MAP --------------------
COLOR_MAP = {
    'Program': Colors.BOLD + Colors.LIME_GREEN,
    'FunctionDef': Colors.ELECTRIC_BLUE,

    'VarDecl': Colors.HOT_PINK,
    'Include': Colors.HOT_PINK,

    'Assign': Colors.GOLD,
    'Return': Colors.GOLD,

    'BinOp': Colors.PURPLE,
    'FunctionCall': Colors.PURPLE,

    'ID': Colors.NEON_CYAN,
    'Constant': Colors.PURE_GREEN,
}


def get_color(node):
    return COLOR_MAP.get(type(node).__name__, Colors.RESET)


# ---------------- CORE AST PRINTER ------------------------
def print_ast(node, indent='', is_last=True, is_root=False):
    """
    Pretty printer that NEVER prints a tree symbol for Program.
    """

    # ---------- ROOT (Program) ----------
    if is_root:
        print(get_color(node) + "Program" + Colors.RESET)
        children = getattr(node, "external_declarations", [])
        for i, child in enumerate(children):
            print_ast(child, indent="", is_last=(i == len(children) - 1))
        return

    branch = "+-- " if is_last else "|-- "
    prefix = indent + branch

    # ---------- None ----------
    if node is None:
        print(prefix + Colors.WHITE + "None" + Colors.RESET)
        return

    # ---------- Primitive ----------
    if isinstance(node, (str, int, float, bool)):
        print(prefix + Colors.PURE_GREEN + repr(node) + Colors.RESET)
        return

    # ---------- List ----------
    if isinstance(node, list):
        print(prefix + Colors.WHITE + "list" + Colors.RESET)
        sub = indent + ("    " if is_last else "|   ")
        for i, item in enumerate(node):
            
            print_ast(item, sub, i == len(node) - 1)
        return

    # ---------- Non-AST ----------
    if not hasattr(node, "__dict__"):
        print(prefix + repr(node))
        return

    # ---------- AST NODE ----------
    node_color = get_color(node)
    print(prefix + node_color + type(node).__name__ + Colors.RESET)

    sub = indent + ("    " if is_last else "|   ")
    attrs = list(node.__dict__.items())

    for i, (name, value) in enumerate(attrs):
        last = (i == len(attrs) - 1)
        attr_prefix = sub + ("+-- " if last else "|-- ")

        # ---- Simple fields ----
        if isinstance(value, (str, int, float, bool)) or value is None:

            # SPECIAL CASE: Include → show PP_DIRECTIVE
            if type(node).__name__ == "Include" and name in ("text", "filename"):
                print(attr_prefix + Colors.HOT_PINK + "PP_DIRECTIVE" + Colors.RESET)
                continue

            if name == "value" and type(node).__name__ == "Constant":
                vcolor = Colors.PURE_GREEN
            elif name in ("name", "filename"):
                vcolor = Colors.NEON_CYAN
            elif name in ("op", "type_name"):
                vcolor = Colors.GOLD
            else:
                vcolor = Colors.WHITE

            print(
                attr_prefix +
                Colors.WHITE + name + ": " +
                vcolor + repr(value) +
                Colors.RESET
            )

        # ---- Complex fields ----
        else:
            print(attr_prefix + Colors.WHITE + name + ":" + Colors.RESET)
            print_ast(value, sub + ("    " if last else "|   "), True)


# ---------------- ENTRY POINT -----------------------------
def print_ast_root(ast):
    print("\n" + Colors.BOLD + Colors.LIME_GREEN + "=== ABSTRACT SYNTAX TREE ===" + Colors.RESET)
    print_ast(ast, is_root=True)
    print(Colors.LIME_GREEN + "=" * 55 + Colors.RESET)
