from typing import Optional

from pycparser.c_ast import Node
from pycparser.c_generator import CGenerator


class Block:
    def __init__(self, label: str = ""):
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
        self._statements += statements

    @property
    def statements(self) -> list[Node]:
        return self._statements

    @property
    def is_empty(self):
        return len(self._statements) == 0

    def render_statements(self) -> str:
        output = ""
        cg = CGenerator()
        for s in self._statements:
            output += f"{cg.visit(s)}\\l".replace("<", "\\<").replace(">", "\\>")
        return output

    def __str__(self):
        return self.render_statements().replace("\\l", "\n")

    def __repr__(self): return self.__str__()