import tempfile
import os

from analyzer_core.c_sentinel import run_pipeline
from analyzer_core.analysis.buffer_overflow import BufferOverflowAnalyzer
from analyzer_core.utils.ast_text import ast_to_text


def analyze_c_code(code: str, filename: str = "input.c"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".c") as f:
        f.write(code.encode())
        temp_path = f.name

    try:
        # Run pipeline
        pipeline = run_pipeline(temp_path)

        ast = pipeline["ast"]
        tokens = pipeline["tokens"]
        preprocessed_code = pipeline["preprocessed_code"]

        # AST as text
        ast_text = ast_to_text(ast, is_root=True)

        analyzer = BufferOverflowAnalyzer()
        issues = analyzer.analyze(ast)

        return {
            "status": "success",
            "file_name": filename,

            # 🔑 THESE FIX THE UI
            "preprocessed_code": preprocessed_code,
            "tokens": serialize_tokens(tokens),

            # New AST format
            "ast_text": ast_text,

            "vulnerabilities": issues,
            "total_issues": len(issues),
            "cfg": pipeline["cfg"]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Analysis failed",
            "error": str(e)
        }

    finally:
        os.remove(temp_path)



# ─────────────────────────────
# Helpers 
# ─────────────────────────────

def serialize_tokens(tokens):
    return [
        {
            "line": t.line,
            "column": t.column,
            "type": t.type,
            "value": t.value
        }
        for t in tokens
    ]


def serialize_ast(node, depth=0):
    if node is None or depth > 15:
        return None

    data = {
        "node": type(node).__name__,
        "children": []
    }

    for value in vars(node).values():
        if hasattr(value, "__dict__"):
            child = serialize_ast(value, depth + 1)
            if child:
                data["children"].append(child)

        elif isinstance(value, list):
            for item in value:
                if hasattr(item, "__dict__"):
                    child = serialize_ast(item, depth + 1)
                    if child:
                        data["children"].append(child)

    return data
