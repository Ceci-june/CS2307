import unittest
from unittest.mock import patch

try:
    import torch
except ImportError:  # Local parser-only environments do not install ML dependencies.
    torch = None


@unittest.skipUnless(torch is not None, "PyTorch is not installed in this test environment")
class EmbeddingDeviceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
