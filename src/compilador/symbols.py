from __future__ import annotations

from dataclasses import dataclass

from compilador import ast


BASIC_TYPES = frozenset({"number", "string", "boolean", "date", "time", "datetime"})
TYPE_CATEGORIES = frozenset({"class", "datatype", "enum"})
DEFAULT_PACKAGE = "<default>"


@dataclass
class Symbol:
    name: str
    category: str
    package: str
    node: object
    file: str | None
    owner: str | None = None
    line: int | None = None
    column: int | None = None
    anonymous: bool = False

    @property
    def key(self):
        return (self.package, self.owner, self.category, self.name)


@dataclass
class Reference:
    name: str
    source: Symbol
    field: str
    expected_categories: frozenset[str]
    node: object
    file: str | None
    line: int | None = None
    column: int | None = None
    allow_basic: bool = False
    target: Symbol | None = None
    basic_type: str | None = None


def _position(node):
    line = getattr(node, "line", None)
    if line is None:
        line = getattr(node, "lineno", None)
    return line, getattr(node, "column", None)


def _namespace(category, owner):
    # A categoria na chave não pode esconder conflitos no mesmo espaço de nomes.
    if category in TYPE_CATEGORIES:
        return "type"
    if category in {"attribute", "enum_value"} or (
        category == "relation" and owner is not None
    ):
        return "member"
    return category


class SymbolTable:
    def __init__(self):
        self.symbols: dict[tuple, Symbol] = {}
        self.packages: dict[str, Symbol] = {}
        self.imports: dict[str, list[Reference]] = {}
        self.references: list[Reference] = []
        self.diagnostics: list[dict] = []
        self._by_name: dict[tuple, list[Symbol]] = {}
        self._anonymous_relations = 0

    def add_diagnostic(
        self, code, message, suggestion, *, file=None, node=None,
        line=None, column=None, stage="symbols"
    ):
        node_line, node_column = _position(node)
        self.diagnostics.append({
            "stage": stage,
            "code": code,
            "file": file,
            "line": line if line is not None else node_line,
            "column": column if column is not None else node_column,
            "message": message,
            "suggestion": suggestion,
        })

    def add_symbol(
        self, name, category, package, node=None, file=None, owner=None,
        anonymous=False
    ):
        scope_key = (package, owner, name)
        namespace = _namespace(category, owner)
        for previous in self._by_name.get(scope_key, []):
            if _namespace(previous.category, previous.owner) == namespace:
                self.add_diagnostic(
                    "duplicate_declaration",
                    f"Declaração duplicada de '{name}' no escopo "
                    f"'{package}'" + (f" de '{owner}'." if owner else "."),
                    "Renomeie ou remova a declaração repetida. "
                    f"A primeira declaração está em {previous.file or 'memória'}.",
                    file=file, node=node,
                )
                return None

        line, column = _position(node)
        symbol = Symbol(
            name, category, package, node, file, owner, line, column, anonymous
        )
        self.symbols[symbol.key] = symbol
        self._by_name.setdefault(scope_key, []).append(symbol)
        if category == "package":
            self.packages[name] = symbol
            self.imports[name] = []
        return symbol

    def lookup(self, name, package, owner=None, category=None):
        matches = self._by_name.get((package, owner, name), [])
        return [s for s in matches if category is None or s.category == category]

    def symbols_in_package(self, package, category=None):
        return [
            s for s in self.symbols.values()
            if s.package == package and (category is None or s.category == category)
        ]

    def members(self, package, owner, category=None):
        return [
            s for s in self.symbols_in_package(package, category)
            if s.owner == owner
        ]

    def relations(self, package=None, external=None):
        return [
            s for s in self.symbols.values()
            if s.category == "relation"
            and (package is None or s.package == package)
            and (external is None or (s.owner is None) == external)
        ]

    def add_reference(
        self, source, name, field, expected_categories, *, node=None,
        file=None, allow_basic=False
    ):
        if node is None:
            node = source.node
        line, column = _position(node)
        reference = Reference(
            name, source, field, frozenset(expected_categories), node,
            source.file if file is None else file, line, column, allow_basic,
        )
        self.references.append(reference)
        if field == "import":
            self.imports.setdefault(source.package, []).append(reference)
        return reference

    def register_ast(self, tree, file=None):
        instructions = tree.instructions if isinstance(tree, ast.ListInstructions) else list(tree)
        declarations = [n for n in instructions if isinstance(n, ast.Package)]
        if len(declarations) > 1:
            self.add_diagnostic(
                "multiple_packages",
                "Este processamento aceita apenas um pacote por arquivo.",
                "Separe as declarações de pacote em arquivos diferentes.",
                file=file, node=declarations[1], stage="packages",
            )
            return None

        package_node = declarations[0] if declarations else None
        package_name = package_node.name if package_node else DEFAULT_PACKAGE
        package = self.packages.get(package_name)
        if package is not None and package_node is not None:
            self.add_diagnostic(
                "duplicate_package",
                f"O pacote '{package_name}' já foi declarado em '{package.file}'.",
                "Use nomes distintos para os pacotes de cada arquivo.",
                file=file, node=package_node, stage="packages",
            )
            return None
        if package is None:
            package = self.add_symbol(
                package_name, "package", package_name, package_node,
                file if package_node else None,
            )

        # O pacote do arquivo inteiro é conhecido antes de tratar os imports.
        for node in instructions:
            if isinstance(node, ast.Package):
                continue
            if isinstance(node, ast.Import):
                self.add_reference(
                    package, node.name, "import", {"package"}, node=node, file=file
                )
            elif isinstance(node, (ast.DeclClass, ast.DeclType)):
                category = "class" if isinstance(node, ast.DeclClass) else "datatype"
                symbol = self.add_symbol(node.name, category, package_name, node, file)
                if symbol is None:
                    continue
                if node.specializes is not None:
                    self.add_reference(
                        symbol, node.specializes, "specializes",
                        {"class"} if category == "class" else TYPE_CATEGORIES,
                        allow_basic=category == "datatype",
                    )
                for attribute in node.attributes:
                    member = self.add_symbol(
                        attribute.name, "attribute", package_name, attribute,
                        file, owner=node.name,
                    )
                    if member is not None:
                        self.add_reference(
                            member, attribute.type, "type", TYPE_CATEGORIES,
                            allow_basic=True,
                        )
                if isinstance(node, ast.DeclClass):
                    for relation in node.relations:
                        self._register_relation(relation, package_name, file, node.name)
            elif isinstance(node, ast.DeclEnum):
                symbol = self.add_symbol(node.name, "enum", package_name, node, file)
                if symbol is not None:
                    for value in node.variances:
                        self.add_symbol(
                            value, "enum_value", package_name, value,
                            file, owner=node.name,
                        )
            elif isinstance(node, ast.RelationOut):
                self._register_relation(node, package_name, file)
            elif isinstance(node, ast.DeclGenset):
                symbol = self.add_symbol(node.name, "genset", package_name, node, file)
                if symbol is not None:
                    self.add_reference(symbol, node.general, "general", {"class"})
                    for index, name in enumerate(node.specifics):
                        self.add_reference(symbol, name, f"specifics[{index}]", {"class"})
        return package

    def _register_relation(self, node, package, file, owner=None):
        anonymous = isinstance(node.type, ast.RelationType1)
        if anonymous:
            self._anonymous_relations += 1
            name = f"<relation:{self._anonymous_relations}>"
        else:
            name = node.type.name
        symbol = self.add_symbol(
            name, "relation", package, node, file, owner, anonymous
        )
        if symbol is None:
            return
        if isinstance(node, ast.RelationOut):
            self.add_reference(symbol, node.name1, "source", {"class"})
            self.add_reference(symbol, node.name2, "target", {"class"})
        else:
            # RelationIn.name é o destino; o nome da relação pertence a node.type.
            self.add_reference(symbol, node.name, "target", {"class"})

    def resolve(self):
        # Permite repetir a resolução depois de registrar novos arquivos.
        self.diagnostics[:] = [d for d in self.diagnostics if d["stage"] != "resolution"]
        for reference in self.references:
            reference.target = None
            reference.basic_type = None

        for imports in self.imports.values():
            for reference in imports:
                reference.target = self.packages.get(reference.name)
                if reference.target is None:
                    self._reference_error(
                        reference, "missing_import",
                        f"Pacote importado '{reference.name}' não encontrado.",
                        "Inclua o arquivo desse pacote no projeto ou corrija o import.",
                    )

        for reference in self.references:
            if reference.field != "import":
                self._resolve_reference(reference)
        return self

    def _resolve_reference(self, reference):
        if reference.allow_basic and reference.name in BASIC_TYPES:
            reference.basic_type = reference.name
            return

        package = reference.source.package
        local = self.lookup(reference.name, package)
        candidates = [s for s in local if s.category in TYPE_CATEGORIES]
        imported = []
        visited = set()
        for dependency in self.imports.get(package, []):
            target = dependency.target
            if target is not None and target.name not in visited:
                visited.add(target.name)
                imported.extend(self.lookup(reference.name, target.name))
        if not candidates:
            candidates = [s for s in imported if s.category in TYPE_CATEGORIES]
        if not candidates:
            candidates = local or imported

        compatible = [s for s in candidates if s.category in reference.expected_categories]
        if len(compatible) == 1:
            reference.target = compatible[0]
        elif len(compatible) > 1:
            packages = ", ".join(sorted({s.package for s in compatible}))
            self._reference_error(
                reference, "ambiguous_reference",
                f"Referência '{reference.name}' ambígua entre os pacotes: {packages}.",
                "Renomeie as declarações conflitantes ou remova um dos imports.",
            )
        elif candidates or reference.name in BASIC_TYPES:
            expected = ", ".join(sorted(reference.expected_categories))
            self._reference_error(
                reference, "incompatible_category",
                f"'{reference.name}' não possui a categoria esperada: {expected}.",
                "Utilize uma declaração da categoria adequada para essa referência.",
            )
        else:
            self._reference_error(
                reference, "unresolved_reference",
                f"Referência '{reference.name}' não encontrada no pacote '{package}' "
                "nem nos imports diretos.",
                "Declare o nome, corrija sua grafia ou importe o pacote que o declara.",
            )

    def _reference_error(self, reference, code, message, suggestion):
        self.add_diagnostic(
            code, message, suggestion, file=reference.file,
            line=reference.line, column=reference.column, stage="resolution",
        )
