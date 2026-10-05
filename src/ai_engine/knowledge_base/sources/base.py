from abc import ABC, abstractmethod
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import CHUNK_OVERLAP, CHUNK_SIZE

from ..models import Chunk, Page, SourceConfig


class KnowledgeSource(ABC):
    """Every source type (PDF now, listing pages later) implements download and extract."""

    def __init__(self, config: SourceConfig):
        self.config = config

    @abstractmethod
    def download(self, fresh: bool = False, skip_download: bool = False) -> None:
        pass

    @abstractmethod
    def extract(self) -> list[Page]:
        pass

    def chunk(self, pages: list[Page]) -> list[Chunk]:
        """Split pages into overlapping chunks ready for embedding. Same for every source type."""

        splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        chunks = []
        for page in pages:
            for index, text in enumerate(splitter.split_text(page.text)):
                chunks.append(Chunk(
                    id=f"{self.config.id}:p{page.page_number}:c{index}",
                    text=text,
                    metadata={
                        "source_id": self.config.id,
                        "source_url": str(self.config.url),
                        "publisher": self.config.publisher,
                        "title": self.config.title,
                        "doc_version": self.config.doc_version,
                        "page_number": page.page_number,
                    },
                ))
        return chunks
