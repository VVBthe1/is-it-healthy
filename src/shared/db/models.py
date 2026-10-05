from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, MetaData, Numeric, String, Text, cast, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

SCHEMA = "knowledge"


def code_sort_key(column):
    return cast(func.string_to_array(column, "."), ARRAY(Integer))


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class SourceDoc(Base):
    __tablename__ = "source_docs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    doc_version: Mapped[str] = mapped_column(String(64))
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FoodCategory(Base):
    __tablename__ = "food_categories"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    parent_code: Mapped[str | None] = mapped_column(ForeignKey("food_categories.code"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_docs.id"))

    parent: Mapped["FoodCategory | None"] = relationship(back_populates="children", remote_side="FoodCategory.code")
    children: Mapped[list["FoodCategory"]] = relationship(
        back_populates="parent", order_by=lambda: code_sort_key(FoodCategory.code)
    )


class Additive(Base):
    __tablename__ = "additives"

    id: Mapped[int] = mapped_column(primary_key=True)
    ins_number: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(Text)
    functional_classes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_docs.id"))

    limits: Mapped[list["AdditiveLimit"]] = relationship(back_populates="additive")


class AdditiveLimit(Base):
    __tablename__ = "additive_limits"

    additive_id: Mapped[int] = mapped_column(ForeignKey("additives.id"), primary_key=True)
    category_code: Mapped[str] = mapped_column(ForeignKey("food_categories.code"), primary_key=True, index=True)
    max_level: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(String(16))
    is_gmp: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_docs.id"))

    additive: Mapped["Additive"] = relationship(back_populates="limits")
    category: Mapped["FoodCategory"] = relationship()


class Nutrient(Base):
    __tablename__ = "nutrients"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(16))


class Food(Base):
    __tablename__ = "foods"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    scientific_name: Mapped[str | None] = mapped_column(Text)
    food_group: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_docs.id"))

    nutrients: Mapped[list["FoodNutrient"]] = relationship(back_populates="food")


class FoodNutrient(Base):
    __tablename__ = "food_nutrients"

    food_code: Mapped[str] = mapped_column(ForeignKey("foods.code"), primary_key=True)
    nutrient_code: Mapped[str] = mapped_column(ForeignKey("nutrients.code"), primary_key=True, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric)
    sd: Mapped[Decimal | None] = mapped_column(Numeric)

    food: Mapped["Food"] = relationship(back_populates="nutrients")
    nutrient: Mapped["Nutrient"] = relationship()


class NutrientRequirement(Base):
    __tablename__ = "nutrient_requirements"

    nutrient_code: Mapped[str] = mapped_column(ForeignKey("nutrients.code"), primary_key=True)
    population_group: Mapped[str] = mapped_column(String(64), primary_key=True)
    ear: Mapped[Decimal | None] = mapped_column(Numeric)
    rda: Mapped[Decimal | None] = mapped_column(Numeric)
    tul: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[str] = mapped_column(ForeignKey("source_docs.id"))

    nutrient: Mapped["Nutrient"] = relationship()
