from pycparser.c_ast import *


def rename_in_node(old_var_name: str, new_var_name: str, n: Node):
    if n is None:
        return
    elif isinstance(n, Decl):
        _rename_decl(old_var_name, new_var_name, n)
    elif isinstance(n, Assignment):
        _rename_assignment(old_var_name, new_var_name, n)
    elif isinstance(n, BinaryOp):
        _rename_binop(old_var_name, new_var_name, n)
    elif isinstance(n, ID):
        if n.name == old_var_name:
            n.name = new_var_name


def _rename_decl(old_var_name: str, new_var_name: str, n: Decl):
    rename_in_node(old_var_name, new_var_name, n.init)


def _rename_assignment(old_var_name: str, new_var_name: str, n: Assignment):
    rename_in_node(old_var_name, new_var_name, n.lvalue)
    rename_in_node(old_var_name, new_var_name, n.rvalue)


def _rename_binop(old_var_name: str, new_var_name: str, n: BinaryOp):
    rename_in_node(old_var_name, new_var_name, n.left)
    rename_in_node(old_var_name, new_var_name, n.right)

# def get_usages()