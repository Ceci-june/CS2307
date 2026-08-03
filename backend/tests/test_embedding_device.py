import os
import unittest
from unittest.mock import Mock, patch

try:
    import numpy as np
    import torch
except ImportError:  # Local parser-only environments do not install ML dependencies.
    np = None
    torch = None


@unittest.skipUnless(
    torch is not None and np is not None,
    "Embedding dependencies are not installed in this test environment",
)
class EmbeddingDeviceTests(unittest.TestCase):
    def test_local_provider_defaults_to_cpu(self):
        from src.search.embedding import E5EmbeddingModel

        with patch.dict(os.environ, {}, clear=True):
            model = E5EmbeddingModel()

        self.assertEqual(model.provider, "local")
        self.assertEqual(model.device_name, "cpu")

    def test_auto_prefers_cuda(self):
        from src.search.embedding import E5EmbeddingModel

        with patch.object(torch.cuda, "is_available", return_value=True):
            self.assertEqual(E5EmbeddingModel._resolve_device("auto").type, "cuda")

    def test_auto_uses_mps_when_cuda_is_unavailable(self):
        from src.search.embedding import E5EmbeddingModel

        with (
            patch.object(torch.cuda, "is_available", return_value=False),
            patch.object(E5EmbeddingModel, "_mps_available", return_value=True),
        ):
            self.assertEqual(E5EmbeddingModel._resolve_device("auto").type, "mps")

    def test_explicit_unavailable_cuda_falls_back_to_cpu(self):
        from src.search.embedding import E5EmbeddingModel

        with patch.object(torch.cuda, "is_available", return_value=False):
            self.assertEqual(E5EmbeddingModel._resolve_device("cuda").type, "cpu")

    @patch("src.search.embedding.requests.post")
    def test_lmstudio_calls_embeddings_api_and_normalizes_vectors(self, post):
        from src.search.embedding import E5EmbeddingModel

        first = [0.0] * 1024
        first[0] = 3.0
        first[1] = 4.0
        second = [0.0] * 1024
        second[2] = 2.0
        response = Mock()
        response.json.return_value = {
            "data": [
                {"index": 1, "embedding": second},
                {"index": 0, "embedding": first},
            ]
        }
        post.return_value = response
        with patch.dict(
            os.environ,
            {
                "SEARCH_EMBEDDING_PROVIDER": "lmstudio",
                "SEARCH_EMBEDDING_MODEL": "test-e5",
                "SEARCH_EMBEDDING_BASE_URL": "http://localhost:1234/v1",
                "SEARCH_EMBEDDING_API_KEY": "secret",
            },
            clear=True,
        ):
            model = E5EmbeddingModel()
            vectors = model.encode(["căn hộ", "nhà phố"], kind="passage")

        self.assertEqual(vectors.shape, (2, 1024))
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), [1.0, 1.0])
        post.assert_called_once_with(
            "http://localhost:1234/v1/embeddings",
            headers={"Content-Type": "application/json", "Authorization": "Bearer secret"},
            json={"model": "test-e5", "input": ["passage: căn hộ", "passage: nhà phố"]},
            timeout=60.0,
        )

    @patch("src.search.embedding.requests.post")
    def test_lmstudio_rejects_vectors_with_wrong_dimension(self, post):
        from src.search.embedding import E5EmbeddingModel

        response = Mock()
        response.json.return_value = {"data": [{"index": 0, "embedding": [1.0, 2.0]}]}
        post.return_value = response
        with patch.dict(os.environ, {"SEARCH_EMBEDDING_PROVIDER": "lmstudio"}, clear=True):
            model = E5EmbeddingModel()
            self.assertIsNone(model.encode_query("test"))

    @patch("src.search.embedding.requests.post")
    def test_lmstudio_can_request_schema_dimension(self, post):
        from src.search.embedding import E5EmbeddingModel

        response = Mock()
        response.json.return_value = {"data": [{"index": 0, "embedding": [1.0] * 1024}]}
        post.return_value = response
        with patch.dict(
            os.environ,
            {
                "SEARCH_EMBEDDING_PROVIDER": "lmstudio",
                "SEARCH_EMBEDDING_REQUEST_DIMENSIONS": "1024",
            },
            clear=True,
        ):
            model = E5EmbeddingModel()
            vectors = model.encode_query("test")

        self.assertEqual(vectors.shape, (1024,))
        self.assertEqual(post.call_args.kwargs["json"]["dimensions"], 1024)


if __name__ == "__main__":
    unittest.main()
