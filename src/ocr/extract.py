import re

INGREDIENTS_START = re.compile(r"ingredients?\s*[:\-]?", re.IGNORECASE)
SECTION_END = re.compile(
    r"\b(?:nutrition(?:al)?\s+(?:information|facts|value)|allergen|contains\s*:|may contain|best before|use by"
    r"|mfd|manufactured|marketed|packed|net\s+(?:wt|weight|qty|quantity)|storage|store in|mrp|batch"
    r"|fssai|lic\.?\s*no)",
    re.IGNORECASE,
)
MIN_LIST_COMMAS = 3


def flatten(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_ingredients(text: str) -> str | None:
    flat = flatten(text)
    start = INGREDIENTS_START.search(flat)
    if start:
        rest = flat[start.end():]
    elif flat.count(",") >= MIN_LIST_COMMAS:
        rest = flat
    else:
        return None
    end = SECTION_END.search(rest)
    section = rest[: end.start()] if end else rest
    return section.strip(" .:;,-") or None
