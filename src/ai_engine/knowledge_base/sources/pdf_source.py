import re

import pypdf
import requests

from ..config import RAW_DIR, HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT
from ..models import Page, SourceConfig
from .base import KnowledgeSource


class PdfSource(KnowledgeSource):
    """A single public PDF (`kind: file` in sources.yaml)."""

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.file_path = RAW_DIR / f"{config.id}.pdf"

    def download(self, fresh: bool = False, skip_download: bool = False) -> None:
        if skip_download and not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        if self.file_path.exists() and not fresh:
            return

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        response = requests.get(str(self.config.url), timeout=HTTP_TIMEOUT_SECONDS, headers={"User-Agent": HTTP_USER_AGENT})
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError("Not a PDF")
        self.file_path.write_bytes(response.content)

    def extract(self) -> list[Page]:
        empty_pages = 0
        with open(self.file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            pages = []
            for page_number, page in enumerate(reader.pages):
                text = page.extract_text().strip()
                has_text = len(text) > 0

                if not has_text:
                    empty_pages += 1
                    continue

                clean_text = re.sub(r'\s+', ' ', text)
                pages.append(Page(page_number=page_number + 1, text=clean_text))

            print(f"Empty pages: {empty_pages}, Source: {self.config.id}")
            return pages

