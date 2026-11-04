"""Interface de linha de comando do analisador TONTO."""

import argparse

from compilador.packages import load_project
from compilador.reports import render_report


def main(argv=None):
    argument_parser = argparse.ArgumentParser(description="Analisador sintático de ontologias TONTO.")
    argument_parser.add_argument("paths", nargs="+", metavar="ARQUIVO_OU_PASTA",
                                 help="arquivos .tonto ou pastas (sem busca recursiva)")
    arguments = argument_parser.parse_args(argv)
    project = load_project(arguments.paths)
    print(render_report(project))
    if project.diagnostics:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
