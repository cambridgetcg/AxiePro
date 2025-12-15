"""Type definitions for Axie data structures."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class AxieClass(str, Enum):
    """Axie class types."""
    BEAST = "beast"
    BUG = "bug"
    BIRD = "bird"
    PLANT = "plant"
    AQUATIC = "aquatic"
    REPTILE = "reptile"
    MECH = "mech"
    DAWN = "dawn"
    DUSK = "dusk"


class PartType(str, Enum):
    """Body part types."""
    EYES = "eyes"
    EARS = "ears"
    MOUTH = "mouth"
    HORN = "horn"
    BACK = "back"
    TAIL = "tail"


class GeneType(str, Enum):
    """Gene inheritance types."""
    D = "d"      # Dominant
    R1 = "r1"    # Recessive 1
    R2 = "r2"    # Recessive 2


class Part(BaseModel):
    """Represents a body part."""
    part_id: str
    name: str
    class_: AxieClass
    type: PartType

    class Config:
        use_enum_values = True


class PartGenes(BaseModel):
    """Genes for a single body part position (D, R1, R2)."""
    d: Part
    r1: Part
    r2: Part


class AxieStats(BaseModel):
    """Axie base stats."""
    hp: int
    speed: int
    skill: int
    morale: int


class AxieGeneData(BaseModel):
    """Complete gene data for an Axie."""
    class_: AxieClass
    region: str
    tag: str
    body_skin: str
    pattern: str
    color: str
    eyes: PartGenes
    ears: PartGenes
    mouth: PartGenes
    horn: PartGenes
    back: PartGenes
    tail: PartGenes

    class Config:
        use_enum_values = True


class BreedingProbability(BaseModel):
    """Probability of a specific breeding outcome."""
    part: Part
    probability: float


class PartBreedingOutcome(BaseModel):
    """Breeding outcomes for a body part position."""
    position: PartType
    probabilities: list[BreedingProbability]


class ClassBreedingProbability(BaseModel):
    """Class probability for offspring."""
    class_: AxieClass
    probability: float

    class Config:
        use_enum_values = True
