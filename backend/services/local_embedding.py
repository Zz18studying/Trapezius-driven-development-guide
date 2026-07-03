# -*- coding: utf-8 -*-
"""
本地轻量 embedding 兜底实现。

用于没有 sentence-transformers 本地模型、又不能联网下载 Chroma 默认模型的环境。
服务器存在 /home/ubuntu/.cache/sentence-transformers/local_model 时仍优先使用正式模型。
"""

import hashlib
import math
import re
from typing import List


class SimpleChineseEmbeddingFunction:
    """基于字符 n-gram 的确定性向量，适合本地离线测试和兜底检索。"""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def name(self) -> str:
        return "simple_chinese_ngram"

    def default_space(self) -> str:
        return "cosine"

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in input]

    def embed_query(self, input: List[str]) -> List[List[float]]:
        return self(input)

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        return self(input)

    def _embed(self, text: str) -> List[float]:
        text = self._normalize(text)
        vector = [0.0] * self.dim
        tokens = self._tokens(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + min(len(token), 4) * 0.15
            vector[index] += sign * weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        return vector

    def _normalize(self, text: str) -> str:
        text = (text or "").lower()
        text = re.sub(r"\s+", "", text)
        return text

    def _tokens(self, text: str) -> List[str]:
        tokens = []
        for size in (1, 2, 3, 4):
            if len(text) < size:
                continue
            tokens.extend(text[i:i + size] for i in range(len(text) - size + 1))
        tokens.extend(re.findall(r"[a-z0-9]+", text))
        return tokens
