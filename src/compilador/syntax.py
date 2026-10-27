import ply.yacc as yacc
from compilador.lex import tokens  # Não remova esse import
import compilador.ast as ast

start = "start"


def p_start(p):
    """
    start : list_instructions
    """
    p[0] = p[1]


def p_list_instructions(p):
    """
    list_instructions : list_instructions instruction
                      | instruction
    """
    if len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = ast.ListInstructions(p[1])


def p_instruction(p):
    """
    instruction : decl_class
                | decl_type
                | decl_enum
                | package
                | import
                | decl_genset
    """
    p[0] = p[1]


def p_decl_class(p):
    """
    decl_class : decl_class1 ID_CLASS decl_class2
    """
    p[0] = ast.DeclClass(p[1], p[2], p[3][0], p[3][1], p[3][2])


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


def p_decl_class2(p):
    """
    decl_class2 : SPECIALIZES ID_CLASS decl_class3
                | decl_class3
    """
    if len(p) == 4:
        p[0] = (p[2], p[3][0], p[3][1])
    else:
        p[0] = (None, p[1][0], p[1][1])


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


def p_list_attributes(p):
    """
    list_attributes : list_attributes attribute
                    | attribute
    """
    if len(p) == 3:
        p[0] = ("A", p[1][1] + [p[2]])
    else:
        p[0] = ("A", [p[1]])


def p_attribute(p):
    """
    attribute : attribute1 attribute2 attribute3
    """
    p[0] = ast.Attribute(p[1][0], p[1][1], p[2], p[3])


def p_attribute1(p):
    """
    attribute1 : ID_RELATION COLON type
    """
    p[0] = (p[1], p[3])


def p_attribute2(p):
    """
    attribute2 : cardinality
               | empty
    """
    p[0] = p[1]


def p_attribute3(p):
    """
    attribute3 : L_BRACE list_metas R_BRACE
               | empty
    """
    if len(p) == 4:
        p[0] = p[2]


def p_cardinality(p):
    """
    cardinality : L_BRACKET cardinality1 R_BRACKET
    """
    p[0] = p[2]


def p_cardinality1(p):
    """
    cardinality1 : cardinality2
                 | NUMBER DOT_DOT cardinality2
    """
    if len(p) == 2:
        p[0] = ast.Cardinality(p[1], None)
    else:
        p[0] = ast.Cardinality(p[1], p[3])


def p_cardinality2(p):
    """
    cardinality2 : NUMBER
                 | STAR
    """
    p[0] = p[1]


def p_list_metas(p):
    """
    list_metas : list_metas COMMA meta
               | meta
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


def p_meta(p):
    """
    meta : ORDERED_META
         | CONST_META
         | DERIVED_META
         | SUBSETS_META
         | REDEFINES_META
    """
    p[0] = ast.Meta(p[1])


def p_list_relations(p):
    """
    list_relations : list_relations relation
                   | relation
    """
    if len(p) == 3:
        p[0] = ("R", p[1][1] + [p[2]])
    else:
        p[0] = ("R", [p[1]])


def p_relation(p):
    """
    relation : relation1 relation2 relation3 cardinality relation4 cardinality ID_CLASS
    """
    p[0] = ast.Relation(p[1], p[2], p[3], p[4], p[5], p[6], p[7])


def p_relation1(p):
    """
    relation1 : AT_RELATION
              | empty
    """
    if p[1] is not None:
        p[0] = ast.AtRelation(p[1])


def p_relation2(p):
    """
    relation2 : RELATION
              | empty
    """
    p[0] = p[1] is not None


def p_relation3(p):
    """
    relation3 : ID_CLASS
              | empty
    """
    p[0] = p[1]


def p_relation4(p):
    """
    relation4 : relation5 ID_RELATION relation5
              | relation5
    """
    if len(p) == 4:
        p[0] = ast.RelationType2(p[1], p[2], p[3])
    else:
        p[0] = ast.RelationType1(p[1])


def p_relation5(p):
    """
    relation5 : L_AGGREGATION
              | R_AGGREGATION
              | MINUS_MINUS
    """
    p[0] = ast.RelationOperator(p[1])


def p_type(p):
    """
    type : NUMBER_TYPE
         | STRING_TYPE
         | BOOLEAN_TYPE
         | DATE_TYPE
         | TIME_TYPE
         | DATETIME_TYPE
         | ID_TYPE
    """
    p[0] = p[1]


def p_decl_type(p):
    """
    decl_type : DATATYPE ID_TYPE decl_type1
    """
    p[0] = ast.DeclType(p[2], p[3])


def p_decl_type1(p):
    """
    decl_type1 : L_BRACE list_attributes R_BRACE
               | empty
    """
    if len(p) == 4:
        p[0] = p[2][1]
    else:
        p[0] = []


def p_decl_enum(p):
    """
    decl_enum : ENUM ID_TYPE L_BRACE list_enum_itens COMMA ID_INSTANCE R_BRACE
    """
    p[0] = ast.DeclEnum(p[2], p[4] + [p[6]])


def p_list_enum_itens(p):
    """
    list_enum_itens : list_enum_itens COMMA ID_INSTANCE
                    | ID_INSTANCE
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


def p_package(p):
    """
    package : PACKAGE ID_CLASS
    """
    p[0] = ast.Package(p[2])


def p_import(p):
    """
    import : IMPORT PACKAGE
    """
    p[0] = ast.Import(p[2])


def p_decl_genset(p):
    """
    decl_genset : decl_genset1 decl_genset2 GENSET ID_CLASS decl_genset3
    """
    p[0] = ast.DeclGenset(p[1], p[2], p[4], p[5][0], p[5][1])


def p_decl_genset1(p):
    """
    decl_genset1 : DISJOINT
                 | empty
    """
    p[0] = p[1] is not None


def p_decl_genset2(p):
    """
    decl_genset2 : COMPLETE
                 | empty
    """
    p[0] = p[1] is not None


def p_decl_genset3(p):
    """
    decl_genset3 : WHERE list_id_class SPECIALIZES ID_CLASS
                 | L_BRACE GENERAL ID_CLASS SPECIFICS list_id_class R_BRACE
    """
    if len(p) == 5:
        p[0] = (p[4], p[2])
    else:
        p[0] = (p[3], p[5])


def p_list_id_class(p):
    """
    list_id_class : list_id_class COMMA ID_CLASS
                  | ID_CLASS
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


def p_empty(p):
    """
    empty :
    """
    pass


def p_error(p):
    print("Aconteceu um error: ", p)


# Usando para não perder a ast anterior em caso de error
def p_list_instructions_error(p):
    """
    list_instructions : list_instructions error
    """
    p[0] = p[1]


parser = yacc.yacc()


def parse_code(code):
    print(parser.parse(code))
