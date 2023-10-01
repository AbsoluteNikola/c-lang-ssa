import abc
from abc import *
from dataclasses import dataclass
from typing import Optional

from pycparser.c_ast import Node
from pycparser.c_generator import CGenerator


@dataclass
class DotParams:
    label: str
    color: str
    shape: str


class Block(ABC):
    def __init__(self):
        self._statements = []
        self._parents = []
        self._next_blocks = []
        self._color = "white"

    def add_parent(self, block: 'Block'):
        self._parents.append(block)

    @property
    def parents_blocks(self) -> list['Block']:
        return self._parents

    def add_statements(self, statements: list[Node]):
        self._statements += statements

    @property
    def statements(self) -> list[Node]:
        return self._statements

    @property
    def is_empty(self):
        return len(self._statements) == 0

    def set_color(self, color):
        self._color = color

    @property
    def next_blocks(self) -> list['Block']:
        return self._next_blocks

    @property
    @abc.abstractmethod
    def dot_params(self) -> DotParams:
        pass

    @property
    @abc.abstractmethod
    def _can_be_merged(self) -> bool:
        return False

    @abc.abstractmethod
    def _merge_with(self, block: 'Block'):
        pass

    def merge_blocks_recursive(self):
        self._merge_blocks_recursive(set())

    # empty block is block without statements and always base block
    # it can have more than one parent, but only one next block
    def _eliminate_empty(self):
        next_block = self._next_blocks[0]
        next_block._parents.remove(self)
        for p in self._parents:
            # next_block.set_color(self._color)
            p._next_blocks.remove(self)
            p._next_blocks.append(next_block)
            next_block._parents.append(p)

    def _merge_blocks_recursive(self, was):
        was.add(id(self))

        # merge chains of base block line b1 -> b2 -> b3
        i = 0
        while self._can_be_merged and i < len(self.next_blocks):
            if self.next_blocks[i]._can_be_merged:
                self._merge_with(self.next_blocks[i])
                i = 0
            else:
                i += 1

        i = 0
        while i < len(self.next_blocks):
            if self.next_blocks[i].is_empty:
                self.next_blocks[i]._eliminate_empty()
                i = 0
            else:
                i += 1

        for next_block in self.next_blocks:
            if id(next_block) not in was:
                next_block._merge_blocks_recursive(was)

    def _render_statements(self) -> str:
        output = ""
        cg = CGenerator()
        for s in self._statements:
            output += f"{cg.visit(s)}\\l".replace("<", "\\<").replace(">", "\\>")
        return output

    def __str__(self):
        rendered_statements = self._render_statements().replace('\\l', ';')
        return f"{type(self)} {rendered_statements}"

    def __repr__(self): return self.__str__()


class BaseBlock(Block):

    def __init__(self, label: str = ""):
        super().__init__()
        self._statements = []
        self._label = label

    @property
    def label(self):
        return self._label

    def add_next_block(self, block: 'Block'):
        self._next_blocks.append(block)

    @property
    def dot_params(self) -> DotParams:
        label = self._render_statements()
        return DotParams(label=label, color=self._color, shape='record')

    @property
    def _can_be_merged(self) -> bool:
        return len(self.next_blocks) == 1 and len(self._parents) <= 1

    def _merge_with(self, block: 'BaseBlock'):
        self._next_blocks = block.next_blocks
        self._statements += block.statements
        del block


class ConditionBlock(Block):

    def __init__(self):
        super().__init__()
        self._next_blocks: list[Optional[Block]] = [None, None]

    def add_condition(self, cond: Node):
        self._statements = [cond]

    def add_left_block(self, block: Block):
        block.set_color("#80ff80")
        self._next_blocks[0] = block

    def add_right_block(self, block: Block):
        block.set_color("#ff9999")
        self._next_blocks[1] = block

    @property
    def dot_params(self) -> DotParams:
        label = self._render_statements()
        return DotParams(label=label, color='white', shape='diamond')

    def _render_statements(self) -> str:
        cg = CGenerator()
        return f"{cg.visit(self._statements[0])}".replace("<", "\\<").replace(">", "\\>")

    @property
    def _can_be_merged(self) -> bool:
        return False

    def _merge_with(self, block: 'BaseBlock'):
        raise Exception("ConditionBlock can't be merged")
