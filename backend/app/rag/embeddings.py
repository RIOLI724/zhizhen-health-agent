"""Embedding 抽象：Mock 哈希向量化 / OpenAI 兼容接口。"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

import numpy as np

from app.config import Settings


class BaseEmbedder(ABC):
    @property
    @abstractmethod
    def provider(self) -> str: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """批量向量化，返回 L2 归一化矩阵。"""

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


class MockEmbedder(BaseEmbedder):
    """确定性哈希向量化，保证测试与 CI 零外部依赖。"""

    def __init__(self, dim: int = 256):
        self.dim = dim

    @property
    def provider(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype="float32")
        for index, text in enumerate(texts):
            matrix[index] = self._vectorize(text)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def _vectorize(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype="float32")
        counts: dict[str, int] = {}
        for token in self._tokenize(text.lower()):
            counts[token] = counts.get(token, 0) + 1
        for token, count in counts.items():
            vector[self._hash(token)] += 1.0 + math.log(count)
        return vector

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens: list[str] = []
        for word in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text):
            tokens.append(word)
            if re.match(r"[\u4e00-\u9fff]", word):
                tokens.append(f"^{word}$")
        return tokens

    def _hash(self, token: str) -> int:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % self.dim


class LocalBgeEmbedder(BaseEmbedder):
    """本地中文语义向量（BGE small zh，ONNX 推理，免费离线）。

    首次使用需下载模型（约 90MB），之后完全本地运行。
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        cache_dir: str | None = None,
    ):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(
            model_name, cache_dir=cache_dir or None
        )
        self.model_name = model_name

    @property
    def provider(self) -> str:
        return f"fastembed:{self.model_name}"

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = list(self._model.embed(texts))
        matrix = np.array(vectors, dtype="float32")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


class OpenAICompatibleEmbedder(BaseEmbedder):
    """OpenAI 兼容 Embedding（智谱 embedding-3 等）。"""

    def __init__(self, settings: Settings):
        from openai import OpenAI

        self._settings = settings
        self._client = OpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            timeout=60,
        )

    @property
    def provider(self) -> str:
        return self._settings.embedding_model

    def embed(self, texts: list[str]) -> np.ndarray:
        response = self._client.embeddings.create(
            model=self._settings.embedding_model,
            input=texts,
        )
        data = sorted(response.data, key=lambda item: item.index)
        matrix = np.array([item.embedding for item in data], dtype="float32")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


def get_embedder(settings: Settings) -> BaseEmbedder:
    if (
        settings.embedding_provider == "openai_compatible"
        and settings.embedding_api_key
    ):
        return OpenAICompatibleEmbedder(settings)
    if settings.embedding_provider == "local_bge":
        try:
            cache_dir = settings.data_dir / "models"
            cache_dir.mkdir(parents=True, exist_ok=True)
            return LocalBgeEmbedder(
                settings.local_embedding_model, str(cache_dir)
            )
        except Exception:  # noqa: BLE001 - 模型不可用时回退，保证可运行
            import logging

            logging.getLogger(__name__).warning(
                "本地语义模型不可用，回退哈希向量（检索质量下降）"
            )
    return MockEmbedder(dim=settings.mock_embedding_dim)
