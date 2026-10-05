from langchain_core.runnables import Runnable

from .llm import get_llm
from .prompts import CATEGORIZE_PROMPT, DETAILS_PROMPT, IMPACTS_PROMPT
from .schemas import CategorizeOutput, IngredientDetail, IngredientImpact

# Ollama's default json_schema mode returns empty lists for short inputs on qwen2.5:7b.
STRUCTURED_METHOD = "function_calling"


def categorize_chain() -> Runnable:
    return CATEGORIZE_PROMPT | get_llm().with_structured_output(CategorizeOutput, method=STRUCTURED_METHOD)


def details_chain() -> Runnable:
    return DETAILS_PROMPT | get_llm().with_structured_output(IngredientDetail, method=STRUCTURED_METHOD)


def impacts_chain() -> Runnable:
    return IMPACTS_PROMPT | get_llm().with_structured_output(IngredientImpact, method=STRUCTURED_METHOD)
