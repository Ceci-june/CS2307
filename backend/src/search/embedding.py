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
        self.requested_device = os.getenv("SEARCH_EMBEDDING_DEVICE", "auto").strip().lower()
        self._device = self._resolve_device(self.requested_device)
        self._tokenizer = None
        self._model = None
        self._load_failed = False
        self._lock = Lock()
        self._inference_lock = Lock()

    @staticmethod
    def _mps_available() -> bool:
        backend = getattr(torch.backends, "mps", None)
        is_available = getattr(backend, "is_available", lambda: False)
        is_built = getattr(backend, "is_built", lambda: False)
        return bool(backend and is_available() and is_built())

    @classmethod
    def _resolve_device(cls, requested: str) -> torch.device:
        requested = (requested or "auto").strip().lower()
        if requested == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            if cls._mps_available():
                return torch.device("mps")
            return torch.device("cpu")
        if requested.startswith("cuda"):
            if torch.cuda.is_available():
                try:
                    device = torch.device(requested)
                    if device.index is None or device.index < torch.cuda.device_count():
                        return device
                except (RuntimeError, ValueError):
                    pass
            logger.warning(f"Requested embedding device '{requested}' is unavailable; falling back to CPU")
            return torch.device("cpu")
        if requested == "mps":
            if cls._mps_available():
                return torch.device("mps")
            logger.warning("Requested embedding device 'mps' is unavailable; falling back to CPU")
            return torch.device("cpu")
        if requested != "cpu":
            logger.warning(f"Unknown embedding device '{requested}'; falling back to CPU")
        return torch.device("cpu")

    @property
    def device_name(self) -> str:
        return str(self._device)

    @property
    def is_gpu(self) -> bool:
        return self._device.type in {"cuda", "mps"}

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
                model = AutoModel.from_pretrained(self.model_name, **kwargs)
                try:
                    model = model.to(self._device)
                except (RuntimeError, NotImplementedError) as exc:
                    if self._device.type == "cpu":
                        raise
                    logger.warning(
                        f"Could not move embedding model to {self._device}; falling back to CPU: {exc}"
                    )
                    self._device = torch.device("cpu")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    model = model.to(self._device)
                self._model = model
                self._model.eval()
                logger.info(f"Embedding model loaded on {self._device}")
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
        inputs = {name: tensor.to(self._device) for name, tensor in inputs.items()}
        # One model instance is shared by API requests and offline batches. The lock
        # avoids overlapping inference on a single GPU and unpredictable OOM spikes.
        with self._inference_lock, torch.inference_mode():
            output = self._model(**inputs)
            embeddings = self._pool(output.last_hidden_state, inputs["attention_mask"])
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().numpy().astype("float32")

    @lru_cache(maxsize=512)
    def encode_query(self, text: str):
        result = self.encode([text], kind="query")
        return None if result is None else result[0]


embedding_model = E5EmbeddingModel()
