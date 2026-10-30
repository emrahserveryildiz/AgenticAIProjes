from __future__ import annotations

import json
from typing import Any

from .config import ROOT
from .knowledge import KnowledgeBase


def run_retrieval_evaluation(kb: KnowledgeBase) -> dict[str, Any]:
    cases = json.loads((ROOT / "data" / "eval_cases.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        matches = kb.search(case["query"], top_k=3)
        text = " ".join(item["text"].lower() for item in matches)
        source_hit = any(item["source"] == case["expected_source"] for item in matches)
        terms_hit = [term for term in case["expected_terms"] if term.lower() in text]
        results.append({"id": case["id"], "query": case["query"], "source_hit": source_hit,
                        "terms_hit": terms_hit, "expected_terms": case["expected_terms"],
                        "top_sources": [item["source"] for item in matches]})
    count = len(results)
    return {"results": results,
            "source_hit_rate": sum(1 for r in results if r["source_hit"]) / count if count else 0,
            "term_coverage": sum(len(r["terms_hit"]) / max(1, len(r["expected_terms"])) for r in results) / count if count else 0}

