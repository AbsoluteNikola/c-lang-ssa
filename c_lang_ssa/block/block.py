import abc
import copy
from abc import *
from dataclasses import dataclass
from typing import Optional

import frozendict as frozendict
from pycparser.c_ast import *
from pycparser.c_generator import CGenerator
from c_lang_ssa.ast_utils import rename_in_node


@dataclass
class DotParams:
    label: str
    color: str
    shape: str


class Block(ABC):
    def __init__(self, is_final: bool = False):
        self._statements = []
        self._parents = []
        self._next_blocks = []
        self._color = "white"
        self._phis = {}
        self._decls = []
        self.is_final = is_final

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
    def next_blocks_with_edge_color(self) -> list[tuple['Block', str]]:
        return [(b, "black") for b in self._next_blocks]

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

    def fill_decls(self) -> set[str]:
        return self._fill_decls(set())

    def _fill_decls(self, was) -> set[str]:
        was.add(id(self))

        for s in self._statements:
            if isinstance(s, Decl):
                self._decls.append(s.name)

        decls = (set(self._decls))

        for next_block in self.next_blocks:
            if id(next_block) not in was:
                decls = decls | next_block._fill_decls(was)
        return decls

    def init_phi_functions(self, variables: frozenset[str]):
        self._init_phi_functions(frozenset(), set())

    def _init_phi_functions(self, variables: frozenset[str], was):
        was.add(id(self))

        for s in self._statements:
            if isinstance(s, Decl):
                variables = variables.union(frozenset([s.name]))

        for next_block in self.next_blocks:
            if len(next_block.parents_blocks) > 1:
                for v in variables:
                    next_block._phis[v] = []

            if id(next_block) not in was:
                next_block._init_phi_functions(variables, was)

    def rename(self, variables):
        # vd = frozendict.frozendict()
        vd = {}
        for v in variables:
            vd[v] = 0
        self._rename(vd, frozendict.frozendict(), was=set())

    def _rename(self, var_available_names, env, was):
        was.add(id(self))

        for phi in list(self._phis.keys()):
            new_name = f"{phi}_{var_available_names[phi]}"
            var_available_names[phi] = var_available_names[phi] + 1
            env = env.set(phi, new_name)
            self._phis[new_name] = self._phis[phi]
            del self._phis[phi]

        for s in self._statements:
            for v, v_index in list(env.items()):
                rename_in_node(v, v_index, s)

            if isinstance(s, Assignment) and isinstance(s.lvalue, ID):
                name = s.lvalue.name
                new_name = f"{name}_{var_available_names[name]}"
                s.lvalue.name = new_name
                var_available_names[name] = var_available_names[name] + 1
                env = env.set(name, new_name)
                # vd = vd.set(name, vd[name] + 1)
            elif isinstance(s, Decl):
                name = s.name
                new_name = f"{name}_{var_available_names[name]}"
                s.name = new_name
                s.type.declname = f"{name}_{var_available_names[name]}"
                var_available_names[name] = var_available_names[name] + 1
                env = env.set(name, new_name)
                # vd = vd.set(name, vd[name] + 1)

        for next_block in self.next_blocks:
            if len(next_block._parents) > 1:
                for v, v_index in env.items():
                    for phi in next_block._phis.keys():
                        if phi.startswith(v):
                            next_block._phis[phi].append(v_index)
            if id(next_block) not in was:
                next_block._rename(var_available_names, env, was)

    @staticmethod
    def _render_phi(name, args):
        return f"{name} = phi({', '.join(args)})"

    def _render_statements(self) -> str:
        output = ""
        if len(self._phis) > 0:
            output = "\\l".join([self._render_phi(p, args)for (p, args) in self._phis.items()]) + "\\l"
        cg = CGenerator()
        for s in self._statements:
            output += f"{cg.visit(s)}\\l".replace("<", "\\<").replace(">", "\\>")
        return output

    def generate_dot(self, dot):
        self._generate_dot(dot, was=set())

    def _generate_dot(self, dot, was):
        was.add(id(self))
        params = self.dot_params()
        dot.node(str(id(self)), shape=params.shape, label=params.label, fillcolor=params.color, style='filled')
        for (next_block, color) in self.next_blocks_with_edge_color:
            if id(next_block) not in was:
                next_block._generate_dot(dot, was)
            dot.edge(str(id(self)), str(id(next_block)), color=color)

    def __str__(self):
        rendered_statements = self._render_statements().replace('\\l', ';')
        return f"{type(self)} {rendered_statements}"

    def __repr__(self): return self.__str__()


class BaseBlock(Block):

    def __init__(self, is_final: bool = False, label: str = ""):
        super().__init__(is_final=is_final)
        self._statements = []
        self._label = label

    @property
    def label(self):
        return self._label

    def add_next_block(self, block: 'Block'):
        self._next_blocks.append(block)

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
        super().__init__(is_final=False)
        self._next_blocks: list[Optional[Block]] = [None, None]

    def add_condition(self, cond: Node):
        self._statements = [cond]

    def add_left_block(self, block: Block):
        block.set_color("#80ff80")
        self._next_blocks[0] = block

    def add_right_block(self, block: Block):
        block.set_color("#ff9999")
        self._next_blocks[1] = block

    def dot_params(self) -> DotParams:
        label = self._render_statements()
        return DotParams(label=label, color='white', shape='record')

    # def _render_statements(self) -> str:
    #     cg = CGenerator()
    #     return f"{cg.visit(self._statements[0])}".replace("<", "\\<").replace(">", "\\>")

    @property
    def next_blocks_with_edge_color(self) -> list[tuple['Block', str]]:
        return [(self._next_blocks[0], "#2b782a"), (self._next_blocks[1], "red")]

    @property
    def _can_be_merged(self) -> bool:
        return False

    def _merge_with(self, block: 'BaseBlock'):
        raise Exception("ConditionBlock can't be merged")
