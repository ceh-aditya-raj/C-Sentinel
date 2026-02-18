# 🛡️ C-Sentinel
**Static C Code Analyzer · AST & CFG-Driven Vulnerability Detection Engine**

> “Don’t grep for bugs. Model the program.”

## 🔗 Live Demo
[https://c-sentinel.onrender.com/](https://c-sentinel.onrender.com/)

*(May take a few seconds to wake from cold start.)*

A sample `test-code.c` file is included for demonstration.

## 🔍 Overview

C-Sentinel is a static analysis engine for C programs that performs:
* Compiler-style lexical analysis
* Grammar-driven parsing
* Abstract Syntax Tree (AST) construction
* Control Flow Graph (CFG) generation
* Structural vulnerability detection

All without executing the target code.

Unlike pattern-based scanners, C-Sentinel understands program structure and execution flow, enabling accurate detection of memory corruption vulnerabilities with precise line-level context.

Built from scratch to explore how real static analyzers and compilers reason about code.

## 🧠 Core Capabilities

### ⚙️ Compiler-Grade Frontend
* Custom C lexer (tokenization engine)
* Grammar-driven parser
* Full Abstract Syntax Tree (AST) generation
* Preprocessing pipeline
* Token stream extraction

### 🔄 Control Flow Graph (CFG) Generation
C-Sentinel builds a Control Flow Graph per function, modeling:
* Entry and exit nodes
* Conditional branches (if, else)
* Loop structures
* Merge points
* Unreachable code paths

The CFG allows:
* Structural reasoning about execution paths
* Identification of unreachable blocks
* Context-aware vulnerability placement
* Foundation for future data-flow and taint analysis

Example CFG structure:
```text
entry
  ↓
IF (condition)
  ↙        ↘
then      else
  ↓          ↓
return     merge
```
This transforms static code into a graph-based execution model.

## 🛑 Static Vulnerability Detection

**Memory Corruption Detection**
* Stack buffer overflows
* Heap buffer overflows

**Detection of unsafe sinks:**
* `gets`
* `strcpy`
* `strcat`
* `scanf` (unbounded)

**Structural Awareness**
Detection is not text-based. C-Sentinel analyzes:
* Buffer allocation context (stack vs heap)
* Write paths into fixed-size buffers
* Call sites within CFG branches
* Variable ownership context

**Precise Reporting**
Each finding includes:
* Vulnerability type
* Severity level
* Function name
* Variable involved
* Exact source line
* Structured JSON output

## ⚙️ How It Works

```text
C Source Code
        ↓
Preprocessor
        ↓
Lexer → Tokens
        ↓
Parser → AST
        ↓
CFG Builder (per function)
        ↓
Static Analyzer
        ↓
Vulnerability Report
```

No execution.  
No fuzzing.  
No runtime instrumentation.  
No AI guessing.

Pure structural reasoning.

## 🧪 Example Detection

```c
char buf[8];
gets(buf);           // Stack overflow

char *p = malloc(8);
strcpy(p, input);    // Heap overflow
```

### Generated Report (simplified)
```json
{
  "type": "HEAP_OVERFLOW",
  "severity": "CRITICAL",
  "function": "strcpy",
  "line": 42,
  "variable": "p"
}
```

## 🌐 Web Interface

C-Sentinel provides a FastAPI-based web interface designed to be minimal, professional, and analysis-focused.

**Features:**
* **Upload .c files** for instant analysis.
* **View:**
    * Preprocessed source code (rendered via Monaco Editor)
    * Token stream extraction
    * AST (compiler-style tree visualization)
    * CFG (per-function flow visualization)
    * Structured vulnerability report

---

## 🧰 Tech Stack

### Backend
* **Python**: Core logic and engine.
* **FastAPI**: High-performance web framework.
* **Custom Lexer & Parser**: Built using PLY (Python Lex-Yacc).
* **Static Analysis Engine**: Custom AST-based logic.
* **CFG Builder**: Graph-based execution modeling.

### Frontend
* **HTML / CSS / JavaScript**: Custom UI components.
* **Monaco Editor**: High-fidelity code and AST rendering.
* **Visualization**: Structured graph and tree components.

### Deployment
* **Render**: Hosted as a Python Web Service.

---

## 🎯 Design Philosophy

C-Sentinel treats C as a language, not as text.

* ❌ **No regex-only scanning**
* ❌ **No runtime execution**
* ❌ **No black-box AI guesses**
* ❌ **No surface-level pattern matching**
* ✅ **Structural parsing**
* ✅ **Graph-based reasoning**
* ✅ **Deterministic results**
* ✅ **Explainable findings**
* ✅ **Compiler-style modeling**

---

## 📌 Use Cases

* **Security Research & Education**: Deep dive into how vulnerabilities look at the structural level.
* **Vulnerability Patterns**: Understanding memory corruption beyond the surface.
* **Compiler Internals**: Demonstrating AST and CFG concepts in a practical tool.
* **Foundation**: Prototype for advanced taint-analysis or data-flow engines.

---

## 🚧 Current Scope & Future Work




### Implemented
* Lexer & parser construction.
* Full AST generation.
* Per-function CFG generation.
* Stack & Heap overflow detection.
* Web-based analysis dashboard.

### Planned
* **Source → Sink Taint Analysis**: Tracking untrusted input through the graph.
* **Integer Overflow Detection**: Identifying arithmetic safety issues.
* **Null Pointer Dereference**: Detecting potential crashes.
* **Inter-procedural CFG Linking**: Connecting calls between different functions.
* **Data-flow Analysis**: SSA-based reasoning for better accuracy.

---

## ⚠️ Disclaimer

C-Sentinel is a static analyzer, not a guarantee of exploitability. Static analysis can produce false positives/negatives; all findings should be reviewed manually or combined with dynamic analysis tools.

---

## 👨‍💻 Author

Developed as a low-level security engineering project to explore:
* Compiler internals and program representation.
* Static analysis techniques and graph-based reasoning.
* Memory safety vulnerabilities in C.
