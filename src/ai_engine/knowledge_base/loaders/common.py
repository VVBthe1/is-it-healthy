from pathlib import Path

import pypdf
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.shared.db.models import SourceDoc

from ..models import SourceConfig


def read_lines(path: Path) -> list[str]:
    reader = pypdf.PdfReader(path)
    lines = []
    for page in reader.pages:
        lines.extend((page.extract_text() or "").splitlines())
    return lines


def save_source_doc(session: Session, config: SourceConfig) -> None:
    stmt = insert(SourceDoc).values(
        id=config.id,
        url=str(config.url),
        publisher=config.publisher,
        title=config.title,
        doc_version=config.doc_version,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "url": stmt.excluded.url,
            "publisher": stmt.excluded.publisher,
            "title": stmt.excluded.title,
            "doc_version": stmt.excluded.doc_version,
            "loaded_at": func.now(),
        },
    )
    session.execute(stmt)
