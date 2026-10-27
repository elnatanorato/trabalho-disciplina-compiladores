# Documento para ajudar a desenvolver a gramatica

## Observação
 - O `empty` significar o vazio 

## Primeiro token
```
start : list_instructions

list_instructions : list_instructions instruction
                  | instruction

instruction : decl_class
            | decl_type
            | decl_enum
            | package
            | import
            | decl_genset
```

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
            | RELATOR

decl_class2 : SPECIALIZES ID_CLASS decl_class3
            | decl_class3
            

decl_class3 : L_BRACE list_attributes R_BRACE
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

attribute3 : L_BRACE list_metas R_BRACE
           | empty

cardinality : L_BRACKET cardinality1 R_BRACKET

cardinality1 : cardinality2
             | NUMBER DOT_DOT cardinality2

cardinality2 : NUMBER
             | STAR

list_metas : list_metas COMMA meta
           | meta

meta : ORDERED_META
      | CONST_META
      | DERIVED_META
      | SUBSETS_META
      | REDEFINES_META
```

## Relações
```
list_relations : list_relations relation
               | relation

relation : relation1 relation2 relation3 cardinality relation4 cardinality ID_CLASS

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

decl_enum : ENUM ID_TYPE L_BRACE list_enum_itens COMMA ID_INSTANCE R_BRACE

list_enum_itens : list_enum_itens COMMA ID_INSTANCE
                | ID_INSTANCE
```

## Package e import
```
package : PACKAGE ID_CLASS

import : IMPORT PACKAGE
```


## Conjuntos
```
decl_genset : decl_genset1 decl_genset2 GENSET ID_CLASS decl_genset3

decl_genset1 : DISJOINT
             | empty

decl_genset2 : COMPLETE
             | empty

decl_genset3 : WHERE list_id_class SPECIALIZES ID_CLASS
             | L_BRACE GENERAL ID_CLASS SPECIFICS list_id_class R_BRACE

list_id_class : list_id_class COMMA ID_CLASS
              | ID_CLASS
```