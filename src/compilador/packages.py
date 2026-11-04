from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from compilador import ast
from compilador.symbols import SymbolTable


@dataclass
class Project:
    table: SymbolTable = field(default_factory=SymbolTable)
    asts: dict[str, ast.ListInstructions | None] = field(default_factory=dict)

    @property
    def packages(self):
        return self.table.packages

    @property
    def symbols(self):
        return self.table.symbols

    @property
    def imports(self):
        return self.table.imports

    @property
    def references(self):
        return self.table.references

    @property
    def diagnostics(self):
        return self.table.diagnostics


def _select_files(paths, table):
    if isinstance(paths, (str, Path)):
        paths = [paths]
    selected = []
    seen = set()
    for supplied in paths:
        path = Path(supplied).expanduser()
        try:
            path = path.resolve()
            if path.is_dir():
                # glob() pode ocultar erros de acesso e produzir uma lista vazia.
                candidates = sorted(
                    entry for entry in path.iterdir()
                    if entry.suffix == ".tonto" and entry.is_file()
                )
                if not candidates:
                    table.add_diagnostic(
                        "no_source_files", f"A pasta '{path}' não contém arquivos .tonto.",
                        "Informe uma pasta com arquivos .tonto diretamente nela.",
                        file=str(path), stage="packages",
                    )
                    continue
            else:
                candidates = [path]
        except OSError as error:
            table.add_diagnostic(
                "invalid_path", f"Não foi possível acessar '{path}': {error}.",
                "Verifique o caminho e as permissões de leitura.",
                file=str(path), stage="packages",
            )
            continue
        for candidate in candidates:
            try:
                candidate = candidate.resolve()
            except OSError as error:
                table.add_diagnostic(
                    "invalid_path", f"Não foi possível acessar '{candidate}': {error}.",
                    "Verifique o caminho e as permissões de leitura.",
                    file=str(candidate), stage="packages",
                )
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.suffix != ".tonto":
                table.add_diagnostic(
                    "invalid_extension", f"O arquivo '{candidate}' não é .tonto.",
                    "Forneça arquivos .tonto ou a pasta que os contém.",
                    file=str(candidate), stage="packages",
                )
                continue
            selected.append(candidate)
    return selected


def _parse_source(source):
    from compilador.syntax import parse_code

    result = parse_code(source)
    return result.tree, result.diagnostics


def load_project(paths):
    project = Project()
    files = _select_files(paths, project.table)

    # Etapa 1: ler cada arquivo uma vez e registrar todas as declarações.
    for path in files:
        filename = str(path)
        project.asts[filename] = None
        try:
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            project.table.add_diagnostic(
                "file_read_error", f"Não foi possível ler '{filename}': {error}.",
                "Verifique se o arquivo existe, tem permissão de leitura e usa UTF-8.",
                file=filename, stage="packages",
            )
            continue

        tree, diagnostics = _parse_source(source)
        for error in diagnostics:
            project.table.add_diagnostic(
                error["code"], error["message"], error["suggestion"],
                file=filename, line=error.get("line"), column=error.get("column"),
                stage=error["stage"],
            )
        project.asts[filename] = tree
        if tree is None:
            if any(error["stage"] == "syntax" for error in diagnostics):
                continue
            project.table.add_diagnostic(
                "ast_unavailable", "O parser não produziu uma AST para este arquivo.",
                "Verifique os erros sintáticos apresentados pelo parser.",
                file=filename, stage="packages",
            )
            continue
        project.table.register_ast(tree, filename)

    # Etapa 2: imports e referências são ligações entre símbolos já registrados.
    project.table.resolve()
    return project
