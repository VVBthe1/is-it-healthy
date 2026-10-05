import chromadb

from chromadb.utils import embedding_functions
from .config import CHROMA_COLLECTION, CHROMA_HOST, CHROMA_PORT, EMBEDDING_MODEL
from .models import Chunk


class ChromaStore:
    def __init__(self):
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        self.collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
            metadata={"embedding_model": EMBEDDING_MODEL},
        )

    def upsert(self, chunks: list[Chunk]) -> int:
        batch_size = 100
        inserted = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            try:
                self.collection.upsert(
                    ids=[chunk.id for chunk in batch],
                    documents=[chunk.text for chunk in batch],
                    metadatas=[chunk.metadata for chunk in batch],
                )
                inserted += len(batch)
            except Exception as e:
                print(f"Error upserting batch {i}: {e}")
                continue
        return inserted

    def query(self, text: str, n_results: int = 5) -> list[dict]:
        results = self.collection.query(
            query_texts=[text],
            n_results=n_results,
        )
        if not results["documents"]:
            return []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        return [
            {
                "text": document,
                "source_id": metadata["source_id"],
                "page_number": metadata["page_number"],
                "distance": distance,
            }
            for document, metadata, distance in zip(documents, metadatas, distances)
        ]
