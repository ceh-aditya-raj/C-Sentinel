"""
Phase 2 — Preprocessor (Option 3, pcpp disabled)

• Removes comments (// and /* */)
• Preserves line numbers (comments replaced with blank lines / same number of '\n')
• Preserves macros (#define) and includes (#include)
• Does NOT expand macros or includes
• Handles strings, char literals, escape sequences safely
• Full logging
"""

from pathlib import Path
import logging
import traceback
from typing import Tuple


# ---------------------------------------------------------
# Force logging to project-root/logs/sentinel.log
# ---------------------------------------------------------
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
logger = logging.getLogger("c_sentinel.phase2")


# ---------------------------------------------------------
# STATE-MACHINE PREPROCESSOR (Primary Implementation)
# ---------------------------------------------------------

def preprocess_code(code: str) -> Tuple[str, dict]:
    """
    Process code with a robust state-machine.
    Preserves line count.
    """
    logger.info("Phase 2: preprocess_code started (state-machine only)")

    meta = {"warnings": []}

    try:
        n = len(code)
        i = 0
        out = []

        in_single = False
        in_multi = False
        in_string = False
        in_char = False
        escape = False

        while i < n:
            ch = code[i]

            
            if in_single:
                if ch == "\n":
                    in_single = False
                    out.append("\n")  # preserve newline
                i += 1
                continue

        
            if in_multi:
                if ch == "\n":
                    out.append("\n")  # preserve line count
                    i += 1
                    continue
                if code[i:i+2] == "*/":
                    in_multi = False
                    i += 2
                    continue
                i += 1
                continue

        
            if in_string:
                out.append(ch)
                if escape:
                    escape = False
                else:
                    if ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_string = False
                i += 1
                continue

            
            if in_char:
                out.append(ch)
                if escape:
                    escape = False
                else:
                    if ch == "\\":
                        escape = True
                    elif ch == "'":
                        in_char = False
                i += 1
                continue


            two = code[i:i+2]

            if two == "//":
                in_single = True
                i += 2
                continue

            if two == "/*":
                in_multi = True
                i += 2
                continue

            # Start of string
            if ch == '"':
                in_string = True
                out.append(ch)
                i += 1
                continue

            # Start of char literal
            if ch == "'":
                in_char = True
                out.append(ch)
                i += 1
                continue

            # Normal character
            out.append(ch)
            i += 1


        if in_multi:
            meta["warnings"].append("Unclosed multi-line comment at EOF.")
            logger.warning("Phase 2: Unclosed multi-line comment.")

        if in_string:
            meta["warnings"].append("Unclosed string literal at EOF.")
            logger.warning("Phase 2: Unclosed string literal.")

        if in_char:
            meta["warnings"].append("Unclosed char literal at EOF.")
            logger.warning("Phase 2: Unclosed char literal.")

        # ---------------------------
        # Normalize whitespace (light)
        # ---------------------------
        intermediate = "".join(out)
        cleaned_lines = [ln.rstrip() for ln in intermediate.splitlines()]
        cleaned = "\n".join(cleaned_lines)

        if code.endswith("\n"):
            cleaned += "\n"

        meta["original_length"] = len(code)
        meta["cleaned_length"] = len(cleaned)

        logger.info(
            f"Phase 2 successful: original={meta['original_length']} cleaned={meta['cleaned_length']}"
        )
        return cleaned, meta

    except Exception as e:
        logger.error("Phase 2: Exception in preprocess_code: %s", e)
        logger.debug(traceback.format_exc())
        raise



def preprocess_file(path: str) -> Tuple[str, dict]:
    logger.info(f"Phase 2: preprocess_file called: {path}")

    p = Path(path)
    if not p.exists():
        msg = f"Input file does not exist: {path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    try:
        code = p.read_text(encoding="utf-8", errors="replace")
        cleaned, meta = preprocess_code(code)
        meta["source_path"] = str(p.resolve())
        return cleaned, meta
    except Exception as e:
        logger.error("Phase 2: preprocess_file failed: %s", e)
        logger.debug(traceback.format_exc())
        raise

