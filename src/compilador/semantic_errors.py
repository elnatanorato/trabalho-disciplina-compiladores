"""Diagnósticos e coerção semântica, independentes do reconhecedor de ODPs.

As verificações locais são parciais: validam somente marcadores de gensets.
Um reconhecedor externo pode fornecer padrões completos/incompletos pelo
contrato SemanticCheck, sem precisar imprimir ou alterar o projeto.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from compilador import ast
from compilador.symbols import Symbol

if TYPE_CHECKING:
    from compilador.packages import Project


class PatternKind(StrEnum):
    SUBKIND = "subkind"
    ROLE = "role"
    PHASE = "phase"
    RELATOR = "relator"
    MODE = "mode"
    ROLE_MIXIN = "roleMixin"


# Código estável → mensagem e orientação. Sem regras de reconhecimento aqui.
ISSUE_CATALOG = {
    "subkind_missing_kind": (
        "Subkind sem classe-mãe kind confirmada.",
        "Declare ou ajuste a especialização para uma classe kind, conforme o padrão adotado.",
    ),
    "role_missing_kind": (
        "Role sem classe-mãe kind confirmada.",
        "Declare ou ajuste a especialização para uma classe kind; não crie uma mãe arbitrária.",
    ),
    "phase_missing_kind": (
        "Phase sem classe-mãe kind confirmada.",
        "Associe a phase à classe kind que fornece sua identidade.",
    ),
    "phase_missing_sibling": (
        "Phase sem outra phase irmã confirmada.",
        "Modele pelo menos outra phase que especialize a mesma classe kind.",
    ),
    "relator_missing_mediations": (
        "Relator sem as duas mediações exigidas pelo padrão.",
        "Declare mediações com os participantes apropriados; os destinos não podem ser inventados pelo analisador.",
    ),
    "relator_missing_material": (
        "Relator sem relação material correspondente confirmada.",
        "Declare a relação @material entre os participantes mediados pelo relator.",
    ),
    "mode_missing_characterization": (
        "Mode sem relação characterization confirmada.",
        "Declare @characterization ligando o mode ao portador apropriado.",
    ),
    "mode_missing_external_dependence": (
        "Mode sem relação externalDependence confirmada.",
        "Declare @externalDependence com o destino apropriado ao modelo.",
    ),
    "rolemixin_missing_roles": (
        "RoleMixin sem os roles exigidos pelo padrão confirmados.",
        "Modele os roles que especializam o roleMixin e os respectivos kinds.",
    ),
    "rolemixin_same_kind": (
        "RoleMixin sem roles de kinds distintos confirmados.",
        "Revise os kinds de origem dos roles; não troque estereótipos apenas para eliminar o erro.",
    ),
    "genset_missing_disjoint": (
        "Genset de phases ou subkinds sem o marcador disjoint exigido no PDF.",
        "Adicione disjoint ao genset; a coerção opcional pode aplicar esse ajuste em memória.",
    ),
    "role_genset_disjoint": (
        "Genset de roles com disjoint, divergindo do modelo canônico do PDF.",
        "Segundo o critério desta tarefa, remova disjoint; confirme essa interpretação com o professor.",
    ),
}


@dataclass(frozen=True)
class SemanticIssue:
    code: str
    subject: Symbol
    details: str = ""

    def __post_init__(self):
        if self.code not in ISSUE_CATALOG:
            raise ValueError(f"Código semântico desconhecido: {self.code}")

    def diagnostic(self):
        message, suggestion = ISSUE_CATALOG[self.code]
        message = f"'{self.subject.package}::{self.subject.name}': {message}"
        if self.details:
            message += f" {self.details}"
        return {
            "stage": "semantic", "code": self.code, "file": self.subject.file,
            "line": self.subject.line, "column": self.subject.column,
            "message": message, "suggestion": suggestion,
        }


@dataclass(frozen=True)
class PatternFinding:
    """

    missing vazio significa completo segundo o reconhecedor, NÃO segundo este
    módulo. blocked distingue contexto inconclusivo de dependência ausente.
    variant identifica a alternativa/sobrecarga avaliada pelo reconhecedor.
    """

    pattern: PatternKind
    subject: Symbol
    missing: tuple[SemanticIssue, ...] = ()
    variant: str = "canônico"
    blocked: str = ""

    @property
    def status(self):
        if self.blocked:
            return "bloqueado"
        return "incompleto" if self.missing else "completo"


@dataclass(frozen=True)
class SemanticCheck:
    issues: tuple[SemanticIssue, ...] = ()
    patterns: tuple[PatternFinding, ...] = ()
    coverage: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()

    @property
    def diagnostics(self):
        # Um problema pode aparecer tanto na lista geral quanto numa sobrecarga.
        issues = [*self.issues, *(issue for finding in self.patterns if not finding.blocked
                                  for issue in finding.missing)]
        seen = set()
        result = []
        for issue in issues:
            key = (issue.code, issue.subject.key, issue.details)
            if key not in seen:
                seen.add(key)
                result.append(issue.diagnostic())
        return result


@dataclass(frozen=True)
class AppliedCoercion:
    symbol_key: tuple
    diagnostic: dict
    before: bool
    after: bool
    field: str = "is_disjoint"


@dataclass(frozen=True)
class SemanticAnalysis:
    project: Project
    initial: SemanticCheck
    final: SemanticCheck
    corrections: tuple[AppliedCoercion, ...] = ()
    recognizer_used: bool = False

    @property
    def diagnostics(self):
        return self.final.diagnostics


def _genset_context(project, symbol):
    """Só aceita referências resolvidas, específicas distintas e herança direta.

    Não faz resolução alternativa por nome: evita misturar classes homônimas
    de pacotes diferentes ou ignorar imports ambíguos.
    """
    node = symbol.node
    references = {r.field: r.target for r in project.references if r.source is symbol}
    general = references.get("general")
    specifics = [references.get(f"specifics[{index}]") for index in range(len(node.specifics))]
    if (general is None or len(specifics) < 2 or any(s is None for s in specifics)
            or len({s.key for s in specifics}) != len(specifics)
            or general.category != "class"
            or general.node.stereotype != ast.Stereotype.KIND):
        return None
    stereotypes = {s.node.stereotype for s in specifics if s.category == "class"}
    if len(stereotypes) != 1 or any(s.category != "class" for s in specifics):
        return None
    for specific in specifics:
        parents = [r for r in project.references
                   if r.source is specific and (r.field == "specializes" or r.field.startswith("specializes["))]
        if not any(reference.target is general for reference in parents):
            return None
    return stereotypes.pop()


def check_genset_flags(project):
    """Verificação parcial de marcadores; não certifica um ODP completo."""
    coverage = ("Marcadores de gensets homogêneos de phase, subkind e role",)
    if project.diagnostics:
        return SemanticCheck(coverage=coverage, blocked=(
            "Verificação local adiada: existem erros das etapas anteriores; não se presume uma AST completa.",
        ))
    issues = []
    blocked = []
    for symbol in project.symbols.values():
        if symbol.category != "genset":
            continue
        stereotype = _genset_context(project, symbol)
        if stereotype is None:
            blocked.append(f"{symbol.package}::{symbol.name}: fora do escopo local ou contexto insuficiente; sem coerção.")
            continue
        if stereotype in {ast.Stereotype.PHASE, ast.Stereotype.SUBKIND} and not symbol.node.is_disjoint:
            issues.append(SemanticIssue("genset_missing_disjoint", symbol))
        elif stereotype == ast.Stereotype.ROLE and symbol.node.is_disjoint:
            issues.append(SemanticIssue("role_genset_disjoint", symbol))
    return SemanticCheck(issues=tuple(issues), coverage=coverage, blocked=tuple(blocked))


def analyze_semantics(
    project: Project,
    *,
    coerce: bool = False,
    recognizer: Callable[[Project], SemanticCheck] | None = None,
):
    """Executa verificações e, opcionalmente, coerções limitadas e auditáveis.

    Trabalha numa cópia integral: AST, símbolos e referências continuam ligados
    entre si, mas o projeto de entrada e os arquivos originais são preservados.
    O reconhecedor deve ser puro e é executado novamente depois das coerções.
    """
    working = deepcopy(project)

    def evaluate():
        local = check_genset_flags(working)
        if recognizer is None:
            return local
        external = recognizer(working)
        if not isinstance(external, SemanticCheck):
            raise TypeError("O reconhecedor deve retornar SemanticCheck.")
        return SemanticCheck(
            issues=local.issues + external.issues,
            patterns=local.patterns + external.patterns,
            coverage=tuple(dict.fromkeys(local.coverage + external.coverage)),
            blocked=local.blocked + external.blocked,
        )

    initial = evaluate()
    corrections = []
    if coerce:
        # Não aceita ações arbitrárias sugeridas por reconhecedores externos.
        # Só as duas operações verificadas pelo adaptador local são executadas.
        for issue in check_genset_flags(working).issues:
            node = issue.subject.node
            after = issue.code == "genset_missing_disjoint"
            corrections.append(AppliedCoercion(
                issue.subject.key, issue.diagnostic(), node.is_disjoint, after,
            ))
            node.is_disjoint = after
    final = evaluate() if corrections else initial
    return SemanticAnalysis(working, initial, final, tuple(corrections), recognizer is not None)
