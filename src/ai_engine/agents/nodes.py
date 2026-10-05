import re

from .chains import categorize_chain, details_chain, impacts_chain
from .retrieval import format_context, retrieve
from .schemas import (
    AnalysisState,
    CategorizedIngredient,
    Category,
    Ingredient,
    IngredientDetail,
    IngredientImpact,
)

SEVERITY_PENALTY = {"none": 0, "low": 3, "medium": 10, "high": 25}
HEALTHY_THRESHOLD = 60
DISCLAIMER = "This is general information from public sources, not a diagnosis or medical advice."
UNSUPPORTED_REASON = "Not supported by the retrieved sources."
NOT_FOUND = "Not found in sources"

DETAILS_QUERY = "what is {name} used for in food"
IMPACTS_QUERY = "health risks of eating too much {name}"


INGREDIENTS_PREFIX = re.compile(r"^\s*ingredients\s*:", re.IGNORECASE)
BRACKETS = str.maketrans("[{]}", "(())")
INS_CODE = re.compile(r"\b(?:INS|E)\s*-?\s*(\d{3,4}[a-z]?)", re.IGNORECASE)


def split_top_level(text: str) -> list[str]:
    parts, current, depth = [], "", 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        sentence_end = ch == "." and text[i + 1: i + 2].isspace()
        if (ch in ",;" or sentence_end) and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return parts


def parse_ingredients(text: str) -> list[Ingredient]:
    text = INGREDIENTS_PREFIX.sub("", text).translate(BRACKETS)
    ingredients, seen = [], set()
    for part in split_top_level(text):
        name = re.sub(r"\s+", " ", part).strip().rstrip(".").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        match = INS_CODE.search(name)
        ingredients.append(Ingredient(name=name, ins_number=match.group(1).lower() if match else None))
    return ingredients


def compute_score(impacts: list[IngredientImpact]) -> tuple[int, list[str]]:
    score, reasons = 100, []
    for impact in impacts:
        penalty = SEVERITY_PENALTY[impact.severity]
        score -= penalty
        if penalty:
            reasons.append(f"{impact.name}: {impact.severity} (-{penalty})")
    return max(score, 0), reasons


def normalize(state: AnalysisState) -> dict:
    return {"ingredients": parse_ingredients(state["input_text"])}


def categorize(state: AnalysisState) -> dict:
    lines = "\n".join(f"{n}. {i.name}" for n, i in enumerate(state["ingredients"], start=1))
    response = categorize_chain().invoke({"ingredients": lines})
    by_number = {item.number: item for item in response.items}
    categorized = []
    for n, i in enumerate(state["ingredients"], start=1):
        match = by_number.get(n)
        categorized.append(
            CategorizedIngredient(
                name=i.name,
                category=match.category if match else Category.UNKNOWN,
                search_name=(match.search_name.strip() if match else "") or i.name,
            )
        )
    return {"categorized": categorized}


def keep_retrieved_citations(output: IngredientDetail | IngredientImpact, chunks: list[dict]) -> None:
    retrieved = {(c["source_id"], c["page_number"]) for c in chunks}
    kept, seen = [], set()
    for citation in output.citations:
        key = (citation.source_id, citation.page_number)
        if key in retrieved and key not in seen:
            seen.add(key)
            kept.append(citation)
    output.citations = kept
    if kept:
        return
    if isinstance(output, IngredientDetail):
        output.notable_effects = NOT_FOUND
    elif output.severity != "none":
        output.severity = "none"
        output.reason = UNSUPPORTED_REASON
        output.conditions = []


def run_per_ingredient(state: AnalysisState, chain, query: str) -> list:
    items = [item for item in state["categorized"] if item.category != Category.UNKNOWN]
    chunks = [retrieve(query.format(name=item.search_name or item.name)) for item in items]
    inputs = [
        {"name": item.name, "category": item.category.value, "context": format_context(item_chunks)}
        for item, item_chunks in zip(items, chunks)
    ]
    outputs = chain.batch(inputs)
    for item, item_chunks, output in zip(items, chunks, outputs):
        output.name = item.name
        keep_retrieved_citations(output, item_chunks)
    return outputs


def details(state: AnalysisState) -> dict:
    return {"details": run_per_ingredient(state, details_chain(), DETAILS_QUERY)}


def impacts(state: AnalysisState) -> dict:
    return {"impacts": run_per_ingredient(state, impacts_chain(), IMPACTS_QUERY)}


def score(state: AnalysisState) -> dict:
    health_score, score_reasons = compute_score(state["impacts"])
    return {"health_score": health_score, "score_reasons": score_reasons}


def compose(state: AnalysisState) -> dict:
    category = {item.name: item.category.value for item in state["categorized"]}
    has_high = any(i.severity == "high" for i in state["impacts"])
    return {
        "result": {
            "is_healthy": state["health_score"] >= HEALTHY_THRESHOLD and not has_high,
            "health_score": state["health_score"],
            "score_reasons": state["score_reasons"],
            "medical_flags_applied": [],
            "unsafe_ingredients": [
                {**i.model_dump(), "category": category.get(i.name, Category.UNKNOWN.value)}
                for i in state["impacts"]
                if i.severity != "none"
            ],
            "ingredient_details": [
                {**d.model_dump(), "category": category.get(d.name, Category.UNKNOWN.value)}
                for d in state["details"]
            ],
            "unknown_ingredients": [c.name for c in state["categorized"] if c.category == Category.UNKNOWN],
            "disclaimer": DISCLAIMER,
        }
    }
