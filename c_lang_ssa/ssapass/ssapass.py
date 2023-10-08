import graphviz

from c_lang_ssa.block.block import *
import copy


class SSAPass:
    def __init__(self, start_block: Block):
        self.start_block = copy.deepcopy(start_block)
        variables = self.start_block.fill_decls()
        self.start_block.init_phi_functions(variables)
        self.start_block.rename(variables)
        pass

    def show(self):
        dot = graphviz.Digraph("CFG", format='png', renderer='cairo', strict=True)
        self.start_block.generate_dot(dot)
        dot.view(quiet_view=True)

