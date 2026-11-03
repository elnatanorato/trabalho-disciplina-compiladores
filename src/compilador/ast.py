from dataclasses import dataclass
from enum import StrEnum
from typing import List, Literal
import pprint


class ListInstructions:
    """
    Uma lista com todas as instruções que são reconhecidas por esse compilador.
    Ela receber a primeira instrução na inicialização e novas pode ser adicionando
    somando uma instancia dessa classe com uma `Instruction`.
    """

    def __init__(self, instruction: Instruction):
        self.instructions = [instruction]

    def __add__(self, other: Instruction):
        self.instructions.append(other)
        return self

    def __repr__(self):
        return "\n\n".join(pprint.pformat(i) for i in self.instructions)


@dataclass
class DeclClass:
    """
    Instrução de declaração de classe.
    """

    stereotype: Stereotype
    name: str
    specializes: None | str
    attributes: List[Attribute]
    relations: List[RelationIn]


class Stereotype(StrEnum):
    """
    Enum de estereótipos de classes.
    """

    EVENT = "event"
    SITUATION = "situation"
    PROCESS = "process"
    CATEGORY = "category"
    MIXIN = "mixin"
    PHASE_MIXIN = "phaseMixin"
    ROLE_MIXIN = "roleMixin"
    HISTORICAL_ROLE_MIXIN = "historicalRoleMixin"
    KIND = "kind"
    COLLECTIVE = "collective"
    QUANTITY = "quantity"
    QUALITY = "quality"
    MODE = "mode"
    INTRINSIC_MODE = "intrinsicMode"
    EXTRINSIC_MODE = "extrinsicMode"
    SUBKIND = "subkind"
    PHASE = "phase"
    ROLE = "role"
    HISTORICAL_ROLE = "historicalRole"
    RELATOR = "relator"


@dataclass
class Attribute:
    """
    Parte de algumas instrução, representar um atributo com suas propriedades.
    """

    name: str
    type: str
    cardinality: Cardinality
    metas: List[Meta]


class Meta(StrEnum):
    """
    Enum de meta atributos
    """

    ORDERED = "ordered"
    CONST = "const"
    DERIVED = "derived"
    SUBSETS = "subsets"
    REDEFINES = "redefines"


@dataclass
class RelationIn:
    """
    Parte de algumas instrução, representar um relação interna com suas propriedades.
    """

    at: AtRelation | None
    cardinality1: Cardinality
    type: RelationType1 | RelationType2
    cardinality2: Cardinality
    name: str


@dataclass
class RelationOut:
    """
    Instrução de declaração de relação, como uma relação externa não faz parte de outras instruções.
    """

    at: AtRelation | None
    name1: str
    cardinality1: Cardinality
    type: RelationType1 | RelationType2
    cardinality2: Cardinality
    name2: str


class AtRelation(StrEnum):
    """
    Enum de estereótipos de relação.
    """

    MATERIAL = "@material"
    DERIVATION = "@derivation"
    COMPARATIVE = "@comparative"
    MEDIATION = "@mediation"
    CHARACTERIZATION = "@characterization"
    EXTERNAL_DEPENDENCE = "@externalDependence"
    COMPONENT_OF = "@componentOf"
    MEMBER_OF = "@memberOf"
    SUB_COLLECTION_OF = "@subCollectionOf"
    SUB_QUALITY_OF = "@subQualityOf"
    INSTANTIATION = "@instantiation"
    TERMINATION = "@termination"
    PARTICIPATIONAL = "@participational"
    PARTICIPATION = "@participation"
    HISTORICAL_DEPENDENCE = "@historicalDependence"
    CREATION = "@creation"
    MANIFESTATION = "@manifestation"
    BRINGS_ABOUT = "@bringsAbout"
    TRIGGERS = "@triggers"
    COMPOSITION = "@composition"
    AGGREGATION = "@aggregation"
    INHERENCE = "@inherence"
    VALUE = "@value"
    FORMAL = "@formal"
    CONSTITUTION = "@constitution"


@dataclass
class RelationType1:
    """
    Parte de uma instrução, representar uma relação com apenas um único operador.
    """

    operator: RelationOperator


@dataclass
class RelationType2:
    """
    Parte de uma instrução, representar uma relação com apenas dois operadores e um nome.
    """

    operator1: RelationOperator
    name: str
    operator2: RelationOperator


class RelationOperator(StrEnum):
    """
    Enum de operador de relação
    """

    L_AGGREGATION = "<>--"
    R_AGGREGATION = "--<>"
    MINUS_MINUS = "--"


@dataclass
class Cardinality:
    """
    Parte de uma instrução, representar a cardinalidade com o `end` sendo opcional para que as duas formas possam ser representadas.
    """

    start: int | Literal["*"]
    end: int | Literal["*"] | None


@dataclass
class DeclType:
    """
    Instrução de declaração de tipo.
    """

    name: str
    specializes: str
    attributes: List[Attribute]


@dataclass
class DeclEnum:
    """
    Instrução de declaração de enum.
    """

    name: str
    variances: List[str]


@dataclass
class Package:
    """
    Instrução de declaração de pacote.
    """

    name: str


@dataclass
class Import:
    """
    Instrução de importação de pacote.
    """

    name: str


@dataclass
class DeclGenset:
    """
    Instrução de declaração de conjunto.
    """

    is_disjoint: bool
    is_complete: bool
    name: str
    general: str
    specifics: List[str]


# Tipo que agrupar todas as instrução em um único nome
Instruction = DeclClass | DeclType | DeclEnum | Package | Import | DeclGenset
