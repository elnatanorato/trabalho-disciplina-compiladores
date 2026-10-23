# Documento para ajudar a desenvolver a gramatica

## Observação
 - O `empty` significar o vazio 

## Estereótipos de classes
```
decl_class : decl_class1 ID_CLASS decl_class2

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

decl_class2 : SPECIALIZES ID_CLASS
            | L_BRACE list_attributes R_BRACE
            | L_BRACE list_relations R_BRACE
            | L_BRACE list_attributes list_relations R_BRACE
            | empty
```

## Atributos
```
list_attributes : list_attributes attribute
                | attribute

attribute : attribute1 attribute2 attribute3

attribute1 : ID_RELATION COLON type

attribute2 : cardinality 
           | empty

attribute3 : meta 
           | empty

cardinality : L_BRACKET cardinality1 R_BRACKET

cardinality1 : cardinality2
             | NUMBER DOT_DOT cardinality2

cardinality2 : NUMBER
             | STAR

meta : L_BRACE meta1 R_BRACE

meta1 : ORDERED_META
      | CONST_META
      | DERIVED_META
      | SUBSETS_META
      | REDEFINES_META
```

## Relações
```
list_relations : list_relations relation
               | relation

relation : relation1 relation2 relation3 cardinality relation5 cardinality ID_CLASS

relation1 : AT_RELATION
          | empty

relation2 : RELATION
          | empty

relation3 : ID_CLASS
          | empty

relation4 : relation5 ID_RELATION relation5
          | relation5

relation5 : L_AGGREGATION
          | R_AGGREGATION
          | MINUS_MINUS
```

## Tipos

```
type : NUMBER_TYPE
     | STRING_TYPE
     | BOOLEAN_TYPE
     | DATE_TYPE
     | TIME_TYPE
     | DATETIME_TYPE
     | ID_TYPE

decl_type : DATATYPE ID_TYPE decl_type1

decl_type1 : L_BRACE list_attributes R_BRACE
           | empty

decl_enum : ENUM ID_TYPE L_BRACE list_enum_itens COMMA enum_item R_BRACE

list_enum_itens : list_enum_itens COMMA enum_item
                | enum_item


```
