import functools

from src.ai_engine.knowledge_base.chroma_store import ChromaStore

from .config import MAX_DISTANCE, RETRIEVAL_TOP_K


@functools.cache
def get_store() -> ChromaStore:
    return ChromaStore()


def retrieve(query: str, k: int = RETRIEVAL_TOP_K) -> list[dict]:
    chunks = get_store().query(query, n_results=k)
    return [c for c in chunks if c["distance"] <= MAX_DISTANCE]


def format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No source excerpts found."
    return "\n\n".join(f"[{c['source_id']} p.{c['page_number']}] {c['text']}" for c in chunks)
