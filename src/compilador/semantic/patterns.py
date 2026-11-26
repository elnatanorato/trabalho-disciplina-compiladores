from typing import cast

from compilador import ast
from compilador.packages import Project
from compilador.symbols import Symbol


def subkind_role_phase_pattern(project: Project):
    for symbol in project.symbols.values():
        if symbol.category == "genset":
            node = cast(ast.DeclGenset, symbol.node)

            general = find_class(project, node.general)

            if general is None:
                continue

            general_node = cast(ast.DeclClass, general.node)

            if general_node.stereotype != ast.Stereotype.KIND:
                continue

            specifics = [find_class(project, s) for s in node.specifics]

            specifics_node = to_specifics_node(specifics)

            if len(specifics_node) == 0:
                print(f"{symbol.name} deve ter pelo menos um specifics")

            for s in specifics_node:
                if s.specializes != general_node.name:
                    print(f"{s.name} deve especializar o {general_node.name}")

            stereotype = specifics_sterotype(symbol.name, specifics_node)

            if (
                stereotype == ast.Stereotype.SUBKIND
                or stereotype == ast.Stereotype.PHASE
            ) and not node.is_disjoint:
                print(f"{node.name} o disjoint é obrigatorio nesse caso")

            if stereotype == ast.Stereotype.ROLE and node.is_disjoint:
                print(f"{node.name} o disjoint não é permitido nesse caso")

            if stereotype == ast.Stereotype.PHASE and len(specifics_node) <= 1:
                print(f"{node.name} quando é phase é necessario ter pelo menos 2")

        elif symbol.category == "class":
            node = cast(ast.DeclClass, symbol.node)
            stereotype = node.stereotype

            if (
                stereotype != ast.Stereotype.SUBKIND
                and stereotype != ast.Stereotype.ROLE
                and stereotype != ast.Stereotype.PHASE
            ):
                continue

            if node.specializes is None:
                print(f"{node.name} deve especializar um kind")
                continue

            specializes = find_class(project, node.specializes)

            if specializes is None:
                continue

            specializes_node = cast(ast.DeclClass, specializes.node)

            if node.name == specializes_node.name:
                print(f"{node.name} não pode ser auto especializar")

            if (
                specializes_node.stereotype != ast.Stereotype.KIND
                and specializes_node.stereotype != ast.Stereotype.SUBKIND
            ):
                print(f"{node.name} deve especializar um kind ou subkind")
                continue

            if (
                stereotype == ast.Stereotype.PHASE
                and len(get_phases(project, specializes_node.name)) <= 1
            ):
                print(f"{node.name} deve ter pelo menos uma irmã")


def find_class(project: Project, name: str):
    for symbol in project.symbols.values():
        if symbol.category == "class" and symbol.name == name:
            return symbol
    return None


def to_specifics_node(specifics: list[Symbol | None]):
    specifics_node: list[ast.DeclClass] = []
    for s in specifics:
        if s == None:
            continue
        specifics_node.append(cast(ast.DeclClass, s.node))
    return specifics_node


def get_phases(project: Project, specializes: str):
    phases = []
    for symbol in project.symbols.values():
        if symbol.category == "class":
            node = cast(ast.DeclClass, symbol.node)
            if (
                node.stereotype == ast.Stereotype.PHASE
                and node.specializes == specializes
            ):
                phases.append(symbol)
    return phases


def specifics_sterotype(genset_name: str, specifics: list[ast.DeclClass]):
    stereotype = specifics[0].stereotype
    for node in specifics:
        if node.stereotype != stereotype:
            print(f"{genset_name} no specifcs todos devem ser do mesmo tipo")
            return None
    return stereotype
