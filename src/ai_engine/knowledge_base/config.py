import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")
PACKAGE_DIR = Path(__file__).resolve().parent

SOURCES_PATH = PACKAGE_DIR / "sources.yaml"

DATA_DIR = REPO_ROOT / "src" / "data" / "knowledge"
RAW_DIR = DATA_DIR / "raw"
CHROMA_DATA_DIR = DATA_DIR / "chroma"

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "knowledge_v1")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DATABASE_URL = os.environ["DATABASE_URL"]

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

HTTP_TIMEOUT_SECONDS = 60
HTTP_USER_AGENT = "is-it-healthy-knowledge-base/0.1"
