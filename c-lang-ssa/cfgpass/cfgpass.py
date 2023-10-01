from typing import Tuple

from pycparser.c_ast import *
from .block import *
import graphviz


# TODO: break in for and while, switch case, labels goto, returns
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
            (self._traverse_while, While),
            (self._traverse_for, For),
        ]
        self.start_blocks = self._traverse_file_ast(ast)
        self._merge_base_blocks()

    def _traverse_file_ast(self, node: FileAST) -> list[BaseBlock]:
        all_blocks = []
        for n in node.ext:
            all_blocks.append(self._traverse(n)[0])
        return all_blocks

    def _traverse(self, node: Node) -> Tuple[BaseBlock, BaseBlock]:
        for (f, node_type) in self._traverses:
            if isinstance(node, node_type):
                return f(node)
        else:
            print(f"Unknown node: {type(node)} at {node.coord}")

    @staticmethod
    def _link_blocks(parent: BaseBlock, child: Block):
        parent.add_next_block(child)
        child.add_parent(parent)

    def _traverse_func_def(self, node: FuncDef) -> Tuple[BaseBlock, BaseBlock]:
        func_start_block = BaseBlock(f"function {node.decl.name} start")
        args = node.decl.type.args
        func_start_block.add_statements([] if args is None else args.params)
        (func_body_block_start, func_body_block_finish) = \
            self._traverse_compound(node.body)
        self._link_blocks(parent=func_start_block, child=func_body_block_start)
        return func_start_block, func_body_block_finish

    def _default_traverse(self, node: Node) -> Tuple[BaseBlock, BaseBlock]:
        print(f"use default traverse for {type(node)}")
        block = BaseBlock()
        block.add_statements([node])
        return block, block

    def _traverse_func_decl(self, node: FuncDecl) -> Tuple[BaseBlock, BaseBlock]:
        return self._default_traverse(node)

    def _traverse_param_list(self, node: ParamList) -> Tuple[BaseBlock, BaseBlock]:
        return self._default_traverse(node)

    def _traverse_decl(self, node: Decl) -> Tuple[BaseBlock, BaseBlock]:
        return self._default_traverse(node)

    def _traverse_compound(self, node: Compound) -> Tuple[BaseBlock, BaseBlock]:
        first_compound_block = BaseBlock()
        current_block = first_compound_block

        for n in (node.block_items or []):
            first, last = self._traverse(n)
            self._link_blocks(parent=current_block, child=first)
            current_block = last
        return first_compound_block, current_block

    def _traverse_if(self, node: If) -> Tuple[BaseBlock, BaseBlock]:
        begin_block = BaseBlock()
        cond_block = ConditionBlock()
        self._link_blocks(parent=begin_block, child=cond_block)
        cond_block.add_statements([node.cond])
        left_first_block, left_last_block = self._traverse(node.iftrue)
        if node.iffalse is not None:
            right_first_block, right_last_block = self._traverse(node.iffalse)
        else:
            b = BaseBlock()
            right_first_block, right_last_block = (b, b)
        join_block = BaseBlock()
        cond_block.add_left_block(left_first_block)
        cond_block.add_right_block(right_first_block)
        left_first_block.add_parent(cond_block)
        right_first_block.add_parent(cond_block)
        self._link_blocks(parent=left_last_block, child=join_block)
        self._link_blocks(parent=right_last_block, child=join_block)
        return begin_block, join_block

    def _traverse_while(self, node: While) -> Tuple[BaseBlock, BaseBlock]:
        begin_block = BaseBlock()
        cond_block = ConditionBlock()
        after_block = BaseBlock()

        self._link_blocks(parent=begin_block, child=cond_block)
        cond_block.add_statements([node.cond])
        first_statement, last_statement = self._traverse(node.stmt)

        cond_block.add_left_block(first_statement)
        first_statement.add_parent(cond_block)

        self._link_blocks(parent=last_statement, child=cond_block)

        cond_block.add_right_block(after_block)
        after_block.add_parent(cond_block)

        return begin_block, after_block

    def _traverse_for(self, node: For) -> Tuple[BaseBlock, BaseBlock]:
        init_block = BaseBlock()
        init_block.add_statements(node.init.decls)

        cond_block = ConditionBlock()
        cond_block.add_condition(node.cond)

        next_block = BaseBlock()
        next_block.add_statements([node.next])

        after_block = BaseBlock()

        first_statement, last_statement = self._traverse(node.stmt)
        self._link_blocks(parent=init_block, child=cond_block)
        cond_block.add_left_block(first_statement)
        first_statement.add_parent(cond_block)
        self._link_blocks(parent=last_statement, child=next_block)
        self._link_blocks(parent=next_block, child=cond_block)
        cond_block.add_right_block(after_block)
        after_block.add_parent(cond_block)
        return init_block, after_block

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

    def _merge_base_blocks(self):
        self.start_blocks[0].merge_blocks_recursive()

    def _generate_dot(self, dot, block, was=None):
        if was is None:
            was = set()
        was.add(id(block))
        params = block.dot_params
        dot.node(str(id(block)), shape=params.shape, label=params.label, fillcolor=params.color, style='filled')
        for next_block in block.next_blocks:
            if id(next_block) not in was:
                self._generate_dot(dot, next_block, was)
            dot.edge(str(id(block)), str(id(next_block)))
