import hashlib
import json
import math
import urllib.request
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig

HASH_EMBEDDING_DIM = 384
HASH_EMBEDDING_MODEL_NAME = "kubemind-hash-cgram-384"


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for each input text."""
        ...


class OpenAIEmbeddingProvider:
    def __init__(self, config: ModelConfig) -> None:
        self.endpoint = config.endpoint.rstrip("/")
        self.api_key = config.api_key
        self.model_name = config.model_name
        config_json = json.loads(config.config_json) if config.config_json else {}
        self.dimensions = config_json.get("dimensions", 1536)

    def embed(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.endpoint}/embeddings"
        payload = json.dumps({"model": self.model_name, "input": texts}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return [item["embedding"] for item in body["data"]]


class TFIDFEmbeddingProvider:
    """Simple character n-gram TF-IDF embedding. No external dependencies."""

    def __init__(self, corpus: list[str] | None = None) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        if corpus:
            self.fit(corpus)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = text.lower().strip()
        tokens: list[str] = []
        for ch in text:
            if ch.strip():
                tokens.append(f"c:{ch}")
        for i in range(len(text) - 1):
            a, b = text[i], text[i + 1]
            if a.strip() and b.strip():
                tokens.append(f"b:{a}{b}")
        return tokens

    def fit(self, corpus: list[str]) -> None:
        doc_count = len(corpus)
        doc_freq: dict[str, int] = {}
        for text in corpus:
            seen: set[str] = set()
            for token in self._tokenize(text):
                if token not in self.vocab:
                    self.vocab[token] = len(self.vocab)
                if token not in seen:
                    doc_freq[token] = doc_freq.get(token, 0) + 1
                    seen.add(token)
        self.idf = {
            token: math.log((doc_count + 1) / (freq + 1)) + 1
            for token, freq in doc_freq.items()
        }

    def _vectorize(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        if not tokens or not self.vocab:
            return [0.0] * max(1, len(self.vocab))
        tf: dict[int, float] = {}
        for t in tokens:
            idx = self.vocab.get(t)
            if idx is not None:
                tf[idx] = tf.get(idx, 0.0) + 1.0
        vec = [0.0] * len(self.vocab)
        for idx, count in tf.items():
            token = list(self.vocab.keys())[list(self.vocab.values()).index(idx)]
            vec[idx] = (count / len(tokens)) * self.idf.get(token, 0.0)
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(t) for t in texts]


class HashEmbeddingProvider:
    """确定性、固定维度的本地 embedding：基于字符 unigram + bigram 的 feature hashing.

    - 固定维度 (HASH_EMBEDDING_DIM)，写入 Milvus 维度永不漂移
    - 完全离线、无外部依赖、中文友好 (按字符 / 字符对统计)
    - 余弦空间下能表达基本词袋相似度，足以作为无 API key 时的兜底
    """

    def __init__(self, dim: int = HASH_EMBEDDING_DIM) -> None:
        self.dim = dim

    @staticmethod
    def _tokens(text: str) -> list[str]:
        text = (text or "").lower()
        tokens: list[str] = []
        for ch in text:
            if not ch.isspace():
                tokens.append(f"u:{ch}")
        for i in range(len(text) - 1):
            a, b = text[i], text[i + 1]
            if not a.isspace() and not b.isspace():
                tokens.append(f"b:{a}{b}")
        return tokens

    def _vectorize(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in self._tokens(text):
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "big") % self.dim
            sign = 1.0 if (h[4] & 1) else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(t) for t in texts]


def _get_active_config(db: Session, model_type: str) -> ModelConfig | None:
    return (
        db.query(ModelConfig)
        .filter(ModelConfig.model_type == model_type, ModelConfig.is_active.is_(True))
        .first()
    )


def _is_local_hash_config(config: ModelConfig) -> bool:
    return (
        config.provider == "local"
        or config.model_name == HASH_EMBEDDING_MODEL_NAME
        or not config.endpoint
    )


def get_embedding_provider(db: Session, corpus: list[str] | None = None) -> EmbeddingProvider:
    """返回 embedding provider.

    优先级：active API embedding 配置 → 本地哈希 embedding (固定维度，可写 Milvus).
    注意：不再回落 TF-IDF — TF-IDF 维度不稳定，不能用于持久化向量库。
    in-memory TF-IDF 回退由 `vector_search._tfidf_fallback` 自行直接构造。
    """
    config = _get_active_config(db, "embedding")
    if config and not _is_local_hash_config(config) and config.api_key:
        try:
            return OpenAIEmbeddingProvider(config)
        except Exception:
            pass
    return HashEmbeddingProvider()
