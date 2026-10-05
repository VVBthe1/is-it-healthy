from src.ai_engine.agents.nodes import (
    DISCLAIMER,
    NOT_FOUND,
    UNSUPPORTED_REASON,
    compose,
    compute_score,
    keep_retrieved_citations,
    parse_ingredients,
)
from src.ai_engine.agents.schemas import (
    CategorizedIngredient,
    Category,
    Citation,
    IngredientDetail,
    IngredientImpact,
)


def names(text):
    return [i.name for i in parse_ingredients(text)]


def test_parse_simple_list():
    parsed = parse_ingredients("sugar, salt, INS 211")

    assert [i.name for i in parsed] == ["sugar", "salt", "INS 211"]
    assert [i.ins_number for i in parsed] == [None, None, "211"]


def test_parse_drops_prefix_and_splits_on_semicolons():
    assert names("Ingredients: Wheat flour (Maida), Sugar; Edible vegetable oil (Palm oil).") == [
        "Wheat flour (Maida)",
        "Sugar",
        "Edible vegetable oil (Palm oil)",
    ]


def test_parse_keeps_commas_inside_parentheses():
    parsed = parse_ingredients("Emulsifiers (INS 322, INS 471), Sugar")

    assert [i.name for i in parsed] == ["Emulsifiers (INS 322, INS 471)", "Sugar"]
    assert parsed[0].ins_number == "322"


def test_parse_ins_and_e_number_formats():
    parsed = parse_ingredients("Preservative (E211), Acidity regulator (E 330), Colour (INS 160a)")

    assert [i.ins_number for i in parsed] == ["211", "330", "160a"]


def test_parse_cleans_whitespace_and_duplicates():
    assert names("  Sugar ,sugar,   SUGAR, Iodised   salt , ,") == ["Sugar", "Iodised salt"]


def test_parse_ocr_text_with_sentences_and_odd_brackets():
    assert names("Butter, common salt. CONTAINS PERMITTED NATURAL COLOUR {ANNATTO]") == [
        "Butter",
        "common salt",
        "CONTAINS PERMITTED NATURAL COLOUR (ANNATTO)",
    ]


def test_parse_keeps_decimal_points():
    assert names("Gram Meal (0.5%), Salt 1.2%") == ["Gram Meal (0.5%)", "Salt 1.2%"]


def test_parse_empty_text():
    assert parse_ingredients("   ") == []


def impact(name, severity, citations=(), conditions=()):
    return IngredientImpact(
        name=name, severity=severity, reason="r", conditions=list(conditions), citations=list(citations)
    )


def detail(name, citations=()):
    return IngredientDetail(name=name, what_it_does="Base", notable_effects="x", citations=list(citations))


def test_score_subtracts_penalties_and_lists_reasons():
    impacts = [impact("Salt", "high"), impact("Sugar", "medium"), impact("INS 330", "low"), impact("Rice", "none")]

    assert compute_score(impacts) == (62, ["Salt: high (-25)", "Sugar: medium (-10)", "INS 330: low (-3)"])


def test_score_never_below_zero():
    score, _ = compute_score([impact(f"x{i}", "high") for i in range(5)])

    assert score == 0


def test_score_with_no_impacts():
    assert compute_score([]) == (100, [])


def test_compose_builds_result():
    citation = Citation(source_id="dgi_2024", page_number=90)
    state = {
        "categorized": [
            CategorizedIngredient(name="Salt", category=Category.SALT_SODIUM),
            CategorizedIngredient(name="Rice", category=Category.CEREALS_GRAINS),
            CategorizedIngredient(name="Xyzzy", category=Category.UNKNOWN),
        ],
        "details": [detail("Salt", [citation]), detail("Rice")],
        "impacts": [impact("Salt", "high", [citation], ["hypertension"]), impact("Rice", "none")],
        "health_score": 75,
        "score_reasons": ["Salt: high (-25)"],
    }

    result = compose(state)["result"]

    assert result["is_healthy"] is False
    assert result["health_score"] == 75
    assert result["score_reasons"] == ["Salt: high (-25)"]
    assert result["medical_flags_applied"] == []
    assert result["unsafe_ingredients"] == [
        {
            "name": "Salt",
            "category": "salt_sodium",
            "severity": "high",
            "reason": "r",
            "conditions": ["hypertension"],
            "citations": [{"source_id": "dgi_2024", "page_number": 90}],
        }
    ]
    assert [d["name"] for d in result["ingredient_details"]] == ["Salt", "Rice"]
    assert result["ingredient_details"][0]["category"] == "salt_sodium"
    assert result["unknown_ingredients"] == ["Xyzzy"]
    assert result["disclaimer"] == DISCLAIMER


def test_compose_healthy_when_score_high_and_nothing_high():
    state = {
        "categorized": [CategorizedIngredient(name="Rice", category=Category.CEREALS_GRAINS)],
        "details": [],
        "impacts": [impact("Rice", "low")],
        "health_score": 97,
        "score_reasons": ["Rice: low (-3)"],
    }

    assert compose(state)["result"]["is_healthy"] is True


CHUNKS = [{"source_id": "dgi_2024", "page_number": 90}, {"source_id": "dgi_2024", "page_number": 91}]


def cite(page, source_id="dgi_2024"):
    return Citation(source_id=source_id, page_number=page)


def test_citations_keep_only_retrieved_and_dedupe():
    output = impact("Salt", "high", [cite(90), cite(90), cite(12), cite(91, "fssai")])

    keep_retrieved_citations(output, CHUNKS)

    assert output.citations == [cite(90)]
    assert output.severity == "high"


def test_impact_without_valid_citation_is_downgraded():
    output = impact("Sugar", "medium", [cite(12)], ["diabetes"])

    keep_retrieved_citations(output, CHUNKS)

    assert (output.severity, output.reason, output.conditions, output.citations) == (
        "none", UNSUPPORTED_REASON, [], []
    )


def test_detail_without_valid_citation_drops_effects():
    output = detail("Maida", [cite(12)])

    keep_retrieved_citations(output, [])

    assert (output.what_it_does, output.notable_effects, output.citations) == ("Base", NOT_FOUND, [])
