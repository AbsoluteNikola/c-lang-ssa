import argparse
from pycparser import parse_file
from pycparser.c_ast import *
from cfgpass.cfgpass import *


def main():
    argparser = argparse.ArgumentParser('Dump AST')
    argparser.add_argument('filename',
                           default='examples/basic_with_cycles.c',
                           nargs='?',
                           help='name of file to parse')
    argparser.add_argument('--coord', help='show coordinates in the dump',
                           action='store_true')
    args = argparser.parse_args()

    ast: FileAST = parse_file(args.filename, use_cpp=False)
    ast.show()
    cfg = CfgPass(ast)
    cfg.show()


if __name__ == '__main__':
    main()
