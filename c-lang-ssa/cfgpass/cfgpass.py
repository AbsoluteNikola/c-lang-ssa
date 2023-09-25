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
            all_blocks.append(self._traverse(n))
        return all_blocks

    def _traverse(self, node: Node) -> Block:
        for (f, node_type) in self._traverses:
            if isinstance(node, node_type):
                return f(node)
        else:
            print(f"Unknown node: {type(node)}")

    def _traverse_func_def(self, node: FuncDef) -> Block:
        func_start_block = Block()
        func_start_block.add_statements(node.decl.type.args.params)
        func_body_block = self._traverse_compound(node.body)
        func_start_block.merge(func_body_block)
        return func_start_block

    def _traverse_func_decl(self, node: FuncDecl):
        print(type(node))

    def _traverse_param_list(self, node: ParamList):
        print(type(node))

    def _traverse_decl(self, node: Decl):
        print(type(node))

    def _traverse_compound(self, node: Compound) -> Block:
        first_block = Block()
        current_block = first_block
        for n in node.block_items:
            if isinstance(n, If):
                current_block.add_statements([n.cond])

                left_block, right_block = self._traverse_if(n)
                current_block.add_next_block(left_block)
                current_block.add_next_block(right_block)
                left_block.add_parent(left_block)
                right_block.add_parent(right_block)

                new_block = Block()
                new_block.add_parent(left_block)
                new_block.add_parent(right_block)
                left_block.add_next_block(new_block)
                right_block.add_next_block(new_block)
                current_block = new_block
            else:
                current_block.add_statements([n])
        return first_block

    def _traverse_if(self, node: If) -> Tuple[Block, Block]:
        left_block = self._traverse_compound(node.iftrue)
        right_block = self._traverse_compound(node.iffalse)
        return left_block, right_block

    def _traverse_binary_op(self, node: BinaryOp):
        print(type(node))

    def _traverse_assigment(self, node: Assignment):
        print(type(node))

    def _traverse_return(self, node: Return):
        print(type(node))

    def show(self):
        dot = graphviz.Digraph("CFG", format='png')
        self._generate_dot(dot, self.start_blocks[0])
        dot.view()

    def _generate_dot(self, dot, block):
        dot.node(str(id(block)), shape="record", label=block.render_statements())
        for next_block in block.next_blocks:
            self._generate_dot(dot, next_block)
            dot.edge(str(id(block)), str(id(next_block)))
