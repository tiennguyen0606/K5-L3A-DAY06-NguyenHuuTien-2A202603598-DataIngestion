# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang: McGuffey's Sixth Eclectic Reader (Project Gutenberg #16751, public domain). Cắt trang gốc 40–80 → `starter/data/McGuffey_p40_80.pdf` (41 trang; 39 trang có text). Quy tắc: trang có text strip nonempty được tính nội dung; trang 27 và 30 trống không tính. Chi tiết: `data/manifest.json`.
- Chuẩn hóa, lỗi và giới hạn: Unicode NFC, gom khoảng trắng; PDF extract đôi khi tách giữa từ (`for mation`). Không OCR. Giới hạn: tiếng Anh cổ, layout bài đọc/elocution.
- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí: `sentence-transformers/all-MiniLM-L6-v2` (local, 384 dims); PostgreSQL + pgvector (Docker starter), cosine (`<=>`). Chi phí API = 0. Chạy từ `starter/`: `docker compose -p day6_student_starter up -d --wait` → `python -m src.run`. Trace: `starter/results/evaluation_summary.json` (bản sao `results/`).
- Metadata bắt buộc, trường lọc bổ sung: `document_id`, `source`, `page`; thêm `section` ∈ {emphasis_verse, voice, gesture, selection} map theo khoảng trang (manifest).

## Cấu hình và benchmark
- A: fixed_size 500 / overlap 50, không filter. B: by_paragraph max 600, không filter. C: giống B, filter `section` chỉ khi câu hỏi có `filter`. Khác biệt duy nhất B–C: filter lúc truy vấn.
- 20 câu trong `benchmark/questions.json` (15 dev / 5 test); filter: q06, q11, q15, q17, q20 (≥1 test). Evidence đã verify substring trên trang gold trước khi chạy.
- Tiêu chí chọn trước khi xem chi tiết test: ưu tiên Evidence Hit@3 trên **dev**, sau đó Hit@1, rồi số chunk/coherence.

## Kết quả
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A fixed | dev | 14/15 | 14/15 | 155 | ~1 lần ingest local | 0 |
| A fixed | test | 2/5 | 3/5 | 155 | | 0 |
| B paragraph | dev | 14/15 | 15/15 | 128 | | 0 |
| B paragraph | test | 3/5 | 5/5 | 128 | | 0 |
| C + filter | dev | 14/15 | 15/15 | 128 | | 0 |
| C + filter | test | 3/5 | 5/5 | 128 | | 0 |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1.2 /2 (n=10) | 15/15 | N/A | 0×2, 1×1, 2×2 → mean 1.0 |
| B | 2.0 /2 (n=10) | 15/15 | N/A | 0×0, 1×2, 2×3 → mean 1.6 |
| C | 2.0 /2 (n=10) | 15/15 | 5/5 | 0×0, 1×2, 2×3 → mean 1.6 |

Đường dẫn: `results/evaluation_summary.json`, `results/manual_audit.json`. Mẫu coherence = 10 page ID cố định; grounding = 5 câu test.

## Phân tích và kết luận
- A–B: B tốt hơn Hit@3 (đặc biệt test 5/5 vs 3/5) và coherence vì không cắt giữa ý. B–C: cùng chỉ số retrieval trên bộ này; filter hữu ích để tuân thủ phạm vi nhưng không đổi Hit khi gold đã cùng section với distractor gần.
- Ví dụ lỗi: **q01** (dev) — nhấn mạnh emphasis/accent, A không bắt page 2 trong top-3; B/C bắt ở hạng 3. **q19** (test) — hỏi Thomson / *The Seasons*, top-1 thường trang thunderstorm (37) thay vì bio trang 38.
- Chiến lược chọn: **B** (hoặc C nếu runtime luôn có section từ ngữ cảnh). Đánh đổi: A đơn giản hơn nhưng coherence thấp; C cần filter tin cậy.
- Hạn chế: test chỉ 5 câu; embedding tiếng Anh chung trên văn cổ; `section` heuristic; nhãn thủ công do chính tác giả.
- Làm lại: OCR/cleaner hyphenation; thử hybrid BM25; gắn section theo heading thật.
