from enum import StrEnum
from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class Category(StrEnum):
    CEREALS_GRAINS = "cereals_grains"
    PULSES_LEGUMES = "pulses_legumes"
    DAIRY = "dairy"
    OILS_FATS = "oils_fats"
    SWEETENERS = "sweeteners"
    SALT_SODIUM = "salt_sodium"
    SPICES_CONDIMENTS = "spices_condiments"
    FRUITS_VEGETABLES = "fruits_vegetables"
    NUTS_SEEDS = "nuts_seeds"
    MEAT_EGG_FISH = "meat_egg_fish"
    COLOUR = "additive_colour"
    PRESERVATIVE = "additive_preservative"
    EMULSIFIER = "additive_emulsifier"
    STABILIZER = "additive_stabilizer"
    FLAVOUR_ENHANCER = "additive_flavour_enhancer"
    ANTIOXIDANT = "additive_antioxidant"
    ACIDITY_REGULATOR = "additive_acidity_regulator"
    OTHER_ADDITIVE = "additive_other"
    UNKNOWN = "unknown"


Severity = Literal["none", "low", "medium", "high"]


class Ingredient(BaseModel):
    name: str
    ins_number: str | None = None


class CategorizedIngredient(BaseModel):
    name: str
    category: Category
    search_name: str = ""


class CategorizeItem(BaseModel):
    number: int = Field(description="The line number of the ingredient in the input.")
    search_name: str = Field(description="Common English or chemical name, e.g. INS 211 -> sodium benzoate.")
    category: Category


class CategorizeOutput(BaseModel):
    items: list[CategorizeItem]


class Citation(BaseModel):
    source_id: str
    page_number: int


class IngredientDetail(BaseModel):
    name: str
    what_it_does: str = Field(description="Role in the food, one or two sentences.")
    notable_effects: str = Field(description="Effects stated in the sources, or 'Not found in sources'.")
    citations: list[Citation] = Field(description="Every excerpt used, as its source_id and page number.")


class IngredientImpact(BaseModel):
    name: str
    severity: Severity
    reason: str = Field(description="Why this severity, based only on the sources.")
    conditions: list[str] = Field(description="Related conditions, e.g. hypertension. Empty if none.")
    citations: list[Citation] = Field(description="Every excerpt relied on, as its source_id and page number.")


class AnalysisState(TypedDict, total=False):
    input_text: str
    ingredients: list[Ingredient]
    categorized: list[CategorizedIngredient]
    details: list[IngredientDetail]
    impacts: list[IngredientImpact]
    health_score: int
    score_reasons: list[str]
    result: dict
