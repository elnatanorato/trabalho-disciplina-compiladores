import ply.yacc as yacc
from compilador.lex import tokens  # Não remova esse import
import compilador.ast as ast
from dataclasses import dataclass, field
from compilador.lex import analyze as analyze_lexically, find_column
from ply.lex import LexToken

# Distingue o início de uma relação da cardinalidade opcional de um atributo.
# O adaptador de tokens abaixo usa apenas o próximo operador, não quebras de linha.
tokens = list(tokens) + ["RELATION_L_BRACKET"]


def _located(p, node, index=1):
    node.line = p.lineno(index)
    position = p.lexpos(index)
    node.column = position - max(
        p.lexer.lexdata.rfind("\n", 0, position),
        p.lexer.lexdata.rfind("\r", 0, position),
    )
    return node

# Utilizado para indicar a regra inicial.
start = "start"


# Regra inicial
def p_start(p):
    """
    start : list_instructions
    """

    p[0] = p[1]


# Regra que inicializa e adiciona as instrução para apenas uma única lista de instrução.
def p_list_instructions(p):
    """
    list_instructions : list_instructions instruction
                      | instruction
    """
    if len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = ast.ListInstructions(p[1])
    p.parser.last_tree = p[0]


# Regra que generaliza as instruções da linguagem.
def p_instruction(p):
    """
    instruction : decl_class
                | decl_type
                | decl_enum
                | package
                | import
                | decl_genset
                | relation_out
    """
    p[0] = p[1]


# Regra que agrupa as partes da instrução de declaração de classe.
def p_decl_class(p):
    """
    decl_class : decl_class1 ID_CLASS decl_class2
    """
    p[0] = _located(p, ast.DeclClass(p[1], p[2], p[3][0], p[3][1], p[3][2]), 2)


# Regra que generaliza os estereótipos de classes.
def p_decl_class1(p):
    """
    decl_class1 : EVENT
                | SITUATION
                | PROCESS
                | CATEGORY
                | MIXIN
                | PHASE_MIXIN
                | ROLE_MIXIN
                | HISTORICAL_ROLE_MIXIN
                | KIND
                | COLLECTIVE
                | QUANTITY
                | QUALITY
                | MODE
                | INTRINSIC_MODE
                | EXTRINSIC_MODE
                | SUBKIND
                | PHASE
                | ROLE
                | HISTORICAL_ROLE
                | RELATOR
    """
    p[0] = ast.Stereotype(p[1])


# Regra que abstrai os detalhes que o specializes é opcional.
def p_decl_class2(p):
    """
    decl_class2 : SPECIALIZES ID_CLASS decl_class3
                | decl_class3
    """
    if len(p) == 4:
        p[0] = (p[2], p[3][0], p[3][1])
    else:
        p[0] = (None, p[1][0], p[1][1])


# Regra que abstrai os detalhes das propriedades da declaração de classe.
def p_decl_class3(p):
    """
    decl_class3 : L_BRACE list_attributes R_BRACE
                | L_BRACE list_relations R_BRACE
                | L_BRACE list_attributes list_relations R_BRACE
                | empty
    """
    if len(p) == 4:
        if p[2][0] == "A":
            p[0] = (p[2][1], [])
        else:
            p[0] = ([], p[2][1])
    elif len(p) == 5:
        p[0] = (p[2][1], p[3][1])
    else:
        p[0] = ([], [])


# Regra que inicializa e adiciona os atributos em uma lista e inseri o A para identificação.
def p_list_attributes(p):
    """
    list_attributes : list_attributes attribute
                    | attribute
    """
    if len(p) == 3:
        p[0] = ("A", p[1][1] + [p[2]])
    else:
        p[0] = ("A", [p[1]])


# Regra que agrupar as parte de um atributo.
def p_attribute(p):
    """
    attribute : attribute1 attribute2 attribute3
    """
    p[0] = _located(p, ast.Attribute(p[1][0], p[1][1], p[2], p[3]))


# Regra que identifica o nome e tipo de atributo.
def p_attribute1(p):
    """
    attribute1 : ID_RELATION COLON type
    """
    p[0] = (p[1], p[3])


# Regra que trata se a cardinalidade existe.
def p_attribute2(p):
    """
    attribute2 : cardinality
               | empty
    """
    p[0] = p[1]


# Regra que extrai a lista de metas caso exista.
def p_attribute3(p):
    """
    attribute3 : L_BRACE list_metas R_BRACE
               | empty
    """
    if len(p) == 4:
        p[0] = p[2]


# Regra que extrai a cardinalidade.
def p_cardinality(p):
    """
    cardinality : L_BRACKET cardinality1 R_BRACKET
    """
    p[0] = p[2]


# Regra que abstrai os detalhes da cardinalidade que pode está em dois formatos diferentes.
def p_cardinality1(p):
    """
    cardinality1 : cardinality2
                 | NUMBER DOT_DOT cardinality2
    """
    if len(p) == 2:
        p[0] = ast.Cardinality(p[1], None)
    else:
        p[0] = ast.Cardinality(p[1], p[3])


# Regra que generaliza a cardinalidade para pode usar números ou *.
def p_cardinality2(p):
    """
    cardinality2 : NUMBER
                 | STAR
    """
    p[0] = p[1]


# Regra que inicializa e adiciona os meta atributos em uma lista.
def p_list_metas(p):
    """
    list_metas : list_metas COMMA meta
               | meta
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


# Regra que generaliza os metas atributos.
def p_meta(p):
    """
    meta : ORDERED_META
         | CONST_META
         | DERIVED_META
         | SUBSETS_META
         | REDEFINES_META
    """
    p[0] = ast.Meta(p[1])


# Regra que inicializa e adiciona as relações internas em uma lista e inseri o R para identificação.
def p_list_relations(p):
    """
    list_relations : list_relations relation_in
                   | relation_in
    """
    if len(p) == 3:
        p[0] = ("R", p[1][1] + [p[2]])
    else:
        p[0] = ("R", [p[1]])


# Regra que agrupar as partes da relação interna.
def p_relation_in(p):
    """
    relation_in : relation1 relation_cardinality relation2 cardinality ID_CLASS
    """
    p[0] = _located(p, ast.RelationIn(p[1], p[2], p[3], p[4], p[5]), 2)


# Regra que agrupar as partes da relação externa.
def p_relation_out(p):
    """
    relation_out : relation1 RELATION ID_CLASS relation_cardinality relation2 cardinality ID_CLASS
    """
    p[0] = _located(p, ast.RelationOut(p[1], p[3], p[4], p[5], p[6], p[7]), 2)


def p_relation_cardinality(p):
    """
    relation_cardinality : RELATION_L_BRACKET cardinality1 R_BRACKET
    """
    p[0] = p[2]


# Regra que trata se estereótipos de relação existe.
def p_relation1(p):
    """
    relation1 : AT_RELATION
              | empty
    """
    if p[1] is not None:
        p[0] = ast.AtRelation(p[1])


# Regra que abstrai os detalhe de existir dois tipos de relação.
def p_relation2(p):
    """
    relation2 : relation3 ID_RELATION relation3
              | relation3
    """
    if len(p) == 4:
        p[0] = ast.RelationType2(p[1], p[2], p[3])
    else:
        p[0] = ast.RelationType1(p[1])


# Regra que generaliza o operador de relação.
def p_relation3(p):
    """
    relation3 : L_AGGREGATION
              | R_AGGREGATION
              | MINUS_MINUS
    """
    p[0] = ast.RelationOperator(p[1])


# Regra que generaliza o tipo.
def p_type(p):
    """
    type : NUMBER_TYPE
         | STRING_TYPE
         | BOOLEAN_TYPE
         | DATE_TYPE
         | TIME_TYPE
         | DATETIME_TYPE
          | ID_CLASS
          | ID_TYPE
    """
    p[0] = p[1]


# Regra que agrupar as partes da instrução de declaração de tipo.
def p_decl_type(p):
    """
    decl_type : DATATYPE type_name decl_type1
    """
    p[0] = _located(p, ast.DeclType(p[2], p[3][0], p[3][1]), 2)


def p_type_name(p):
    """
    type_name : ID_CLASS
              | ID_TYPE
    """
    p[0] = p[1]


# Regra que abstrair os detalhes do specializes ser opcional.
def p_decl_type1(p):
    """
    decl_type1 : SPECIALIZES type decl_type2
               | decl_type2
    """
    if len(p) == 4:
        p[0] = (p[2], p[3])
    else:
        p[0] = (None, p[1])


# Regra que extrai a lista de atributos se existi.
def p_decl_type2(p):
    """
    decl_type2 : L_BRACE list_attributes R_BRACE
               | empty
    """
    if len(p) == 4:
        p[0] = p[2][1]
    else:
        p[0] = []


# Regra que agrupa as parte da instrução de declaração de enum.
def p_decl_enum(p):
    """
    decl_enum : ENUM ID_CLASS L_BRACE list_enum_itens R_BRACE
    """
    p[0] = _located(p, ast.DeclEnum(p[2], p[4]), 2)


# Regra que inicializa e adiciona as variantes do enum em um lista.
def p_list_enum_itens(p):
    """
    list_enum_itens : list_enum_itens COMMA ID_INSTANCE
                    | ID_INSTANCE
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


# Regra que trata a instrução de declaração de pacote.
def p_package(p):
    """
    package : PACKAGE ID_CLASS
    """
    p[0] = _located(p, ast.Package(p[2]), 2)


# Regra que trata a instrução de importação de pacote.
def p_import(p):
    """
    import : IMPORT ID_CLASS
    """
    p[0] = _located(p, ast.Import(p[2]), 2)


# Regra que agrupa as parte da instrução de declaração de conjunto.
def p_decl_genset(p):
    """
    decl_genset : decl_genset1 decl_genset2 GENSET ID_CLASS decl_genset3
    """
    p[0] = _located(p, ast.DeclGenset(p[1], p[2], p[4], p[5][0], p[5][1]), 4)


# Regra que verifica se disjoint existe.
def p_decl_genset1(p):
    """
    decl_genset1 : DISJOINT
                 | empty
    """
    p[0] = p[1] is not None


# Regra que verifica se complete existe.
def p_decl_genset2(p):
    """
    decl_genset2 : COMPLETE
                 | empty
    """
    p[0] = p[1] is not None


# Regra que abstrai os detalhes das duas forma de escrever o genset.
def p_decl_genset3(p):
    """
    decl_genset3 : WHERE list_id_class SPECIALIZES ID_CLASS
                 | L_BRACE GENERAL ID_CLASS SPECIFICS list_id_class R_BRACE
    """
    if len(p) == 5:
        p[0] = (p[4], p[2])
    else:
        p[0] = (p[3], p[5])


# Regra que inicializa e adiciona os nome de classes em uma lista.
def p_list_id_class(p):
    """
    list_id_class : list_id_class COMMA ID_CLASS
                  | ID_CLASS
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


# Regra vazia
def p_empty(p):
    """
    empty :
    """
    pass


# Regra de error genérico.
def p_error(p):
    replacement = None
    if p is None:
        source = getattr(parser, "source", "")
        normalized = source.replace("\r\n", "\n").replace("\r", "\n")
        line = normalized.count("\n") + 1
        column = len(normalized.rsplit("\n", 1)[-1]) + 1
        code = "unexpected_eof"
        message = "Fim de arquivo inesperado."
        suggestion = "Complete a declaração e verifique se faltam '}', ']' ou um nome."
    else:
        line, column = p.lineno, find_column(p.lexer.lexdata, p)
        code = "unexpected_token"
        message = f"Token {p.value!r} inesperado ({p.type})."
        expected = parser.action.get(parser.state, {})
        if "COLON" in expected:
            suggestion = "Verifique se falta ':' entre o nome e o tipo do atributo."
        elif "R_BRACKET" in expected:
            suggestion = "Verifique se falta ']' para fechar a cardinalidade."
        elif "ID_CLASS" in expected:
            suggestion = "Verifique se falta um nome de classe iniciado por maiúscula."
        else:
            suggestion = "Revise a declaração e os delimitadores próximos ao token indicado."
        declaration_starts = {s.name.upper() for s in ast.Stereotype} | {
            "PACKAGE", "IMPORT", "DATATYPE", "ENUM", "GENSET", "DISJOINT", "COMPLETE", "RELATION",
        }
        if (p.type in declaration_starts and "R_BRACE" in expected
                and isinstance(p.lexer, _TokenStream)
                and p.lexpos not in p.lexer.insertions):
            # O próximo início de declaração é preservado, não consumido.
            # A inserção é apenas recuperação; a fonte continua sendo inválida.
            p.lexer.insertions.add(p.lexpos)
            p.lexer.index -= 1
            replacement = LexToken()
            replacement.type, replacement.value = "R_BRACE", "}"
            replacement.lineno, replacement.lexpos = p.lineno, p.lexpos
            replacement.lexer = p.lexer
            suggestion = "Verifique se falta '}' antes desta nova declaração."
    if not hasattr(parser, "diagnostics"):
        parser.diagnostics = []
    parser.diagnostics.append({
        "stage": "syntax", "code": code, "file": getattr(parser, "filename", None),
        "line": line, "column": column, "message": message,
        "suggestion": suggestion,
    })
    if replacement is not None:
        parser.errok()
        return replacement


# Regra utilizado para não perder a ast anterior em caso de error
def p_list_instructions_error(p):
    """
    list_instructions : list_instructions error
    """
    p[0] = p[1]


def p_decl_class3_empty(p):
    "decl_class3 : L_BRACE R_BRACE"
    p[0] = ([], [])


def p_decl_type2_empty(p):
    "decl_type2 : L_BRACE R_BRACE"
    p[0] = []


def p_decl_class3_error(p):
    """
    decl_class3 : L_BRACE error R_BRACE
                | L_BRACE list_attributes error R_BRACE
                | L_BRACE list_relations error R_BRACE
                | L_BRACE list_attributes list_relations error R_BRACE
    """
    attributes, relations = [], []
    for value in p[2:-2]:
        if isinstance(value, tuple):
            if value[0] == "A":
                attributes = value[1]
            elif value[0] == "R":
                relations = value[1]
    p[0] = (attributes, relations)


def p_list_attributes_error(p):
    """
    list_attributes : list_attributes error attribute
                    | error attribute
    """
    previous = p[1][1] if len(p) == 4 else []
    p[0] = ("A", previous + [p[len(p) - 1]])


def p_list_relations_error(p):
    """
    list_relations : list_relations error relation_in
                   | error relation_in
    """
    previous = p[1][1] if len(p) == 4 else []
    p[0] = ("R", previous + [p[len(p) - 1]])


parser = yacc.yacc(debug=False, write_tables=False)


@dataclass
class ParseResult:
    tree: ast.ListInstructions | None
    diagnostics: list[dict] = field(default_factory=list)


class _TokenStream:
    def __init__(self, source, recognized):
        self.lexdata = source
        self.lexpos = 0
        self.lineno = 1
        self.items = recognized
        self.index = 0
        self.insertions = set()
        for index, token in enumerate(recognized):
            if token.type != "L_BRACKET":
                continue
            end = index + 1
            while end < len(recognized) and recognized[end].type in {"NUMBER", "STAR", "DOT_DOT"}:
                end += 1
            if (end + 1 < len(recognized) and recognized[end].type == "R_BRACKET"
                    and recognized[end + 1].type in {"MINUS_MINUS", "L_AGGREGATION", "R_AGGREGATION"}):
                token.type = "RELATION_L_BRACKET"

    def token(self):
        if self.index == len(self.items):
            return None
        token = self.items[self.index]
        self.index += 1
        self.lexpos, self.lineno = token.lexpos, token.lineno
        token.lexer = self
        return token


def parse_code(code, filename=None):
    """Analisa sem imprimir; mantém a AST parcial e os diagnósticos por arquivo.

    O parser PLY é reutilizado sequencialmente; esta API não é thread-safe.
    """
    analysis = analyze_lexically(code)
    diagnostics = [dict(
        stage="lexical", code="lexical_error", file=filename,
        line=error["line"], column=error["column"],
        message=error["message"], suggestion=error["suggestion"],
    ) for error in analysis["errors"]]
    parser.source, parser.filename, parser.diagnostics = code, filename, []
    parser.last_tree = None
    stream = _TokenStream(code, analysis["tokens"])
    tree = parser.parse(lexer=stream, tracking=True)
    if tree is None:
        tree = parser.last_tree
    diagnostics.extend(parser.diagnostics)
    return ParseResult(tree, diagnostics)
