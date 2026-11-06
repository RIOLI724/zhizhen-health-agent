"""RAG 检索测试：混合检索与引用。"""

import json
from pathlib import Path

from app.config import Settings
from app.rag.embeddings import MockEmbedder
from app.rag.pipeline import RAGPipeline

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_hybrid_retrieval_returns_citations(tmp_path):
    settings = Settings(data_dir=tmp_path, hybrid_search=True)
    pipeline = RAGPipeline(settings, MockEmbedder(64))

    entries = json.loads(
        (DATA_DIR / "knowledge" / "entries.json").read_text(encoding="utf-8")
    )
    pipeline.load_entries(entries)

    hits = pipeline.retrieve("头晕 耳鸣", top_k=3)

    assert hits
    assert any(
        "梅尼埃" in hit.doc_name or "眩晕" in hit.doc_name for hit in hits
    )
    assert all(hit.source for hit in hits)
