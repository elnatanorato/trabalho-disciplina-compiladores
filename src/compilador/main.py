"""Interface de linha de comando do analisador TONTO."""

import argparse

from compilador.packages import load_project
from compilador.reports import render_report


def main(argv=None):
    argument_parser = argparse.ArgumentParser(description="Analisador TONTO com verificações semânticas parciais opcionais.")
    argument_parser.add_argument("paths", nargs="+", metavar="ARQUIVO_OU_PASTA",
                                 help="arquivos .tonto ou pastas (sem busca recursiva)")
    argument_parser.add_argument("--semantic", action="store_true",
                                 help="verifica marcadores de gensets; não reconhece todos os ODPs")
    argument_parser.add_argument("--coerce", action="store_true",
                                 help="com --semantic, ajusta disjoint em uma cópia em memória e revalida")
    arguments = argument_parser.parse_args(argv)
    if arguments.coerce and not arguments.semantic:
        argument_parser.error("--coerce exige --semantic")
    project = load_project(arguments.paths)
    semantic = None
    if arguments.semantic:
        from compilador.semantic_errors import analyze_semantics

        semantic = analyze_semantics(project, coerce=arguments.coerce)
    print(render_report(project, semantic=semantic))
    if project.diagnostics or (semantic is not None and semantic.diagnostics):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
