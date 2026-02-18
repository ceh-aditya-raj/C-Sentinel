import uuid

class BasicBlock:
    def __init__(self, label="block"):
        self.id = str(uuid.uuid4())[:8]  
        self.label = label
        self.instructions = []  
        self.successors = []    
        self.predecessors = []  

    def add_instruction(self, node):
        self.instructions.append(node)

    def add_successor(self, block):
        if block not in self.successors:
            self.successors.append(block)
        if self not in block.predecessors:
            block.predecessors.append(self)

    def to_dict(self):
        """Serialize for frontend consumption."""
        return {
            "id": self.id,
            "label": self.label,
            "instructions": [str(inst) for inst in self.instructions],
            "successors": [b.id for b in self.successors]
        }


class CFG:
    def __init__(self):
        self.blocks = []
        self.entry_block = None

    def add_block(self, block):
        if block not in self.blocks:
            self.blocks.append(block)

    def set_entry(self, block):
        self.entry_block = block
        self.add_block(block)

    def to_dict(self):
        return {
            "entry_id": self.entry_block.id if self.entry_block else None,
            "blocks": [b.to_dict() for b in self.blocks]
        }


class CFGGenerator:
    """
    Traverses the AST and builds a Control Flow Graph.
    """
    def __init__(self):
        self.cfg = CFG()
        self.current_block = None
        self.loop_stack = [] 

    def format_instruction(self, node):
        """
        Recursively formats an AST node into a readable C-like string.
        """
        if node is None:
            return ""

        t = type(node).__name__

        if t == "Constant":
            return str(node.value)
        
        elif t == "Identifier":
            return str(node.name)
        
        elif t == "ID":
            return str(node.name)

        elif t == "BinaryOp":
            left = self.format_instruction(node.left)
            right = self.format_instruction(node.right)
            return f"{left} {node.op} {right}"

        elif t == "Assignment": 
            left = self.format_instruction(node.lvalue)
            right = self.format_instruction(node.rvalue)
            return f"{left} {node.op} {right}"

        elif t == "UnaryOp":
            operand = self.format_instruction(node.operand)
            if node.op == "p++": return f"{operand}++"
            if node.op == "p--": return f"{operand}--"
            return f"{node.op}{operand}"
            
        elif t == "Decl":
            name = node.name if node.name else ""
            init = ""
            if hasattr(node, "init") and node.init:
                 init = f" = {self.format_instruction(node.init)}"
            return f"Decl {name}{init}"
            
        elif t == "FuncCall":
            args = []
            if hasattr(node, "args") and node.args:
                arg_list = node.args.exprs if hasattr(node.args, "exprs") else []
                args = [self.format_instruction(a) for a in arg_list]
            return f"{node.name.name}({', '.join(args)})"

        elif t == "ArrayRef":
            base = self.format_instruction(node.base)
            index = self.format_instruction(node.index)
            return f"{base}[{index}]"

        elif t == "MemberAccess":
            base = self.format_instruction(node.base)
            member = str(node.member.name) if hasattr(node.member, "name") else str(node.member)
            return f"{base}.{member}"

        elif t == "PointerMemberAccess":
            base = self.format_instruction(node.base)
            member = str(node.member.name) if hasattr(node.member, "name") else str(node.member)
            return f"{base}->{member}"
            
        elif t == "Cast":
            to_type = str(node.to_type)
            expr = self.format_instruction(node.expr)
            return f"({to_type}){expr}"

        elif t == "TernaryOp":
            cond = self.format_instruction(node.condition)
            true_e = self.format_instruction(node.true_expr)
            false_e = self.format_instruction(node.false_expr)
            return f"{cond} ? {true_e} : {false_e}"
            
        elif t == "Return":
             expr = self.format_instruction(node.expr) if node.expr else ""
             return f"return {expr}"
        
        elif t == "Break":
            return "break"

        elif t == "SwitchStmt":
            expr = self.format_instruction(node.expr)
            return f"SWITCH ({expr})"

        elif t == "CaseStmt":
            val = self.format_instruction(node.value)
            return f"CASE {val}"

        elif t == "DefaultStmt":
            return "DEFAULT"
        
        elif t == "ExprStmt":
             return self.format_instruction(node.expr)

        if hasattr(node, "coord"):
             return f"Stmt at {node.coord.line}"
        return t

    def build(self, ast_root):
        """Main entry point. Takes an AST root (Program or FunctionDef)."""

        functions_cfgs = {}
        
        if type(ast_root).__name__ == "Program":
            for decl in ast_root.external_declarations:
                if type(decl).__name__ == "FunctionDef":
                    func_cfg = self.build_function_cfg(decl)
                    functions_cfgs[decl.name] = func_cfg.to_dict()
        
        return functions_cfgs

    def build_function_cfg(self, func_node):
        """Builds CFG for a single function."""
        self.cfg = CFG()
        
        # 1. Create Entry Block
        entry = BasicBlock(label=f"entry_{func_node.name}")
        self.cfg.set_entry(entry)
        self.current_block = entry
        
        # 2. Visit Body
        self.visit(func_node.body)
        
        return self.cfg

    def visit(self, node):
        """Dispatch method similar to BaseAnalyzer."""
        if node is None:
            return
        
        # Check for list of statements (common in Compound nodes)
        if isinstance(node, list):
            for item in node:
                self.visit(item)
            return

        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        visitor(node)

    def generic_visit(self, node):
        # Default: just add this node as an instruction to the current block
        if self.current_block:
            # Use the new formatter
            inst = self.format_instruction(node)
            if inst:
                self.current_block.add_instruction(inst)
            
            pass

    # ---------------------------------------------------------
    # Control Flow Visitors
    # ---------------------------------------------------------

    def visit_Compound(self, node):
        # Just visit all children in order
        if hasattr(node, "items"):
            for item in node.items:
                self.visit(item)

    def visit_IfStmt(self, node):
        # 1. The condition is in the current block
        cond_str = self.format_instruction(node.cond)
        self.current_block.add_instruction(f"IF ({cond_str})")
        
        pred_block = self.current_block
        
        # 2. Create THEN block
        then_block = BasicBlock(label="then")
        self.cfg.add_block(then_block)
        
        # 3. Create MERGE block (where paths rejoin)
        merge_block = BasicBlock(label="if_merge")
        self.cfg.add_block(merge_block)
        
        # --- Handle THEN Path ---
        # Link Predecessor -> Then
        pred_block.add_successor(then_block)
        
        self.current_block = then_block
        self.visit(node.then_stmt)
        # Link End of Then -> Merge
        self.current_block.add_successor(merge_block)
        
        # --- Handle ELSE Path ---
        if node.else_stmt:
            else_block = BasicBlock(label="else")
            self.cfg.add_block(else_block)
            
            # Link Predecessor -> Else
            pred_block.add_successor(else_block)
            
            self.current_block = else_block
            self.visit(node.else_stmt)
            # Link End of Else -> Merge
            self.current_block.add_successor(merge_block)
        else:
            # If no else, False branch goes straight to MERGE
            pred_block.add_successor(merge_block)

        # 4. Continue from MERGE
        self.current_block = merge_block

    def visit_WhileStmt(self, node):
        # 1. Create Loop Header (Condition) Block
        header_block = BasicBlock(label="while_cond")
        self.cfg.add_block(header_block)
        
        # Link Entry -> Header
        self.current_block.add_successor(header_block)
        
        # 2. Create Body Block
        body_block = BasicBlock(label="while_body")
        self.cfg.add_block(body_block)
        
        # 3. Create Exit Block
        exit_block = BasicBlock(label="while_exit")
        self.cfg.add_block(exit_block)
        
        # Setup Header
        self.current_block = header_block
        cond_str = self.format_instruction(node.cond)
        self.current_block.add_instruction(f"WHILE ({cond_str})")
        self.current_block.add_successor(body_block) # True => Body
        self.current_block.add_successor(exit_block) # False => Exit
        
        # Track for break/continue
        self.loop_stack.append({
            "header": header_block,
            "exit": exit_block
        })
        
        # Visit Body
        self.current_block = body_block
        self.visit(node.body)
        
        # Loop back to header from end of body
        self.current_block.add_successor(header_block)
        
        self.loop_stack.pop()
        
        # Continue from Exit
        self.current_block = exit_block

    def visit_ForStmt(self, node):
        # 1. Init
        if node.init:
            self.current_block.add_instruction(f"FOR_INIT")

        # 2. Header
        header_block = BasicBlock(label="for_cond")
        self.cfg.add_block(header_block)
        self.current_block.add_successor(header_block)
        
        # 3. Body
        body_block = BasicBlock(label="for_body")
        self.cfg.add_block(body_block)
        
        # 4. Post
        post_block = BasicBlock(label="for_post")
        self.cfg.add_block(post_block)
        
        # 5. Exit
        exit_block = BasicBlock(label="for_exit")
        self.cfg.add_block(exit_block)
        
        # Header logic
        self.current_block = header_block
        self.current_block.add_instruction("FOR_COND")
        self.current_block.add_successor(body_block) # True
        self.current_block.add_successor(exit_block) # False
        
        # Loop Stack
        self.loop_stack.append({
            "header": post_block, # 'continue' goes to post-increment
            "exit": exit_block
        })
        
        # Visit Body
        self.current_block = body_block
        self.visit(node.body)
        
        # Body -> Post
        self.current_block.add_successor(post_block)
        
        # Post -> Header
        self.current_block = post_block
        if node.post:
            self.current_block.add_instruction("FOR_POST")
        self.current_block.add_successor(header_block)
        
        self.loop_stack.pop()
        
        # Continue from Exit
        self.current_block = exit_block

    def visit_Return(self, node):
        self.current_block.add_instruction(f"RETURN")
        # Dead code block
        dead_block = BasicBlock(label="unreachable")
        self.cfg.add_block(dead_block)
        self.current_block = dead_block
