"""Chroma 向量存储：余弦空间、upsert、按文档删除。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings


class ChromaVectorStore:
    def __init__(self, directory: Path, collection_name: str = "knowledge"):
        directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def drop(self) -> None:
        """删除集合（换 embedding 维度时重建索引）。"""
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def dimension(self) -> int | None:
        sample = self._collection.get(limit=1, include=["embeddings"])
        embeddings = sample.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return None
        return len(embeddings[0])

    @property
    def size(self) -> int:
        return self._collection.count()

    def upsert(
        self,
        ids: list[str],
        texts: list[str],
        vectors: np.ndarray,
        metadatas: list[dict[str, Any]],
    ) -> None:
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=np.asarray(vectors, dtype="float32").tolist(),
            metadatas=metadatas,
        )

    def add(
        self,
        ids: list[str],
        texts: list[str],
        vectors: np.ndarray,
        metadatas: list[dict[str, Any]],
    ) -> None:
        self._collection.add(
            ids=ids,
            documents=texts,
            embeddings=np.asarray(vectors, dtype="float32").tolist(),
            metadatas=metadatas,
        )

    def search(
        self, vector: np.ndarray, top_k: int = 4
    ) -> list[tuple[float, dict[str, Any]]]:
        if self.size == 0:
            return []

        result = self._collection.query(
            query_embeddings=[np.asarray(vector, dtype="float32").reshape(-1).tolist()],
            n_results=min(top_k, self.size),
            include=["metadatas", "documents", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        documents = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits: list[tuple[float, dict[str, Any]]] = []
        for item_id, metadata, document, distance in zip(
            ids, metadatas, documents, distances, strict=False
        ):
            meta = dict(metadata or {})
            meta["id"] = item_id
            meta["text"] = document or ""
            hits.append((max(0.0, 1.0 - float(distance)), meta))
        return hits

    def all(self) -> list[dict[str, Any]]:
        result = self._collection.get(include=["metadatas", "documents"])
        ids = result.get("ids", [])
        metadatas = result.get("metadatas", [])
        documents = result.get("documents", [])

        items: list[dict[str, Any]] = []
        for item_id, metadata, document in zip(
            ids, metadatas, documents, strict=False
        ):
            meta = dict(metadata or {})
            meta["id"] = item_id
            meta["text"] = document or ""
            items.append(meta)
        return items

    def delete_doc(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})
