"""TODO: evaluate retrieved evidence and preserve per-query traces."""
from typing import Any
import re


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _hit_page(hit: dict[str, Any]) -> int | None:
    meta = hit.get("metadata") or {}
    page = hit.get("page", meta.get("page"))
    return int(page) if page is not None else None


def _is_evidence_hit(question: dict[str, Any], hit: dict[str, Any]) -> bool:
    gold_page = question.get("gold_page", question.get("page"))
    if _hit_page(hit) != gold_page:
        return False
    quote = question.get("evidence_quote") or ""
    if not quote:
        return True
    return _norm(quote) in _norm(hit.get("text") or "")


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """TODO: check source/page and enough gold evidence; keep hit@1 and hit@3 trace.

    Accept any documented alternative gold evidence. Do not infer human grounding
    or chunk coherence labels from exact string match.
    """
    hit_1 = bool(hits) and _is_evidence_hit(question, hits[0])
    hit_3 = any(_is_evidence_hit(question, h) for h in hits[:3])
    return {
        "question_id": question.get("id"),
        "split": question.get("split"),
        "hit_@1": hit_1,
        "hit_@3": hit_3,
        "hits": hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """TODO: aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    def _rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"n": 0, "hit_1": "0/0", "hit_3": "0/0", "hit_1_rate": 0.0, "hit_3_rate": 0.0}
        n = len(rows)
        h1 = sum(1 for t in rows if t.get("hit_@1"))
        h3 = sum(1 for t in rows if t.get("hit_@3"))
        return {
            "n": n,
            "hit_1": f"{h1}/{n}",
            "hit_3": f"{h3}/{n}",
            "hit_1_rate": h1 / n,
            "hit_3_rate": h3 / n,
        }

    by_split: dict[str, list[dict[str, Any]]] = {}
    for t in traces:
        by_split.setdefault(t.get("split") or "all", []).append(t)

    return {
        "total_queries": len(traces),
        "overall": _rate(traces),
        "by_split": {k: _rate(v) for k, v in by_split.items()},
        "hit_1_rate": _rate(traces)["hit_1_rate"],
        "hit_3_rate": _rate(traces)["hit_3_rate"],
    }
