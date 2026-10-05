from langchain_core.prompts import ChatPromptTemplate

from .schemas import Category

CATEGORY_LIST = "\n".join(f"- {c.value}" for c in Category)

CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You classify packaged-food ingredients from Indian labels into categories.\n"
            "Allowed categories:\n{categories}\n\n"
            "Rules:\n"
            "- Ingredients are numbered. Return one item per line, with its number.\n"
            "- Use an additive_* category when the name is an additive, an INS number or an E-number "
            "(INS 211 is a preservative, INS 322 an emulsifier, INS 330 an acidity regulator).\n"
            "- Hindi or regional names map to the same category as their English name (maida = cereals_grains).\n"
            "- search_name: the common English or chemical name found in nutrition books. "
            "Translate Hindi names and replace INS or E numbers with the chemical name. "
            "Never include INS/E numbers or words like Preservative, Colour or Emulsifier in it.\n"
            "  Examples: 'Preservative (INS 211)' -> 'sodium benzoate', 'Maida' -> 'refined wheat flour', "
            "'Emulsifier (E322)' -> 'lecithin', 'Edible vegetable oil (Palm oil)' -> 'palm oil', "
            "'Sugar' -> 'sugar'.\n"
            "- If you are not sure, use unknown. Do not guess.",
        ),
        ("human", "Ingredients:\n{ingredients}"),
    ]
).partial(categories=CATEGORY_LIST)

DETAILS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You explain one food ingredient using only the source excerpts provided.\n"
            "Each excerpt starts with [source_id p.page].\n\n"
            "Rules:\n"
            "- what_it_does: the ingredient's role in the food, in plain language.\n"
            "- notable_effects: effects the excerpts state. If they say nothing, write 'Not found in sources'.\n"
            "- citations: the source_id and page of every excerpt you used. Empty if none were used.\n"
            "- Never add numbers, limits or health claims that are not in the excerpts.",
        ),
        (
            "human",
            "Ingredient: {name}\nCategory: {category}\n\nSource excerpts:\n{context}",
        ),
    ]
)

IMPACTS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You assess the health impact of one food ingredient for the general Indian population, "
            "using only the source excerpts provided (ICMR-NIN Dietary Guidelines, FSSAI regulations).\n"
            "Each excerpt starts with [source_id p.page].\n\n"
            "Severity:\n"
            "- high: the excerpts restrict or warn strongly against it (e.g. trans fats, excess salt or sugar, "
            "a limited or banned additive).\n"
            "- medium: the excerpts advise limiting it.\n"
            "- low: minor concerns in the excerpts, or safe within permitted limits.\n"
            "- none: no concern in the excerpts, or the excerpts do not mention it.\n\n"
            "Rules:\n"
            "- reason: one or two sentences pointing to what the excerpts say.\n"
            "- conditions: health conditions the excerpts link to it (e.g. hypertension, diabetes). Empty if none.\n"
            "- citations: source_id and page of every excerpt you relied on. A severity above none needs at least one.\n"
            "- Never invent numbers, limits or conditions.",
        ),
        (
            "human",
            "Ingredient: {name}\nCategory: {category}\n\nSource excerpts:\n{context}",
        ),
    ]
)
