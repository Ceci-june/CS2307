from __future__ import annotations

import os
from functools import lru_cache
from threading import Lock
from typing import List, Optional

import numpy as np
import torch
from loguru import logger
from transformers import AutoModel, AutoTokenizer


class E5EmbeddingModel:
    dimension = 1024

    def __init__(self):
        self.model_name = os.getenv("SEARCH_EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
        self.allow_download = os.getenv("SEARCH_ALLOW_MODEL_DOWNLOAD", "false").lower() in {"1", "true", "yes"}
        self._tokenizer = None
        self._model = None
        self._load_failed = False
        self._lock = Lock()

    def _load(self) -> bool:
        if self._model is not None:
            return True
        if self._load_failed:
            return False
        with self._lock:
            if self._model is not None:
                return True
            try:
                kwargs = {"local_files_only": not self.allow_download}
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, **kwargs)
                self._model = AutoModel.from_pretrained(self.model_name, **kwargs)
                self._model.eval()
                return True
            except Exception as exc:
                self._load_failed = True
                logger.warning(f"Semantic search disabled; embedding model unavailable: {exc}")
                return False

    @staticmethod
    def _pool(last_hidden_state, attention_mask):
        mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        return (last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9)

    def encode(self, texts: List[str], kind: str = "query") -> Optional[np.ndarray]:
        if not texts or not self._load():
            return None
        prefix = "query: " if kind == "query" else "passage: "
        prepared = [prefix + (text or "") for text in texts]
        inputs = self._tokenizer(prepared, max_length=512, padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            output = self._model(**inputs)
        embeddings = self._pool(output.last_hidden_state, inputs["attention_mask"])
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().numpy().astype("float32")

    @lru_cache(maxsize=512)
    def encode_query(self, text: str):
        result = self.encode([text], kind="query")
        return None if result is None else result[0]


embedding_model = E5EmbeddingModel()

