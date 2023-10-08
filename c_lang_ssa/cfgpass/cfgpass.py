from typing import Tuple

from pycparser.c_ast import *
from c_lang_ssa.block.block import *
import graphviz
from dataclasses import dataclass


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
            (self._traverse_continue, Continue),
            (self._traverse_break, Break),
        ]
        self.start_blocks = self._traverse_file_ast(ast)
        self._merge_base_blocks()

    def _traverse_file_ast(self, node: FileAST) -> list[BaseBlock]:
        all_blocks = []
        for n in node.ext:
            end_block = BaseBlock()
            context = CFGContext(
                cycle_cont=None,
                cycle_after=None,
                return_block=end_block,
            )
            all_blocks.append(self._traverse(n, context)[0])
        return all_blocks

    def _traverse(self, node: Node, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        for (f, node_type) in self._traverses:
            if isinstance(node, node_type):
                return f(node, context)
        else:
            print(f"Unknown node: {type(node)} at {node.coord}")

    @staticmethod
    def _link_blocks(parent: BaseBlock, child: Block):
        # if not parent.is_final:
        parent.add_next_block(child)
        child.add_parent(parent)

    def _traverse_func_def(self, node: FuncDef, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        func_start_block = BaseBlock(label=f"function {node.decl.name} start")
        args = node.decl.type.args
        func_start_block.add_statements([] if args is None else args.params)
        (func_body_block_start, func_body_block_finish) = \
            self._traverse_compound(node.body, context)
        self._link_blocks(parent=func_start_block, child=func_body_block_start)
        return func_start_block, func_body_block_finish

    def _default_traverse(self, node: Node, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        print(f"use default traverse for {type(node)}")
        block = BaseBlock()
        block.add_statements([node])
        return block, block

    def _traverse_func_decl(self, node: FuncDecl, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        return self._default_traverse(node, context)

    def _traverse_param_list(self, node: ParamList, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        return self._default_traverse(node, context)

    def _traverse_decl(self, node: Decl, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        return self._default_traverse(node, context)

    def _traverse_compound(self, node: Compound, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        first_compound_block = BaseBlock()
        current_block = first_compound_block

        for n in (node.block_items or []):
            first, last = self._traverse(n, context)
            self._link_blocks(parent=current_block, child=first)
            current_block = last
        return first_compound_block, current_block

    def _traverse_if(self, node: If, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        begin_block = BaseBlock()
        cond_block = ConditionBlock()
        self._link_blocks(parent=begin_block, child=cond_block)
        cond_block.add_statements([node.cond])
        left_first_block, left_last_block = self._traverse(node.iftrue, context)
        if node.iffalse is not None:
            right_first_block, right_last_block = self._traverse(node.iffalse, context)
        else:
            b = BaseBlock()
            right_first_block, right_last_block = (b, b)
        join_block = BaseBlock()
        self._link_cond(cond_block, join_block, left_first_block, left_last_block, right_first_block, right_last_block)
        return begin_block, join_block

    def _link_cond(self, cond_block: ConditionBlock,
                   join_block: BaseBlock,
                   left_first_block: BaseBlock,
                   left_last_block: BaseBlock,
                   right_first_block: BaseBlock,
                   right_last_block: BaseBlock):
        cond_block.add_left_block(left_first_block)
        cond_block.add_right_block(right_first_block)
        left_first_block.add_parent(cond_block)
        right_first_block.add_parent(cond_block)
        if not left_last_block.is_final:
            self._link_blocks(parent=left_last_block, child=join_block)
        if not right_last_block.is_final:
            self._link_blocks(parent=right_last_block, child=join_block)

    def _traverse_while(self, node: While, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        begin_block = BaseBlock()
        cond_block = ConditionBlock()
        after_block = BaseBlock()

        self._link_blocks(parent=begin_block, child=cond_block)
        cond_block.add_statements([node.cond])
        first_statement, last_statement = \
            self._traverse(node.stmt,
                           CFGContext(return_block=context.return_block
                                      , cycle_cont=cond_block
                                      , cycle_after=after_block))

        cond_block.add_left_block(first_statement)
        first_statement.add_parent(cond_block)

        self._link_blocks(parent=last_statement, child=cond_block)

        cond_block.add_right_block(after_block)
        after_block.add_parent(cond_block)

        return begin_block, after_block

    def _traverse_for(self, node: For, context: 'CFGContext') -> Tuple[BaseBlock, BaseBlock]:
        init_block = BaseBlock()
        init_block.add_statements(node.init.decls)

        cond_block = ConditionBlock()
        cond_block.add_condition(node.cond)

        next_block = BaseBlock()
        next_block.add_statements([node.next])

        after_block = BaseBlock()

        first_statement, last_statement \
            = self._traverse(node.stmt,
                             CFGContext(return_block=context.return_block
                                        , cycle_cont=next_block
                                        , cycle_after=after_block))

        self._link_blocks(parent=init_block, child=cond_block)
        cond_block.add_left_block(first_statement)
        first_statement.add_parent(cond_block)
        self._link_blocks(parent=last_statement, child=next_block)
        self._link_blocks(parent=next_block, child=cond_block)
        cond_block.add_right_block(after_block)
        after_block.add_parent(cond_block)
        return init_block, after_block

    def _traverse_binary_op(self, node: BinaryOp, context: 'CFGContext') -> Tuple[Block, Block]:
        return self._default_traverse(node, context)

    def _traverse_assigment(self, node: Assignment, context: 'CFGContext') -> Tuple[Block, Block]:
        return self._default_traverse(node, context)

    def _traverse_return(self, node: Return, _context: 'CFGContext') -> Tuple[Block, Block]:
        block = BaseBlock(is_final=True)
        block.add_statements([node])
        return block, block

    def _traverse_continue(self, node: Continue, context: 'CFGContext') -> Tuple[Block, Block]:
        # return self._default_traverse(node, context)
        block = BaseBlock(is_final=True)
        # block.add_statements([node])
        if context.cycle_cont is None:
            raise "continue not in cycle"
        self._link_blocks(block, context.cycle_cont)
        return block, block

    def _traverse_break(self, node: Break, context: 'CFGContext') -> Tuple[Block, Block]:
        block = BaseBlock(is_final=True)
        block.add_statements([])
        if context.cycle_after is None:
            raise "break not in cycle"
        self._link_blocks(block, context.cycle_after)
        return block, block

    def show(self):
        dot = graphviz.Digraph("SSA", format='png', renderer='cairo', strict=True)
        self.start_blocks[0].generate_dot(dot)
        dot.view(quiet_view=True)

    def _merge_base_blocks(self):
        self.start_blocks[0].merge_blocks_recursive()


@dataclass(frozen=True)
class CFGContext:
    cycle_cont: Optional[BaseBlock]
    cycle_after: Optional[BaseBlock]
    return_block: BaseBlock
