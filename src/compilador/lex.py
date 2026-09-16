import ply.lex as lex


# Dicionário contendo as palavras reservadas e estereótipos de classe da linguagem TONTO.
# Mapeia o texto exato para o nome do token em maiúsculo.
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
    "functional-complexes": "FUNCTIONAL_COMPLEXES",
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


# Tupla com os estereótipos de relação válidos na linguagem TONTO.
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

# Lista obrigatória do PLY que junta todos os tokens que o analisador deve ser capaz de reconhecer.
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


# Definição de regras simples usando expressões regulares diretas para símbolos especiais.
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
t_COLON = r":"
t_MINUS_MINUS = r"--"

# Identifica estereótipos de relação: devem começar com '@' e conter
# um nome presente na lista de relações válidas.
def t_RELATION(t):
    r"@[A-Za-z0-9_]*"

    relation_name = t.value[1:]

    if relation_name in relation:
        return t

    t.lexer.errors.append(
        {
            "lexeme": t.value,
            "line": t.lineno,
            "column": find_column(t.lexer.lexdata, t),
            "message": f"Lexema '{t.value}' não reconhecido.",
            "suggestion": "Utilize um estereótipo de relação válido.",
        }
    )

    return None

# Regra para identificar instâncias: devem começar com letra e terminar com número.
def t_ID_INSTANCE(t):
    r"[A-Za-z][A-Za-z_]*[0-9]+"
    return t

# Regra para identificar tipos de dados: devem terminar com a string DataType.
def t_ID_TYPE(t):
    r"[A-Za-z]+DataType(?![A-Za-z0-9_])"
    return t

# Regra para identificar classes: começam obrigatoriamente com letra maiúscula.
def t_ID_CLASS(t):
    r"[A-Z][A-Za-z_]*"
    return t

# Regra para relações ou palavras reservadas: começam com letra minúscula.
# Verifica se o texto capturado é uma relação (na lista relation) ou palavra reservada.
def t_ID_RELATION(t):
    r"functional-complexes|[a-z][A-Za-z_]*"

    t.type = reserved.get(t.value, "ID_RELATION")
    return t


# Regra para capturar números inteiros e convertê-los de string para int.
def t_NUMBER(t):
    r"[0-9]+"
    t.lexeme = t.value
    t.value = int(t.value)
    return t


# Função chamada quando o analisador encontra um caractere que não bate com nenhuma regra.
# Registra as informações do erro (linha, coluna, caractere) e pula para continuar a análise.
def t_error(t):
    invalid_character = t.value[0]

    error = {
        "lexeme": invalid_character,
        "line": t.lineno,
        "column": find_column(t.lexer.lexdata, t),
        "message": f"Caractere '{invalid_character}' não reconhecido.",
        "suggestion": (
            "Remova o caractere ou substitua-o por um símbolo válido da TONTO."
        ),
    }

    t.lexer.errors.append(error)
    t.lexer.skip(1)


# Atualiza o contador de linhas, tratando diferenças de quebra de linha.
def t_newline(t):
    r"(?:\r\n|\r|\n)+"
    normalized_newlines = t.value.replace("\r\n", "\n").replace("\r", "\n")
    t.lexer.lineno += len(normalized_newlines)


# Ignora espaços em branco, tabulações e comentários iniciados por //.
t_ignore = " \t"
t_ignore_COMMENT = r"//.*"


# Calcula a coluna exata do token subtraindo a posição da última quebra de linha.
def find_column(source, token):
    last_newline = max(
        source.rfind("\n", 0, token.lexpos),
        source.rfind("\r", 0, token.lexpos),
    )
    return token.lexpos - last_newline


# Inicializa o analisador léxico do PLY.
lexer = lex.lex()


# Função principal que injeta o código-fonte no analisador, percorre todos os tokens
# e retorna um dicionário contendo os tokens reconhecidos e a lista de erros capturados.
def analyze(source):
    lexer.lineno = 1
    lexer.errors = []
    lexer.input(source)

    recognized_tokens = []

    while True:
        token = lexer.token()

        if token is None:
            break

        if not hasattr(token, "lexeme"):
            token.lexeme = token.value

        token.column = find_column(source, token)
        recognized_tokens.append(token)

    return {
        "tokens": recognized_tokens,
        "errors": list(lexer.errors),
    }


# Atalho que chama a função analyze e retorna apenas a lista de tokens.
def tokenize(source):
    return analyze(source)["tokens"]
