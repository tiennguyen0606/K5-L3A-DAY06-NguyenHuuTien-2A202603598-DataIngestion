"""Suggested pipeline entry point; implement the orchestration."""
import os
import json
from pathlib import Path

from dotenv import load_dotenv

from .ingestion import load_pdf, normalize_text
from .chunking import fixed_size, by_paragraph
from .embeddings import MyEmbedder
from .store import PgVectorStore
from .evaluation import evaluate_query, summarize


def main() -> None:
    """Implement the Day 06 pipeline orchestration."""
    starter_dir = Path(__file__).resolve().parent.parent
    repo_root = starter_dir.parent
    load_dotenv(starter_dir / ".env")

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab",
    )

    embedder = MyEmbedder("all-MiniLM-L6-v2")
    store = PgVectorStore(database_url, embedder.dimensions)
    store.create_schema()

    data_dir = starter_dir / "data"
    results_dir = starter_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Chỉ dùng corpus đã cắt; bỏ qua PDF khác nếu còn sót
    pdf_path = data_dir / "McGuffey_p40_80.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing corpus: {pdf_path}")

    pages = load_pdf(pdf_path, document_id=pdf_path.stem, source=pdf_path.name)
    for p in pages:
        p.text = normalize_text(p.text)
    content_pages = [p for p in pages if p.text]
    print(f"Loaded {len(pages)} pages ({len(content_pages)} with text).")
    if len(content_pages) < 30:
        raise ValueError(f"Need >=30 content pages, got {len(content_pages)}")

    chunks_a = []
    for page in pages:
        chunks_a.extend(fixed_size(page, size=500, overlap=50))
    print(f"Strategy A: {len(chunks_a)} chunks")
    store.upsert("strategy_A_fixed", chunks_a, embedder.embed_documents([c.text for c in chunks_a]))

    chunks_bc = []
    for page in pages:
        chunks_bc.extend(by_paragraph(page, max_size=600))
    print(f"Strategies B/C: {len(chunks_bc)} chunks")
    vectors_bc = embedder.embed_documents([c.text for c in chunks_bc])
    store.upsert("strategy_B_paragraph", chunks_bc, vectors_bc)
    store.upsert("strategy_C_filtered", chunks_bc, vectors_bc)

    bench_path = repo_root / "benchmark" / "questions.json"
    questions = json.loads(bench_path.read_text(encoding="utf-8"))
    print(f"Benchmark questions: {len(questions)}")

    strategies = ["strategy_A_fixed", "strategy_B_paragraph", "strategy_C_filtered"]
    all_evaluation_results = {}

    for strat in strategies:
        traces = []
        for q in questions:
            q_vector = embedder.embed_query(q["question"])
            filters = q.get("filter") if strat == "strategy_C_filtered" else None
            hits = store.search(strat, q_vector, top_k=3, filters=filters)
            # Đảm bảo page có trên hit để chấm
            for h in hits:
                meta = h.get("metadata") or {}
                if "page" not in h and "page" in meta:
                    h["page"] = meta["page"]
            traces.append(evaluate_query(q, hits))
        summary = summarize(traces)
        all_evaluation_results[strat] = {"summary": summary, "traces": traces}
        print(strat, summary["overall"])

    output_file = results_dir / "evaluation_summary.json"
    output_file.write_text(
        json.dumps(all_evaluation_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {output_file}")


if __name__ == "__main__":
    main()
