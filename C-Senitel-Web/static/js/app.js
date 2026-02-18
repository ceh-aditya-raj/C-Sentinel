// =============================
// Monaco Initialization
// =============================
let codeEditor = null;
let astEditor = null;
let pendingPreprocessedCode = "";
let pendingAstText = "";

require.config({
  paths: {
    vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs"
  }
});

require(["vs/editor/editor.main"], function () {

  // -----------------------------
  // Custom AST Language
  // -----------------------------
  monaco.languages.register({ id: "astlang" });

  monaco.languages.setMonarchTokensProvider("astlang", {
    tokenizer: {
      root: [
        [/Program|FunctionDef|Declaration|ExprStmt|Return/, "node.major"],
        [/Compound|Call|Identifier|Constant/, "node.medium"],
        [/ArrayDecl|VarDeclarator/, "node.minor"],
        [/Include/, "node.include"],
        [/'.*?'/, "string"],
        [/\(.*?\)/, "meta"],
        [/├──|└──|│/, "tree"],
        [/[\w_]+:/, "property"]
      ]
    }
  });

  monaco.editor.defineTheme("ast-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "node.major", foreground: "4FC1FF", fontStyle: "bold" },
      { token: "node.medium", foreground: "C586C0" },
      { token: "node.minor", foreground: "9CDCFE" },
      { token: "node.include", foreground: "DCDCAA" },
      { token: "property", foreground: "CE9178" },
      { token: "string", foreground: "CE9178" },
      { token: "meta", foreground: "6A9955" },
      { token: "tree", foreground: "808080" }
    ],
    colors: {
      "editor.background": "#0f1115"
    }
  });

  // -----------------------------
  // Preprocessed Code Editor
  // -----------------------------
  codeEditor = monaco.editor.create(
    document.getElementById("code-editor"),
    {
      value: "// Upload a C file and click Analyze\n",
      language: "c",
      theme: "vs-dark",
      readOnly: true,
      minimap: { enabled: false },
      fontSize: 13,
      scrollBeyondLastLine: false,
      automaticLayout: true
    }
  );
  window.codeEditor = codeEditor;
  if (pendingPreprocessedCode) {
    codeEditor.setValue(pendingPreprocessedCode);
  }

  // -----------------------------
  // AST Editor (Textual Tree)
  // -----------------------------
  astEditor = monaco.editor.create(
    document.getElementById("ast-editor"),
    {
      value: "// AST will appear here after analysis\n",
      language: "astlang",
      theme: "ast-dark",
      readOnly: true,
      minimap: { enabled: false },
      fontSize: 13,
      lineNumbers: "on",
      scrollBeyondLastLine: false,
      automaticLayout: true
    }
  );
  window.astEditor = astEditor;
  if (pendingAstText) {
    astEditor.setValue(pendingAstText);
  }
});

// =============================
// DOM References
// =============================
const analyzeBtn = document.getElementById("analyzeBtn");
const fileInput = document.getElementById("fileInput");
const panelHeaders = document.querySelectorAll(".panel-header");

// Initialize Mermaid
if (typeof mermaid !== 'undefined') {
  mermaid.initialize({ startOnLoad: false, theme: 'dark' });
}

// =============================
// Analyze Button Logic
// =============================
analyzeBtn.addEventListener("click", async () => {
  if (!fileInput.files.length) {
    alert("Please select a .c file first.");
    return;
  }

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error("Analysis failed");
    }

    const data = await response.json();
    if (data.status && data.status !== "success") {
      throw new Error(data.error || data.message || "Analysis failed");
    }

    // -----------------------------
    // Preprocessed Code
    // -----------------------------
    pendingPreprocessedCode = data.preprocessed_code || "// No preprocessed code generated";
    if (codeEditor) {
      codeEditor.setValue(pendingPreprocessedCode);
    }

    // -----------------------------
    // Tokens
    // -----------------------------
    renderTokens(data.tokens || []);

    // -----------------------------
    // AST (Text Tree)
    // -----------------------------
    pendingAstText = data.ast_text || data.ast || "// No AST generated";
    if (astEditor) {
      astEditor.setValue(pendingAstText);
    }

    // -----------------------------
    // Vulnerabilities
    // -----------------------------
    renderVulnerabilities(data.vulnerabilities || []);

    // -----------------------------
    // CFG (Mermaid)
    // -----------------------------
    if (data.cfg) {
      renderCFG(data.cfg);
    }

    openResultsPanels();

  } catch (err) {
    console.error(err);
    alert("Error while analyzing the file. Check console.");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze";
  }
});

function openResultsPanels() {
  const labelsToOpen = [
    "Token Stream",
    "Abstract Syntax Tree (AST)",
    "Control Flow Graph (CFG)",
    "Vulnerability Report"
  ];

  for (const header of panelHeaders) {
    const label = (header.querySelector("span")?.textContent || "").trim();
    if (labelsToOpen.includes(label)) {
      header.parentElement.classList.add("open");
    }
  }

  if (codeEditor) codeEditor.layout();
  if (astEditor) astEditor.layout();
}

// =============================
// Token Renderer
// =============================
function renderTokens(tokens) {
  const tbody = document.querySelector("#tokenTable tbody");
  if (!tbody) return;

  tbody.innerHTML = "";

  if (!tokens.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="placeholder">No tokens</td>
      </tr>`;
    return;
  }

  for (const t of tokens) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${t.line}</td>
      <td>${t.column}</td>
      <td>${t.type}</td>
      <td>${t.value ?? ""}</td>
    `;
    tbody.appendChild(row);
  }
}

// =============================
// Vulnerability Renderer
// =============================
function renderVulnerabilities(vulns) {
  const container = document.getElementById("vulnContainer");
  if (!container) return;

  container.innerHTML = "";

  if (!vulns.length) {
    container.innerHTML =
      `<div class="placeholder">No vulnerabilities detected</div>`;
    return;
  }

  for (const v of vulns) {
    const severity = String(v?.severity || "UNKNOWN");
    const type = String(v?.type || "UNKNOWN");
    const fnName = String(v?.function || "-");
    const line = v?.line ?? "-";
    const variable = String(v?.variable || "-");
    const message = String(v?.message || "No details available");

    const card = document.createElement("div");
    card.className = `vuln-card severity-${severity.toLowerCase()}`;

    card.innerHTML = `
      <div class="vuln-header">
        <span class="vuln-severity">${severity}</span>
        <span class="vuln-type">${type}</span>
      </div>
      <div class="vuln-body">
        <div><strong>Function:</strong> ${fnName}</div>
        <div><strong>Line:</strong> ${line}</div>
        <div><strong>Variable:</strong> ${variable}</div>
        <div class="vuln-message">${message}</div>
      </div>
    `;
    container.appendChild(card);
  }
}


// =============================
// CFG Renderer (Mermaid)
// =============================
async function renderCFG(cfgMap) {
  const container = document.getElementById("cfgContainer");
  if (!container) return;
  if (!cfgMap || typeof cfgMap !== "object" || !Object.keys(cfgMap).length) {
    container.innerHTML = '<div class="placeholder">No CFG generated</div>';
    return;
  }

  // Check if Mermaid is loaded
  if (typeof mermaid === 'undefined') {
    try {
      // Fallback: try dynamic import if global is missing
      const module = await import('/static/js/mermaid.min.js');
      window.mermaid = module.default;
      mermaid.initialize({ startOnLoad: false, theme: 'dark' });
    } catch (e) {
      console.error("Mermaid import failed:", e);
      container.innerHTML = '<div class="placeholder" style="color: #ff5f5f;">Error: Mermaid library not loaded. Check internet connection or content blocker.</div>';
      return;
    }
  }

  // Clear previous
  container.innerHTML = "";
  container.removeAttribute("data-processed"); // Force re-render

  // Sort functions alphabetically for consistent order
  const funcNames = Object.keys(cfgMap).sort();

  for (const funcName of funcNames) {
    const cfg = cfgMap[funcName];

    // Create a wrapper for this function
    const wrapper = document.createElement("div");
    wrapper.className = "cfg-function-wrapper";
    wrapper.style.marginBottom = "40px"; // Spacing between CFGs
    wrapper.style.borderBottom = "1px solid #30363d";
    wrapper.style.paddingBottom = "20px";

    const title = document.createElement("h3");
    title.textContent = `Function: ${funcName}`;
    title.style.color = "#58a6ff";
    title.style.marginBottom = "10px";
    wrapper.appendChild(title);

    // Create container for the graph
    const graphDiv = document.createElement("div");
    // Unique ID for this graph
    const graphId = `mermaid-${funcName}-${Math.floor(Math.random() * 10000)}`;
    graphDiv.id = graphId;
    wrapper.appendChild(graphDiv);
    container.appendChild(wrapper);

    // Generate Mermaid Code logic for THIS function only
    let graph = "graph TD\n";
    graph += "  classDef default fill:#161a22,stroke:#252b36,color:#e6e8eb;\n";

    // Map blocks
    for (const block of (cfg.blocks || [])) {
      // Escape label
      let label = block.label;
      if (block.instructions && block.instructions.length > 0) {
        const content = block.instructions.join("\\n");
        label += "\\n" + content;
      }

      // Sanitization for mermaid strings
      label = label.replace(/"/g, "'");

      // Node definition
      graph += `    ${block.id}["${label}"]\n`;

      // Edges (inside block loop in original data structure, though technically edges are separate)
      // The original code had edges nested in block loop? Let's check.
      // Yes: for (const succId of block.successors) { graph += ... }
      if (block.successors) {
        for (const succId of block.successors) {
          graph += `    ${block.id} --> ${succId}\n`;
        }
      }
    }

    // Render THIS graph
    try {
      mermaid.render(graphId + "-svg", graph, (svgCode) => {
        graphDiv.innerHTML = svgCode;
      });
    } catch (e) {
      console.error(`Mermaid failed for ${funcName}:`, e);
      graphDiv.innerHTML = `<div style="color:red">Error rendering CFG for ${funcName}</div>`;
    }
  }
}
