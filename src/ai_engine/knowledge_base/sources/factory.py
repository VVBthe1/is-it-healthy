import yaml

from ..config import SOURCES_PATH
from ..models import SourceConfig
from .base import KnowledgeSource
from .pdf_source import PdfSource

SOURCE_TYPES = {
    "file": PdfSource,
}


class SourceFactory:
    @staticmethod
    def create(config: SourceConfig) -> KnowledgeSource:
        if config.kind not in SOURCE_TYPES:
            raise ValueError(f"No source class for kind '{config.kind}' (source '{config.id}')")
        source_class = SOURCE_TYPES[config.kind]
        return source_class(config)

    @staticmethod
    def load(only: str | None = None) -> list[KnowledgeSource]:
        with open(SOURCES_PATH) as f:
            data = yaml.safe_load(f)

        sources = []
        for entry in data["sources"]:
            config = SourceConfig(**entry)
            if not config.enabled:
                continue
            if only and config.id != only:
                continue
            sources.append(SourceFactory.create(config))

        if only and not sources:
            raise ValueError(f"No enabled source with id '{only}'")
        return sources
