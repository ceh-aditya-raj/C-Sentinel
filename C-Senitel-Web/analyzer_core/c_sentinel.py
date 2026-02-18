from analyzer_core.core.preprocess import preprocess_file
from analyzer_core.core.lexer_c import lex_code
from analyzer_core.core.parser_ast import parse_code
from analyzer_core.core.ast_printer import print_ast
from analyzer_core.analysis.buffer_overflow import BufferOverflowAnalyzer
import sys


# BEAUTIFUL TOKEN PRINTER

RESET   = "\033[0m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
MAGENTA = "\033[95m"
RED     = "\033[91m"
DIM     = "\033[2m"

def format_value(val):
    """Colorize token value nicely."""
    if val is None:
        return RED + "None" + RESET
    if isinstance(val, str):
        return GREEN + repr(val) + RESET
    return MAGENTA + str(val) + RESET

def print_tokens(tokens):
    """Beautiful, aligned token table output."""
    print("\n" + CYAN + "=== LEXER: TOKENIZATION ===" + RESET + "\n")

    header = f"{YELLOW}LINE COL  TYPE{' ' * 20}VALUE{RESET}"
    print(header)
    print(DIM + "-" * 70 + RESET)

    for t in tokens:
        line = f"{t.line}".rjust(4)
        col  = f"{t.column}".rjust(4)

        token_type = (CYAN + t.type + RESET).ljust(22)
        value = format_value(t.value)

        print(f"{line} {col}  {token_type} {value}")


def run_pipeline(input_path):
    # Phase 2
    cleaned_code, meta = preprocess_file(input_path)
    print(f"\n[PRE-PROCESSOR OUTPUT] Length of CLEANED CODE is: {len(cleaned_code)}")
    #print(cleaned_code)

    # Phase 3
    tokens = lex_code(cleaned_code)
    print_tokens(tokens)

    # Phase 4
    ast = parse_code(cleaned_code)
    print("\n=== ABSTRACT SYNTAX TREE ===")
    print_ast(ast, is_root=True)

    # Phase 4.5: CFG Generation
    from analyzer_core.core.cfg import CFGGenerator, BasicBlock, CFG
    cfg_gen = CFGGenerator()
    cfgs = cfg_gen.build(ast) 
    print(f"\n[CFG] Generated Control Flow Graphs for {len(cfgs)} functions.")

    return {
        "ast": ast,
        "preprocessed_code": cleaned_code,
        "tokens": tokens,
        "cfg": cfgs
    }



    
if __name__ == "__main__":
    
    if len(sys.argv) != 2:
        print("Usage: python c_sentinel.py <file.c>")
        exit(1)

    # Phase 1–4
    ast = run_pipeline(sys.argv[1])

    # Phase 5: Vulnerability Analysis
    analyzer = BufferOverflowAnalyzer()
    vulns = analyzer.analyze(ast)
    if not vulns:
        print("\n[✓] No vulnerabilities detected")
    else:
        print("\n======= VULNERABILITY REPORT =======")
        for v in vulns:
            print(v)