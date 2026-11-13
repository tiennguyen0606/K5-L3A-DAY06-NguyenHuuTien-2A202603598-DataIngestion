# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang: *McGuffey's Sixth Eclectic Reader* (Project Gutenberg #16751, public domain). Cắt trang gốc 40–80 → `starter/data/McGuffey_p40_80.pdf` (41 trang; ~38–39 trang có text sau làm sạch). Quy tắc: trang có text nonempty được tính; trang trống không tính. Chi tiết: `data/manifest.json`.
- Chuẩn hóa / làm sạch PDF: NFC; gỡ soft-hyphen xuống dòng; bỏ running header/footer (`ECLECTIC SERIES`, `SIXTH READER`, số trang trần); gom whitespace, giữ `\n\n`. Không OCR. Giới hạn: PDF cũ vẫn còn tách giữa từ (`for mation`).
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` (local, 384-d); store: PostgreSQL + pgvector, cosine; chi phí API = 0. Chạy: `starter/` → `docker compose -p day6_student_starter up -d --wait` → `python -m src.run`.
- Metadata: `document_id`, `source`, `page` + `section` ∈ {emphasis_verse, voice, gesture, selection}.

## Cấu hình và benchmark
- **Ablation fixed (sentence-snap, overlap ~10%)**: A250 (250/25), **A500** (500/50 = strategy A nộp bài), A1000 (1000/100).
- **B**: by_paragraph max 600, oversized dùng sentence window. **C**: giống B + filter `section` khi câu có `filter`.
- 20 câu (`benchmark/questions.json`), 15 dev / 5 test; filter q06,q11,q15,q17,q20.
- Tiêu chí chọn trước khi soi test: ưu tiên **dev Evidence Hit@3**, rồi Hit@1, rồi coherence/số chunk.

## Kết quả

### Ablation kích thước chunk (fixed + sentence boundary)
| Config | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Chunks |
|---|---|---|---|---|---|
| A250 (250/25) | 12/15 | 14/15 | 3/5 | 4/5 | 325 |
| A500 (500/50) | 13/15 | **15/15** | 1/5 | 3/5 | 167 |
| A1000 (1000/100) | 13/15 | **15/15** | 3/5 | 4/5 | 88 |

Trong các fixed-size, **A500 và A1000** tốt nhất trên **dev Hit@3** (15/15). A1000 nhỉnh hơn trên test Hit nhưng tốn ngữ cảnh dài hơn / ít chunk hơn. A250 phân mảnh quá mức → mất điều kiện xung quanh.

### Ba chiến lược nộp bài (A=A500, B, C)
| Strategy | Split | Hit@1 | Evidence Hit@3 | Chunks | Chi phí |
|---|---|---|---|---|---|
| A fixed-500 | dev | 13/15 | 15/15 | 167 | 0 |
| A fixed-500 | test | 1/5 | 3/5 | 167 | 0 |
| B paragraph | dev | **15/15** | **15/15** | 141 | 0 |
| B paragraph | test | 3/5 | 4/5 | 141 | 0 |
| C + filter | dev | 15/15 | 15/15 | 141 | 0 |
| C + filter | test | 3/5 | 4/5 | 141 | 0 |

| Strategy | Coherence /2 (n=10) | Metadata đủ (n/N) | Filter tuân thủ | Grounding mean /2 (5 test) |
|---|---|---|---|---|
| A500 | 1.6 | 15/15 | N/A | 0.8 |
| B | 2.0 | 15/15 | N/A | 1.4 |
| C | 2.0 | 15/15 | 5/5 | 1.4 |

Trace: `results/evaluation_summary.json`, audit: `results/manual_audit.json`, log: `artifacts/experiment_log.csv`.

## Phân tích và kết luận
- **A–B**: B thắng rõ trên **dev Hit@1** (15/15 vs 13/15) và coherence vì giữ ranh giới đoạn; A vẫn cắt/pha trộn dù đã snap câu.
- **B–C**: cùng retrieval; filter giúp tuân thủ `section` nhưng không tách được distractor cùng section.
- **Ablation**: tăng size từ 250→500 cải thiện Hit@3; 1000 không vượt B. **Chọn B** theo tiêu chí dev.
- **Root cause lỗi**:
  - **q19** (test): top hay lệch sang trang thunderstorm (37) thay vì bio Thomson (38) — gần nghĩa *Seasons*/storm; embedding MiniLM nhầm ngữ cảnh văn học kề nhau hơn là lỗi chunk quá nhỏ.
  - **q20** (test): ngày “latter end of May” nằm trong đoạn house-cleaning dài p39–41; narrative distractor làm Hit@1 trượt dù top-3 (B/C) thường vẫn có trang đúng.
- Hạn chế: test n=5; model không chuyên archaic English; `section` heuristic; nhãn thủ công của tác giả.
- Làm lại: hybrid BM25; section theo heading thật; thử multilingual/literary embedding.
