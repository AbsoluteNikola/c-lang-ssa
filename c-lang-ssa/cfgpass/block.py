from typing import Optional

from pycparser.c_ast import Node
from pycparser.c_generator import CGenerator


class Block:
    def __init__(self, label: str):
        self._next_blocks = []
        self._statements = []
        self._parents_blocks = []
        self._label = label

    @property
    def label(self):
        return self._label

    @property
    def next_blocks(self) -> list['Block']:
        return self._next_blocks

    def add_next_block(self, block: 'Block'):
        self._next_blocks.append(block)

    @property
    def parents_blocks(self) -> list['Block']:
        return self._parents_blocks

    def add_parent(self, block: 'Block'):
        self._parents_blocks.append(block)

    def add_statements(self, statements: list[Node]):
        print(statements)
        self._statements += statements
        pass

    @property
    def statements(self) -> list[Node]:
        return self._statements

    def merge(self, block: 'Block'):
        if len(block.parents_blocks) > 1:
            raise (Exception(f"Can't merge blocks. next {block} has more than one parent"))
        elif len(block.parents_blocks) == 1 and block.parents_blocks[0] is not self:
            raise (Exception(f"Can't merge blocks. next {block} has another parent"))
        elif len(self._next_blocks) > 1:
            raise (Exception(f"Can't merge blocks. current {block} has more than one next block"))

        self._statements += block._statements
        self._next_blocks = block._next_blocks

    def render_statements(self) -> str:
        output = ""
        cg = CGenerator()
        for s in self._statements:
            output += f"{cg.visit(s)}\l"
        return output
