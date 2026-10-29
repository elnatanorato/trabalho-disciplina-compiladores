from dataclasses import dataclass
from enum import StrEnum
from typing import List, Literal
import pprint


class ListInstructions:
    def __init__(self, instruction: Instruction):
        self.instructions = [instruction]

    def __add__(self, other: Instruction):
        self.instructions.append(other)
        return self

    def __repr__(self):
        return "\n\n".join(pprint.pformat(i) for i in self.instructions)


@dataclass
class DeclClass:
    stereotype: Stereotype
    name: str
    specializes: None | str
    attributes: List[Attribute]
    relations: List[RelationIn]


class Stereotype(StrEnum):
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
    name: str
    type: str
    cardinality: Cardinality
    metas: List[Meta]


class Meta(StrEnum):
    ORDERED = "ordered"
    CONST = "const"
    DERIVED = "derived"
    SUBSETS = "subsets"
    REDEFINES = "redefines"


@dataclass
class RelationIn:
    at: AtRelation | None
    cardinality1: Cardinality
    type: RelationType1 | RelationType2
    cardinality2: Cardinality
    name: str


@dataclass
class RelationOut:
    at: AtRelation | None
    name1: str
    cardinality1: Cardinality
    type: RelationType1 | RelationType2
    cardinality2: Cardinality
    name2: str


class AtRelation(StrEnum):
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
    operator: RelationOperator


@dataclass
class RelationType2:
    operator1: RelationOperator
    name: str
    operator2: RelationOperator


class RelationOperator(StrEnum):
    L_AGGREGATION = "<>--"
    R_AGGREGATION = "--<>"
    MINUS_MINUS = "--"


@dataclass
class Cardinality:
    start: int | Literal["*"]
    end: int | Literal["*"] | None


@dataclass
class DeclType:
    name: str
    specializes: str
    attributes: List[Attribute]


@dataclass
class DeclEnum:
    name: str
    variances: List[str]


@dataclass
class Package:
    name: str


@dataclass
class Import:
    name: str


@dataclass
class DeclGenset:
    is_disjoint: bool
    is_complete: bool
    name: str
    general: str
    specifics: List[str]


Instruction = DeclClass | DeclType | DeclEnum | Package | Import | DeclGenset
