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


def _location(diagnostic):
    location = diagnostic["file"] or "arquivo não informado"
    if diagnostic["line"] is not None:
        location += f":{diagnostic['line']}"
        if diagnostic["column"] is not None:
            location += f":{diagnostic['column']}"
    else:
        location += " (localização não disponível)"
    return location


def _semantic_sections(analysis):
    output = ["", "ANÁLISE SEMÂNTICA", "Verificações executadas:"]
    output.extend(f"- {coverage}" for coverage in analysis.final.coverage)
    if not analysis.recognizer_used:
        output.append("COBERTURA PARCIAL: reconhecedor dos seis ODPs ainda não conectado. Validar marcadores não certifica padrões completos.")
    for status, title in [("completo", "PADRÕES COMPLETOS"),
                          ("incompleto", "CANDIDATOS INCOMPLETOS / SOBRECARGAS"),
                          ("bloqueado", "CANDIDATOS BLOQUEADOS")]:
        output.extend(["", title])
        findings = [finding for finding in analysis.final.patterns if finding.status == status]
        if not findings:
            output.append("Nenhum resultado fornecido pelo reconhecedor para esta categoria.")
            continue
        output.append(_table(["Padrão", "Variante", "Contexto", "Pendências"], [
            [str(finding.pattern), finding.variant,
             f"{finding.subject.package}::{finding.subject.name}",
             finding.blocked or ", ".join(issue.code for issue in finding.missing) or "nenhuma"]
            for finding in findings
        ]))
    if analysis.final.blocked:
        output.extend(["", "VERIFICAÇÕES ADIADAS / FORA DO ESCOPO LOCAL"])
        output.extend(f"- {reason}" for reason in analysis.final.blocked)
    output.extend(["", "COERÇÕES APLICADAS"])
    if not analysis.corrections:
        output.append("Nenhuma. Dependências conceituais não são inventadas; pendências exigem revisão do modelo.")
    for correction in analysis.corrections:
        diagnostic = correction.diagnostic
        output.extend([
            f"[Corrigido em memória / {diagnostic['code']}] {_location(diagnostic)}",
            f"  {diagnostic['message']}",
            f"  {correction.field}: {correction.before} → {correction.after}",
        ])
    if analysis.corrections:
        output.append("Visão corrigida e revalidada em memória. O arquivo original continua inalterado; ajuste a fonte para persistir as correções.")
    return output


def render_report(project, *, semantic=None):
    """Com análise semântica, apresenta a cópia analisada e suas correções."""
    if semantic is not None:
        project = semantic.project
    diagnostics = list(project.diagnostics)
    if semantic is not None:
        diagnostics.extend(semantic.diagnostics)
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
    if summary["partial"] or (semantic is not None and semantic.diagnostics):
        output.append("\nATENÇÃO: análise com erros; a síntese pode estar incompleta e não inclui duplicatas rejeitadas.")
    if semantic is not None:
        output.extend(_semantic_sections(semantic))
    output.extend(["", "RELATÓRIO DE ERROS"])
    stages = {"lexical": "Léxico", "syntax": "Sintático", "symbols": "Símbolos",
              "packages": "Pacotes/arquivos", "resolution": "Resolução", "semantic": "Semântico"}
    for diagnostic in sorted(diagnostics, key=lambda d: (
        d["file"] or "", d["line"] or 0, d["column"] or 0, d["stage"], d["code"],
    )):
        location = _location(diagnostic)
        output.extend([
            f"[{stages.get(diagnostic['stage'], diagnostic['stage'])} / {diagnostic['code']}] {location}",
            f"  {diagnostic['message']}", f"  Sugestão: {diagnostic['suggestion']}",
        ])
    if not diagnostics:
        output.append("Nenhum erro encontrado." if semantic is None else
                      "Nenhum erro pendente nas verificações executadas. Consulte a cobertura indicada acima.")
    else:
        output.append(f"Total: {len(diagnostics)} erro(s) pendente(s)." if semantic is not None else
                      f"Total: {len(diagnostics)} erro(s).")
    return "\n".join(output)
