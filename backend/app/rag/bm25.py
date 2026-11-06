"""轻量 BM25：中文按字 + 字二元组，英文按词。"""

from __future__ import annotations

import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    words = re.findall(r"[a-z0-9]+", lowered)
    chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
    return words + chars + bigrams


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._counts = [Counter(tokenize(doc)) for doc in docs]
        self._lengths = [sum(counts.values()) for counts in self._counts]
        self._avgdl = (
            sum(self._lengths) / len(self._lengths) if self._lengths else 0.0
        )
        self._df: Counter[str] = Counter()
        for counts in self._counts:
            self._df.update(counts.keys())
        self._n = len(docs)

    def scores(self, query: str) -> list[float]:
        tokens = tokenize(query)
        result = [0.0] * self._n
        if not tokens or not self._n:
            return result

        for index, counts in enumerate(self._counts):
            length_norm = (
                1 - self.b + self.b * self._lengths[index] / (self._avgdl or 1.0)
            )
            score = 0.0
            for token in tokens:
                tf = counts.get(token, 0)
                if not tf:
                    continue
                df = self._df[token]
                idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
                score += idf * tf * (self.k1 + 1) / (
                    tf + self.k1 * length_norm
                )
            result[index] = score
        return result
