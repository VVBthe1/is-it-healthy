from typing import Literal

from pydantic import BaseModel, ConfigDict, HttpUrl


class SourceConfig(BaseModel):
    """One entry in sources.yaml. Unknown keys or wrong types fail when the file loads."""

    model_config = ConfigDict(extra="forbid")

    id: str
    url: HttpUrl
    kind: Literal["file", "listing"]
    publisher: str
    title: str
    doc_version: str
    store: Literal["chroma", "postgres"] = "chroma"
    enabled: bool = True
    note: str = ""


class Page(BaseModel):
    page_number: int
    text: str


class Chunk(BaseModel):
    id: str
    text: str
    metadata: dict = {}
