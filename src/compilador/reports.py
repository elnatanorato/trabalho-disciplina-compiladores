"""Síntese baseada nos símbolos registrados e apresentação dos diagnósticos."""

from collections import Counter

from compilador import ast
from compilador.symbols import DEFAULT_PACKAGE


def _cardinality(value):
    if value is None:
        return "não informada"
    if value.end is None:
        return f"[{value.start}]"
    return f"[{value.start}..{value.end}]"


def _package_name(name):
    return "(sem pacote declarado)" if name == DEFAULT_PACKAGE else name


def _relation(symbol):
    node = symbol.node
    source = node.name1 if isinstance(node, ast.RelationOut) else symbol.owner
    target = node.name2 if isinstance(node, ast.RelationOut) else node.name
    name = "(sem nome)" if symbol.anonymous else symbol.name
    stereotype = f" {node.at}" if node.at else ""
    if isinstance(node.type, ast.RelationType2):
        operator = f"{node.type.operator1} {name} {node.type.operator2}"
    else:
        operator = str(node.type.operator)
    return name, f"{source} {_cardinality(node.cardinality1)} {operator} {_cardinality(node.cardinality2)} {target}{stereotype}"


def build_summary(project):
    """Retorna dados sem imprimir nem modificar o projeto.

    Totais representam símbolos aceitos pela tabela; duplicatas rejeitadas não
    são contadas novamente. Havendo erros, os dados podem estar incompletos.
    """
    counts = Counter(symbol.category for symbol in project.symbols.values())
    counts["internal_relation"] = len(project.table.relations(external=False))
    counts["external_relation"] = len(project.table.relations(external=True))
    rows = []
    for package in sorted(project.packages):
        display_package = _package_name(package)
        imports = project.imports.get(package, [])
        dependencies = ", ".join(
            reference.name + (" (não encontrado)" if reference.target is None else "")
            for reference in imports
        ) or "nenhuma"
        files = sorted(path for path, tree in project.asts.items() if tree is not None and any(
            symbol.package == package and symbol.file == path
            for symbol in project.symbols.values()
        ))
        rows.append([display_package, "Pacote", display_package,
                     f"Arquivos: {', '.join(files) or 'não informado'}; importações: {dependencies}"])
        symbols = sorted(project.table.symbols_in_package(package), key=lambda s: (s.category, s.owner or "", s.name))
        for symbol in symbols:
            node = symbol.node
            if symbol.category == "class":
                parent = f"; especializa: {node.specializes}" if node.specializes else ""
                details = f"Estereótipo: {node.stereotype}{parent}"
                category, name = "Classe", symbol.name
            elif symbol.category == "datatype":
                category, name = "Tipo complexo", symbol.name
                details = f"Tipo-base: {node.specializes or 'não informado'}"
            elif symbol.category == "attribute":
                category, name = "Atributo", f"{symbol.owner}.{symbol.name}"
                metas = ", ".join(str(meta) for meta in (node.metas or [])) or "nenhum"
                details = f"Tipo: {node.type}; cardinalidade: {_cardinality(node.cardinality)}; metas: {metas}"
            elif symbol.category == "enum":
                category, name = "Enumeração", symbol.name
                details = "Valores: " + ", ".join(node.variances)
            elif symbol.category == "genset":
                category, name = "Generalizações", symbol.name
                details = (f"Geral: {node.general}; específicas: {', '.join(node.specifics)}; "
                           f"disjoint: {'sim' if node.is_disjoint else 'não'}; "
                           f"complete: {'sim' if node.is_complete else 'não'}")
            elif symbol.category == "relation":
                category = "Relação interna" if symbol.owner else "Relação externa"
                name, details = _relation(symbol)
                if symbol.owner:
                    name = f"{symbol.owner}.{name}"
            else:
                continue
            rows.append([display_package, category, name, details])
    return {"counts": dict(counts), "rows": rows, "partial": bool(project.diagnostics)}


def _table(headers, rows):
    # Uma linha de saída por registro, mesmo se uma mensagem contiver quebras.
    rows = [[str(value).replace("\n", " ").replace("\r", " ") for value in row] for row in rows]
    widths = [max(len(row[index]) for row in [headers, *rows]) for index in range(len(headers))]
    def format_row(row):
        return " | ".join(value.ljust(width) for value, width in zip(row, widths))
    return "\n".join([format_row(headers), "-+-".join("-" * width for width in widths),
                      *(format_row(row) for row in rows)])


def render_report(project):
    summary = build_summary(project)
    labels = [
        ("package", "Pacotes/escopos"), ("class", "Classes"),
        ("datatype", "Tipos complexos"), ("enum", "Enumerações"),
        ("enum_value", "Valores enumerados"), ("attribute", "Atributos"),
        ("genset", "Conjuntos de generalizações"),
        ("internal_relation", "Relações internas"), ("external_relation", "Relações externas"),
    ]
    output = ["TABELA DE SÍNTESE", _table(["Construto", "Quantidade"], [
        [label, str(summary["counts"].get(key, 0))] for key, label in labels
    ])]
    if summary["rows"]:
        output.extend(["", _table(["Pacote", "Construto", "Nome", "Detalhes"], summary["rows"])])
    if summary["partial"]:
        output.append("\nATENÇÃO: análise com erros; a síntese pode estar incompleta e não inclui duplicatas rejeitadas.")
    output.extend(["", "RELATÓRIO DE ERROS"])
    stages = {"lexical": "Léxico", "syntax": "Sintático", "symbols": "Símbolos",
              "packages": "Pacotes/arquivos", "resolution": "Resolução"}
    for diagnostic in sorted(project.diagnostics, key=lambda d: (
        d["file"] or "", d["line"] or 0, d["column"] or 0, d["stage"], d["code"],
    )):
        location = diagnostic["file"] or "arquivo não informado"
        if diagnostic["line"] is not None:
            location += f":{diagnostic['line']}"
            if diagnostic["column"] is not None:
                location += f":{diagnostic['column']}"
        else:
            location += " (localização não disponível)"
        output.extend([
            f"[{stages.get(diagnostic['stage'], diagnostic['stage'])} / {diagnostic['code']}] {location}",
            f"  {diagnostic['message']}", f"  Sugestão: {diagnostic['suggestion']}",
        ])
    if not project.diagnostics:
        output.append("Nenhum erro encontrado.")
    else:
        output.append(f"Total: {len(project.diagnostics)} erro(s).")
    return "\n".join(output)
