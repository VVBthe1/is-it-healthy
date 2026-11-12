"""Measure retrieval recall@k against retrieval_golden.yaml.

Requires Chroma running (same as production):
  chroma run --path src/data/knowledge/chroma --port 8000

Usage:
  python -m src.ai_engine.agents.eval.recall_at_k
  python -m src.ai_engine.agents.eval.recall_at_k --k 4
  python -m src.ai_engine.agents.eval.recall_at_k --suggest
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from src.ai_engine.agents.config import RETRIEVAL_TOP_K
from src.ai_engine.agents.retrieval import retrieve
from src.ai_engine.knowledge_base.chroma_store import ChromaStore

GOLDEN_PATH = Path(__file__).with_name("retrieval_golden.yaml")


def load_cases() -> list[dict]:
    data = yaml.safe_load(GOLDEN_PATH.read_text())
    return data["cases"]


def page_key(source_id: str, page_number: int) -> tuple[str, int]:
    return (source_id, int(page_number))


def hit_keys(hits: list[dict]) -> set[tuple[str, int]]:
    return {page_key(h["source_id"], h["page_number"]) for h in hits}


def relevant_keys(case: dict) -> set[tuple[str, int]]:
    return {page_key(r["source_id"], r["page_number"]) for r in case.get("relevant") or []}


def recall(hits: list[dict], relevant: set[tuple[str, int]]) -> float | None:
    if not relevant:
        return None
    return len(hit_keys(hits) & relevant) / len(relevant)


def format_hit(hit: dict) -> str:
    snippet = hit["text"][:100].replace("\n", " ")
    return f"  d={hit['distance']:.3f} {hit['source_id']} p.{hit['page_number']} | {snippet}"


def suggest(cases: list[dict], k: int) -> None:
    """Print raw Chroma top-k (no distance filter) to help label the golden set."""
    store = ChromaStore()
    for case in cases:
        print(f"\n== {case['id']}: {case['query']}")
        for hit in store.query(case["query"], n_results=k):
            print(format_hit(hit))
        labeled = relevant_keys(case)
        if labeled:
            print(f"  labeled: {sorted(labeled)}")


def evaluate(cases: list[dict], k: int) -> None:
    recalls: list[float] = []
    empty_ok = empty_fail = 0

    for case in cases:
        hits = retrieve(case["query"], k=k)
        relevant = relevant_keys(case)
        expect_empty = bool(case.get("expect_empty"))

        print(f"\n== {case['id']}")
        print(f"   query: {case['query']}")
        if case.get("notes"):
            print(f"   notes: {case['notes']}")

        if not hits:
            print("   hits: (none after MAX_DISTANCE filter)")
        else:
            for hit in hits:
                mark = "✓" if page_key(hit["source_id"], hit["page_number"]) in relevant else "·"
                print(f"   {mark}{format_hit(hit)[1:]}")

        if expect_empty:
            if not hits:
                empty_ok += 1
                print("   expect_empty: PASS")
            else:
                empty_fail += 1
                print("   expect_empty: FAIL (got hits)")
            continue

        if not relevant:
            print("   recall: skipped (no labels)")
            continue

        score = recall(hits, relevant)
        assert score is not None
        recalls.append(score)
        found = hit_keys(hits) & relevant
        missing = relevant - hit_keys(hits)
        print(f"   recall@{k}: {score:.2f}  found={sorted(found)}  missing={sorted(missing)}")

    print("\n--- summary ---")
    if recalls:
        mean = sum(recalls) / len(recalls)
        print(f"mean recall@{k} over {len(recalls)} labeled cases: {mean:.2f}")
    else:
        print("no labeled cases with relevant pages")
    if empty_ok or empty_fail:
        print(f"expect_empty: {empty_ok} pass, {empty_fail} fail")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval recall@k against the golden set.")
    parser.add_argument("--k", type=int, default=RETRIEVAL_TOP_K, help="top-k (default: RETRIEVAL_TOP_K)")
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="print raw Chroma hits (no distance filter) to help label YAML",
    )
    args = parser.parse_args()
    cases = load_cases()
    if args.suggest:
        suggest(cases, args.k)
    else:
        evaluate(cases, args.k)


if __name__ == "__main__":
    main()
