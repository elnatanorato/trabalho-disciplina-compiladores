import ply.lex as lex

reserved = {
    # Estereotipos de classes
    "event": "EVENT",
    "situation": "SITUATION",
    "process": "PROCESS",
    "category": "CATEGORY",
    "mixin": "MIXIN",
    "phaseMixin": "PHASE_MIXIN",
    "roleMixin": "ROLE_MIXIN",
    "historicalRoleMixin": "HISTORICAL_ROLE_MIXIN",
    "kind": "KIND",
    "collective": "COLLECTIVE",
    "quantity": "QUANTITY",
    "quality": "QUALITY",
    "mode": "MODE",
    "intrinsicMode": "INTRINSIC_MODE",
    "extrinsicMode": "EXTRINSIC_MODE",
    "subkind": "SUBKIND",
    "phase": "PHASE",
    "role": "ROLE",
    "historicalRole": "HISTORICAL_ROLE",
    # Palavras reservadas
    "genset": "GENSET",
    "disjoint": "DISJOINT",
    "complete": "COMPLETE",
    "general": "GENERAL",
    "specfics": "SPECIFICS",
    "where": "WHERE",
    "package": "PACKAGE",
    "import": "IMPORT",
    #  "functional-complexes": "FUNCITIONAL_COMPLEXES" Sua regra fica em outro lugar
    # Tipos
    "number": "NUMBER_TYPE",
    "string": "STRING_TYPE",
    "boolean": "BOOLEAN_TYPE",
    "date": "DATE_TYPE",
    "time": "TIME_TYPE",
    "datetime": "DATETIME_TYPE",
    "datatype": "DATATYPE",
    # Meta Atributos
    "ordered": "ORDERED_META",
    "const": "CONST_META",
    "derived": "DERIVED_META",
    "subsets": "SUBSETS_META",
    "redefines": "REDEFINES_META",
}

relation = (
    "material",
    "derivation",
    "comparative",
    "mediation",
    "characterization",
    "externalDependence",
    "componentOf",
    "memberOf",
    "subCollectionOf",
    "subQualityOf",
    "instantiation",
    "termination",
    "participational",
    "participation",
    "historicalDependence",
    "creation",
    "manifestation",
    "bringsAbout",
    "triggers",
    "composition",
    "aggregation",
    "inherence",
    "value",
    "formal",
    "constitution",
)

tokens = [
    # Simbolos especial
    "L_BRACE",
    "R_BRACE",
    "L_PAREN",
    "R_PAREN",
    "L_BRACKET",
    "R_BRACKET",
    "COMMA",
    "DOT_DOT",
    "L_AGGREGATION",
    "R_AGGREGATION",
    "STAR",
    "AT", # O PDF define "@" separadamente dos estereótipos de relação.
    "COLON",
    "MINUS_MINUS",
    # Nomes
    "ID_CLASS",
    "ID_RELATION",
    "ID_INSTANCE",
    "ID_TYPE",
    # Outros
    "RELATION",
    "NUMBER",
] + list(reserved.values())

t_L_BRACE = r"{"
t_R_BRACE = r"}"
t_L_PAREN = r"\("
t_R_PAREN = r"\)"
t_L_BRACKET = r"\["
t_R_BRACKET = r"\]"

t_COMMA = r","
t_DOT_DOT = r"\.\."
t_L_AGGREGATION = "<>--"
t_R_AGGREGATION = "--<>"
t_STAR = r"\*"
t_AT = r"@"
t_COLON = r":"
t_MINUS_MINUS = r"--"


def t_ID_CLASS(t):
    r"[A-Z][A-Za-z_]*"
    return t


def t_ID_RELATION(t):
    r"functional-complexes | [a-z][A-Za-z_]*"

    if t.value in relation:
        t.type = "RELATION"
    else:
        t.type = reserved.get(t.value, "ID_RELATION")

    return t


def t_ID_INSTANCE(t):
    r"[A-Za-z][A-Za-z_]*[0-9]+"
    return t


def t_ID_TYPE(t):
    r"[A-Za-z]+(Type)"
    return t


def t_NUMBER(t):
    r"[0-9]+"
    t.value = int(t.value)
    return t


def t_error(t):
    print(f"Error: Caractere {t.value[0]} é invalido")
    t.lexer.skip(1)


def t_newline(t):
    r"(?:\r\n|\r|\n)+"
    normalized_newlines = t.value.replace("\r\n", "\n").replace("\r", "\n")
    t.lexer.lineno += len(normalized_newlines)


t_ignore = " \t"
t_ignore_COMMENT = r"//.*"


def find_column(source, token):
    last_newline = max(
        source.rfind("\n", 0, token.lexpos),
        source.rfind("\r", 0, token.lexpos),
    )    
    return token.lexpos - last_newline


lexer = lex.lex()


def tokenize(source):
    lexer.lineno = 1
    lexer.input(source)

    tokens = []
    while True:
        token = lexer.token()
        if token is None:
            break

        token.column = find_column(source, token)
        tokens.append(token)

    return tokens
