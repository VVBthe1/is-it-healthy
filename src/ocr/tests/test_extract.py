from src.ocr.extract import extract_ingredients


def test_cuts_between_ingredients_and_next_section():
    text = (
        "CRUNCHY BISCUITS\n"
        "INGREDIENTS: Refined Wheat Flour (Maida), Sugar, Edible Vegetable Oil (Palm),\n"
        "Invert Syrup, Salt, Emulsifier (INS 322).\n"
        "NUTRITIONAL INFORMATION per 100 g\n"
        "Energy 480 kcal"
    )

    assert extract_ingredients(text) == (
        "Refined Wheat Flour (Maida), Sugar, Edible Vegetable Oil (Palm), Invert Syrup, Salt, Emulsifier (INS 322)"
    )


def test_joins_words_hyphenated_across_lines():
    text = "Ingredients - Sugar, Pre-\nservative (INS 211)\nBest before 6 months"

    assert extract_ingredients(text) == "Sugar, Preservative (INS 211)"


def test_stops_at_allergen_statement_but_not_inline_contains():
    text = "Ingredients: Milk solids, Sugar. Contains permitted natural colour. Contains: Milk, Nuts"

    assert extract_ingredients(text) == "Milk solids, Sugar. Contains permitted natural colour"


def test_takes_rest_of_text_when_no_next_section():
    assert extract_ingredients("ingredient: rice, salt") == "rice, salt"


def test_cropped_list_without_heading_is_used_whole():
    text = "NOODLES:\nRefined wheat flour (Maida), Palm oil, Iodised salt, Wheat gluten.\nAllergen Note: Contains Wheat"

    assert extract_ingredients(text) == "NOODLES: Refined wheat flour (Maida), Palm oil, Iodised salt, Wheat gluten"


def test_no_heading_and_no_list():
    assert extract_ingredients("Net wt 200 g\nMRP Rs 40, batch 12") is None
