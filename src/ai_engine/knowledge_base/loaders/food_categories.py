import re

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.shared.db.models import FoodCategory

from ..db.session import SessionLocal
from ..sources.pdf_source import PdfSource
from .common import read_lines, save_source_doc

HEADERS = ("Page ", "Food Product Categories used for", "Food Category")
BULLET = re.compile(r"^(\uf0b7|o)\s+")
CODE_LINE = re.compile(r"^(\d+(?:\.\d+)*)\s*[-–]?\s*([A-Za-z].*)")
SECOND_CODE = re.compile(r"\s(?=\d+(?:\.\d+)+\s*[-–]\s*[A-Za-z])")


def parse(lines: list[str]) -> list[dict]:
    rows = {}
    current = None

    for line in lines:
        line = line.strip()
        if line.startswith("Note:"):
            break
        if not line or line.startswith(HEADERS):
            continue
        if line.startswith("[Note"):
            current = None
            continue

        has_bullet = BULLET.match(line) is not None
        line = BULLET.sub("", line)

        for part in SECOND_CODE.split(line):
            match = CODE_LINE.match(part)
            if match:
                code = normalize_code(match.group(1))
                if code in rows:
                    current = None
                    continue
                name = match.group(2).split(f" {match.group(1)} ")[0]
                current = {"code": code, "name": name.strip()}
                rows[code] = current
            elif has_bullet:
                current = None
            elif current:
                current["name"] += " " + part

    for row in rows.values():
        row["parent_code"] = find_parent(row["code"], rows)
    return list(rows.values())


def normalize_code(code: str) -> str:
    return ".".join(str(int(part)) for part in code.split("."))


def find_parent(code: str, rows: dict) -> str | None:
    while "." in code:
        code = code.rsplit(".", 1)[0]
        if code in rows:
            return code
    return None


def save(session: Session, rows: list[dict], source_id: str) -> int:
    stmt = insert(FoodCategory).values([{**row, "source_id": source_id} for row in rows])
    stmt = stmt.on_conflict_do_update(
        index_elements=["code"],
        set_={
            "name": stmt.excluded.name,
            "parent_code": stmt.excluded.parent_code,
            "source_id": stmt.excluded.source_id,
        },
    )
    session.execute(stmt)
    return len(rows)


def load(source: PdfSource) -> int:
    rows = parse(read_lines(source.file_path))
    with SessionLocal.begin() as session:
        save_source_doc(session, source.config)
        return save(session, rows, source.config.id)
