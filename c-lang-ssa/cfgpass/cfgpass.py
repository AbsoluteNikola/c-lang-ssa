from typing import Tuple

from pycparser.c_ast import *
from .block import Block
import graphviz


# noinspection PyMethodMayBeStatic
class CfgPass:

    def __init__(self, ast: FileAST):
        self._traverses = [
            (self._traverse_func_def, FuncDef),
            (self._traverse_func_decl, FuncDecl),
            (self._traverse_param_list, ParamList),
            (self._traverse_decl, Decl),
            (self._traverse_compound, Compound),
            (self._traverse_if, If),
            (self._traverse_binary_op, BinaryOp),
            (self._traverse_assigment, Assignment),
            (self._traverse_return, Return),
        ]
        self.start_blocks = self._traverse_file_ast(ast)

    def _traverse_file_ast(self, node: FileAST) -> list[Block]:
        all_blocks = []
        for n in node.ext:
            all_blocks.append(self._traverse(n)[0])
        return all_blocks

    def _traverse(self, node: Node) -> Tuple[Block, Block]:
        for (f, node_type) in self._traverses:
            if isinstance(node, node_type):
                return f(node)
        else:
            print(f"Unknown node: {type(node)} at {node.coord}")

    @staticmethod
    def _link_blocks(parent: Block, child: Block):
        parent.add_next_block(child)
        child.add_parent(parent)

    def _traverse_func_def(self, node: FuncDef) -> Tuple[Block, Block]:
        func_start_block = Block(f"function {node.decl.name} start")
        func_start_block.add_statements(node.decl.type.args.params)
        (func_body_block_start, func_body_block_finish) = \
            self._traverse_compound(node.body)
        self._link_blocks(parent=func_start_block, child=func_body_block_start)
        return func_start_block, func_body_block_finish

    def _default_traverse(self, node: Node) -> Tuple[Block, Block]:
        print(f"use default traverse for {type(node)}")
        block = Block()
        block.add_statements([node])
        return block, block

    def _traverse_func_decl(self, node: FuncDecl) -> Tuple[Block, Block]:
        return self._default_traverse(node)

    def _traverse_param_list(self, node: ParamList) -> Tuple[Block, Block]:
        return self._default_traverse(node)

    def _traverse_decl(self, node: Decl) -> Tuple[Block, Block]:
        return self._default_traverse(node)

    def _traverse_compound(self, node: Compound) -> Tuple[Block, Block]:
        first_compound_block = Block()
        current_block = first_compound_block
        for n in node.block_items:
            first, last = self._traverse(n)
            self._link_blocks(parent=current_block, child=first)
            current_block = last
        return first_compound_block, current_block

    def _traverse_if(self, node: If) -> Tuple[Block, Block]:
        cond_block = Block()
        cond_block.add_statements([node.cond])
        left_first_block, left_last_block = self._traverse(node.iftrue)
        if node.iffalse is not None:
            right_first_block, right_last_block = self._traverse(node.iffalse)
        else:
            b = Block()
            right_first_block, right_last_block = (b, b)
        join_block = Block()

        self._link_blocks(parent=cond_block, child=left_first_block)
        self._link_blocks(parent=cond_block, child=right_first_block)
        self._link_blocks(parent=left_last_block, child=join_block)
        self._link_blocks(parent=right_last_block, child=join_block)
        return cond_block, join_block

    def _traverse_binary_op(self, node: BinaryOp) -> Tuple[Block, Block]:
        return self._default_traverse(node)

    def _traverse_assigment(self, node: Assignment) -> Tuple[Block, Block]:
        return self._default_traverse(node)

    def _traverse_return(self, node: Return) -> Tuple[Block, Block]:
        return self._default_traverse(node)

    def show(self):
        dot = graphviz.Digraph("CFG", format='png', renderer='cairo', strict=True)
        self._generate_dot(dot, self.start_blocks[0])
        dot.view(quiet_view=True)

    def _generate_dot(self, dot, block):
        body = block.render_statements()
        label = body if block.label == "" else f"{block.label}\\l\\l{body}"
        dot.node(str(id(block)), shape="record", label=label)
        for next_block in block.next_blocks:
            self._generate_dot(dot, next_block)
            dot.edge(str(id(block)), str(id(next_block)))
