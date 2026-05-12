import json
import math
import urllib.request
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig


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


def _get_active_config(db: Session, model_type: str) -> ModelConfig | None:
    return (
        db.query(ModelConfig)
        .filter(ModelConfig.model_type == model_type, ModelConfig.is_active.is_(True))
        .first()
    )


def get_embedding_provider(db: Session, corpus: list[str] | None = None) -> EmbeddingProvider:
    config = _get_active_config(db, "embedding")
    if config and config.api_key:
        try:
            return OpenAIEmbeddingProvider(config)
        except Exception:
            pass
    return TFIDFEmbeddingProvider(corpus)
