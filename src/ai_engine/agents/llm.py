import functools

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from .config import LLM_NUM_CTX, LLM_TEMPERATURE, OLLAMA_BASE_URL, OLLAMA_MODEL


@functools.cache
def get_llm() -> BaseChatModel:
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=LLM_TEMPERATURE,
        num_ctx=LLM_NUM_CTX,
    )
