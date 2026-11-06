"""RAG 管线：知识条目入库、向量 + BM25 混合检索、引用。"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.rag.bm25 import BM25
from app.rag.embeddings import BaseEmbedder
from app.rag.vectorstore import ChromaVectorStore


@dataclass
class RetrievedChunk:
    doc_id: str
    doc_name: str
    text: str
    score: float
    source: str = ""
    section: str = ""

    @property
    def citation(self) -> str:
        if self.source and self.section:
            return f"{self.source} · {self.section}"
        return self.source or self.doc_name


class RAGPipeline:
    def __init__(
        self,
        settings: Settings,
        embedder: BaseEmbedder,
        store: ChromaVectorStore | None = None,
    ):
        self.settings = settings
        self.embedder = embedder
        self.store = store or ChromaVectorStore(settings.vector_dir)
        self._bm25: BM25 | None = None
        self._bm25_size = -1
        self._lock = threading.Lock()

    # ---- 入库 ----
    def load_entries(self, entries: list[dict[str, Any]]) -> int:
        if not entries:
            return 0

        with self._lock:
            texts = [entry["text"] for entry in entries]
            vectors = self.embedder.embed(texts)

            # 换 embedding 模型后维度会变化，旧索引必须重建
            current_dim = self.store.dimension
            if current_dim is not None and current_dim != vectors.shape[1]:
                self.store.drop()

            ids = [entry["id"] for entry in entries]
            metadatas = [
                {
                    "doc_id": entry["id"],
                    "doc_name": entry["title"],
                    "source": entry["source"],
                    "section": entry["section"],
                }
                for entry in entries
            ]
            self.store.upsert(ids, texts, vectors, metadatas)
            self._bm25 = None
            self._bm25_size = -1
            return len(entries)

    # ---- 检索 ----
    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if self.store.size == 0:
            return []

        limit = top_k or self.settings.top_k
        query_vector = self.embedder.embed_query(query)

        if self.settings.hybrid_search:
            hits = self._hybrid_search(query, query_vector, limit)
        else:
            hits = [
                (score, meta)
                for score, meta in self.store.search(query_vector, top_k=limit)
                if score >= self.settings.retrieval_min_score
            ]

        return [self._to_chunk(score, meta) for score, meta in hits]

    def _hybrid_search(
        self, query: str, query_vector, top_k: int
    ) -> list[tuple[float, dict[str, Any]]]:
        items = self.store.all()
        if not items:
            return []

        vector_hits = self.store.search(query_vector, top_k=len(items))
        cosine = {meta["id"]: score for score, meta in vector_hits}

        bm25_scores = self._bm25_scores(query, items)
        bm25_order = sorted(
            range(len(items)), key=lambda index: bm25_scores[index], reverse=True
        )

        rrf_k = max(1, self.settings.rrf_k)
        fused = {meta["id"]: 0.0 for meta in items}
        for rank, (_, meta) in enumerate(vector_hits, 1):
            fused[meta["id"]] += 1.0 / (rrf_k + rank)
        for rank, index in enumerate(bm25_order, 1):
            if bm25_scores[index] <= 0:
                continue
            fused[items[index]["id"]] += 1.0 / (rrf_k + rank)

        ranked = sorted(
            items, key=lambda meta: fused[meta["id"]], reverse=True
        )[:top_k]
        return [(cosine.get(meta["id"], 0.0), meta) for meta in ranked]

    def _bm25_scores(self, query: str, items: list[dict[str, Any]]) -> list[float]:
        if self._bm25 is None or self._bm25_size != len(items):
            self._bm25 = BM25([item["text"] for item in items])
            self._bm25_size = len(items)
        return self._bm25.scores(query)

    def delete_doc(self, doc_id: str) -> None:
        with self._lock:
            self.store.delete_doc(doc_id)
            self._bm25 = None
            self._bm25_size = -1

    @property
    def document_count(self) -> int:
        return len({meta.get("doc_id") for meta in self.store.all()})

    @staticmethod
    def _to_chunk(score: float, meta: dict[str, Any]) -> RetrievedChunk:
        return RetrievedChunk(
            doc_id=meta.get("doc_id", ""),
            doc_name=meta.get("doc_name", ""),
            text=meta.get("text", ""),
            score=round(float(score), 4),
            source=meta.get("source", ""),
            section=meta.get("section", ""),
        )
