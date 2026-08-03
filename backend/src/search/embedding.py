from __future__ import annotations

import os
from collections import OrderedDict
from threading import Lock
from typing import List, Optional

import numpy as np
import requests
import torch
from loguru import logger
from transformers import AutoModel, AutoTokenizer


class E5EmbeddingModel:
    dimension = 1024

    def __init__(self):
        self.provider = os.getenv("SEARCH_EMBEDDING_PROVIDER", "local").strip().lower()
        if self.provider not in {"local", "lmstudio"}:
            logger.warning(f"Unknown embedding provider '{self.provider}'; falling back to local CPU")
            self.provider = "local"
        self.model_name = os.getenv("SEARCH_EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
        self.allow_download = os.getenv("SEARCH_ALLOW_MODEL_DOWNLOAD", "false").lower() in {"1", "true", "yes"}
        # CPU remains the safe default. GPU/auto selection must be explicitly enabled.
        self.requested_device = os.getenv("SEARCH_EMBEDDING_DEVICE", "cpu").strip().lower()
        self._device = self._resolve_device(self.requested_device)
        self.base_url = os.getenv("SEARCH_EMBEDDING_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")
        self.api_key = os.getenv("SEARCH_EMBEDDING_API_KEY", "").strip()
        requested_dimensions = os.getenv("SEARCH_EMBEDDING_REQUEST_DIMENSIONS", "").strip()
        try:
            self.request_dimensions = int(requested_dimensions) if requested_dimensions else None
            if self.request_dimensions is not None and self.request_dimensions <= 0:
                raise ValueError
        except ValueError:
            logger.warning("Invalid SEARCH_EMBEDDING_REQUEST_DIMENSIONS; omitting it from the request")
            self.request_dimensions = None
        try:
            self.request_timeout = float(os.getenv("SEARCH_EMBEDDING_TIMEOUT", "60"))
        except ValueError:
            logger.warning("Invalid SEARCH_EMBEDDING_TIMEOUT; using 60 seconds")
            self.request_timeout = 60.0
        self._tokenizer = None
        self._model = None
        self._load_failed = False
        self._lock = Lock()
        self._inference_lock = Lock()
        self._query_cache = OrderedDict()
        self._cache_lock = Lock()

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
        return "lmstudio-api" if self.provider == "lmstudio" else str(self._device)

    @property
    def is_gpu(self) -> bool:
        return self.provider == "local" and self._device.type in {"cuda", "mps"}

    def _load(self) -> bool:
        if self.provider == "lmstudio":
            return True
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
        if not texts:
            return None
        prefix = "query: " if kind == "query" else "passage: "
        prepared = [prefix + (text or "") for text in texts]
        if self.provider == "lmstudio":
            return self._encode_lmstudio(prepared)
        if not self._load():
            return None
        inputs = self._tokenizer(prepared, max_length=512, padding=True, truncation=True, return_tensors="pt")
        inputs = {name: tensor.to(self._device) for name, tensor in inputs.items()}
        # One model instance is shared by API requests and offline batches. The lock
        # avoids overlapping inference on a single GPU and unpredictable OOM spikes.
        with self._inference_lock, torch.inference_mode():
            output = self._model(**inputs)
            embeddings = self._pool(output.last_hidden_state, inputs["attention_mask"])
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().numpy().astype("float32")

    def _encode_lmstudio(self, texts: List[str]) -> Optional[np.ndarray]:
        endpoint = self.base_url if self.base_url.endswith("/embeddings") else f"{self.base_url}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model_name, "input": texts}
        if self.request_dimensions is not None:
            payload["dimensions"] = self.request_dimensions
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            vectors = np.asarray([item["embedding"] for item in ordered], dtype="float32")
            if vectors.ndim != 2 or vectors.shape != (len(texts), self.dimension):
                raise ValueError(
                    f"expected {len(texts)} vectors with {self.dimension} dimensions, got {vectors.shape}"
                )
            if not np.all(np.isfinite(vectors)):
                raise ValueError("LM Studio returned a non-finite embedding")
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            if np.any(norms == 0):
                raise ValueError("LM Studio returned a zero-length embedding")
            return (vectors / norms).astype("float32")
        except (requests.RequestException, AttributeError, KeyError, TypeError, ValueError) as exc:
            logger.warning(f"Semantic search disabled; LM Studio embedding request failed: {exc}")
            return None

    def encode_query(self, text: str):
        with self._cache_lock:
            cached = self._query_cache.get(text)
            if cached is not None:
                self._query_cache.move_to_end(text)
                return cached
        result = self.encode([text], kind="query")
        if result is None:
            # Do not cache transient local/LM Studio failures.
            return None
        vector = result[0]
        with self._cache_lock:
            self._query_cache[text] = vector
            self._query_cache.move_to_end(text)
            if len(self._query_cache) > 512:
                self._query_cache.popitem(last=False)
        return vector


embedding_model = E5EmbeddingModel()
