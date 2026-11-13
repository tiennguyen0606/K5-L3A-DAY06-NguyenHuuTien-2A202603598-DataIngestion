"""Store and search vectors using PostgreSQL + pgvector."""
import json
import psycopg
from typing import Any
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        """Retain connection settings; validate model dimensions."""
        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        """Create table with vector column and source/page/filter metadata."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Kích hoạt extension pgvector nếu chưa có
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Tạo bảng lưu trữ các chunk dữ liệu và vector embedding
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id SERIAL PRIMARY KEY,
                        strategy TEXT NOT NULL,
                        chunk_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INT NOT NULL,
                        text TEXT NOT NULL,
                        metadata JSONB,
                        embedding VECTOR({self.dimensions})
                    );
                """)
                conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths/dimensions and write stable IDs without duplicates.

        When re-ingesting changed source documents, remove obsolete chunks too.
        """
        if len(chunks) != len(vectors):
            raise ValueError("Number of chunks must match the number of vectors.")
        
        if vectors and len(vectors[0]) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimensions}, got {len(vectors[0])}.")

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Xóa các chunk cũ thuộc chiến lược này để tránh trùng lặp khi nạp lại tài liệu
                cur.execute("DELETE FROM document_chunks WHERE strategy = %s;", (strategy,))
                
                # Chèn các chunk và vector mới vào database
                for chunk, vector in zip(chunks, vectors):
                    cur.execute("""
                        INSERT INTO document_chunks (strategy, chunk_id, document_id, source, page, text, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        strategy,
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.source,
                        chunk.page,
                        chunk.text,
                        json.dumps(chunk.metadata),
                        vector
                    ))
                conn.commit()

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Filter permitted metadata in SQL, rank by cosine distance, return top-k.

        Return chunk ID, text, score and metadata. Parameterize user-supplied values.
        """
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query vector dimension mismatch: expected {self.dimensions}, got {len(query_vector)}.")

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Sử dụng toán tử khoảng cách cosine (<=>) của pgvector
                query = """
                    SELECT chunk_id, text, metadata, page, (embedding <=> %s::vector) as distance
                    FROM document_chunks
                    WHERE strategy = %s
                """
                params: list[Any] = [query_vector, strategy]
                
                # Xử lý dynamic filtering dựa trên metadata JSONB nếu có
                if filters:
                    for key, value in filters.items():
                        query += " AND metadata->>%s = %s"
                        params.extend([key, str(value).lower() if isinstance(value, bool) else str(value)])
                        
                query += " ORDER BY distance ASC LIMIT %s;"
                params.append(top_k)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                results = []
                for row in rows:
                    distance = float(row[4])
                    score = 1.0 - distance
                    meta = row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {}
                    results.append({
                        "chunk_id": row[0],
                        "text": row[1],
                        "page": row[3],
                        "metadata": meta,
                        "score": score
                    })
                return results