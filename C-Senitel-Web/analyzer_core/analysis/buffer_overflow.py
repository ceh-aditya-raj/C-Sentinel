from .base_analyzer import BaseAnalyzer

HEAP_ALLOCATORS = {"malloc", "calloc", "realloc"}


class BufferOverflowAnalyzer(BaseAnalyzer):
    def _extract_call_name(self, call):
        func = getattr(call, "func", None)
        return getattr(func, "name", None)

    def _unwrap_call(self, node):
        if node is None:
            return None
        t = type(node).__name__
        if t == "Call":
            return node
        if t == "Cast":
            return self._unwrap_call(getattr(node, "expr", None))
        return None

    def _target_base_name(self, node):
        if node is None:
            return None
        t = type(node).__name__
        if hasattr(node, "name"):
            return node.name
        if t == "UnaryOp" and getattr(node, "op", None) == "&":
            return self._target_base_name(getattr(node, "operand", None))
        if t == "ArrayRef":
            return self._target_base_name(getattr(node, "base", None))
        if t in {"MemberAccess", "PointerMemberAccess"}:
            return self._target_base_name(getattr(node, "base", None))
        return None

    def _target_label(self, node):
        if node is None:
            return "unknown"
        t = type(node).__name__
        if hasattr(node, "name"):
            return str(node.name)
        if t == "UnaryOp" and getattr(node, "op", None) == "&":
            return f"&{self._target_label(getattr(node, 'operand', None))}"
        if t == "ArrayRef":
            return f"{self._target_label(getattr(node, 'base', None))}[]"
        if t == "MemberAccess":
            member = getattr(getattr(node, "member", None), "name", "field")
            return f"{self._target_label(getattr(node, 'base', None))}.{member}"
        if t == "PointerMemberAccess":
            member = getattr(getattr(node, "member", None), "name", "field")
            return f"{self._target_label(getattr(node, 'base', None))}->{member}"
        return t

    def visit_Call(self, node):
        func_name = self._extract_call_name(node)
        args = getattr(node, "args", []) or []
        line_no = "unknown"

        func_obj = getattr(node, "func", None)
        if hasattr(func_obj, "pos") and func_obj.pos and func_obj.pos[0] is not None:
            line_no = func_obj.pos[0]

        if not func_name:
            self.generic_visit(node)
            return

        write_arg_index = {
            "gets": 0,
            "strcpy": 0,
            "strcat": 0,
            "scanf": -1,
        }

        if func_name in HEAP_ALLOCATORS:
            parent = getattr(node, "parent", None)
            if parent and hasattr(parent, "name"):
                self.heap_vars.add(parent.name)
            self.generic_visit(node)
            return

        if func_name not in write_arg_index:
            self.generic_visit(node)
            return

        idx = write_arg_index[func_name]
        if idx < 0:
            idx = len(args) + idx
        if idx < 0 or idx >= len(args):
            self.generic_visit(node)
            return

        target = args[idx]
        base_name = self._target_base_name(target)
        target_label = self._target_label(target)
        vuln_type = "HEAP_OVERFLOW" if base_name in self.heap_vars else "STACK_OVERFLOW"

        self.report({
            "type": vuln_type,
            "severity": "CRITICAL",
            "severity_score": 9.8,
            "function": func_name,
            "line": line_no,
            "variable": target_label,
            "message": (
                f"Unsafe function '{func_name}' writes to "
                f"{vuln_type.lower().replace('_', ' ')} '{target_label}'"
            )
        })

        self.generic_visit(node)

    def visit_Declaration(self, node):
        for decl in getattr(node, "declarators", []) or []:
            name = getattr(decl, "name", None)
            init = getattr(decl, "initializer", None)
            if not name or not init:
                continue

            call = self._unwrap_call(init)
            if call and self._extract_call_name(call) in HEAP_ALLOCATORS:
                self.heap_vars.add(name)

        self.generic_visit(node)
