class BaseAnalyzer:
    def __init__(self):
        self.vulnerabilities = []
        self.tainted_vars = set()
        self.heap_vars = set()
        self._visited = set()


    def analyze(self, ast):
        self.visit(ast)
        return self.vulnerabilities
    
    def visit(self, node):
        if id(node) in self._visited:
            return
        self._visited.add(id(node))
        try:
            if node is None:
                return

            if isinstance(node, list):
                for item in node:
                    self.visit(item)
                return

            if isinstance(node, tuple):
                for item in node:
                    self.visit(item)
                return

            if isinstance(node, (str, int, float, bool)):
                return

            method = f"visit_{type(node).__name__}"
            visitor = getattr(self, method, self.generic_visit)
            visitor(node)

        except Exception as e:
            print(f"[ANALYZER WARNING] {type(node).__name__}: {e}")


    def generic_visit(self, node):
        for attr, value in vars(node).items():
            if attr == "parent":
                continue

            # Assign parent safely
            if hasattr(value, "__dict__"):
                value.parent = node

            self.visit(value)


    def report(self, vuln):
        self.vulnerabilities.append(vuln)

    
    