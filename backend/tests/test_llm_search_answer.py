import os
import unittest
from unittest.mock import AsyncMock, patch

from src.search.llm_answer import LLMSearchAnswerGenerator


class LLMSearchAnswerTests(unittest.IsolatedAsyncioTestCase):
    async def test_merges_answer_and_property_insights_by_listing_id(self):
        llm = AsyncMock()
        llm.ask_llm.return_value = (
            True,
            """```json
            {"answer":"Có một căn phù hợp.","properties":[
              {"listing_id":"123","explanation":"Phù hợp ngân sách.","comparison":"Giá tốt nhất."}
            ]}
            ```""",
            None,
        )
        generator = LLMSearchAnswerGenerator(llm)
        results = [{"listing_id": 123, "explanation": "fallback"}]

        with patch.dict(os.environ, {"SEARCH_USE_LLM_ANSWER": "true"}):
            answer, generated = await generator.generate("dưới 5 tỷ", {}, results)

        self.assertTrue(generated)
        self.assertEqual(answer, "Có một căn phù hợp.")
        self.assertEqual(results[0]["explanation"], "Phù hợp ngân sách.")
        self.assertEqual(results[0]["comparison"], "Giá tốt nhất.")

    async def test_keeps_deterministic_results_when_llm_fails(self):
        llm = AsyncMock()
        llm.ask_llm.return_value = (False, None, RuntimeError("offline"))
        generator = LLMSearchAnswerGenerator(llm)
        results = [{"listing_id": 123, "explanation": "fallback"}]

        with patch.dict(os.environ, {"SEARCH_USE_LLM_ANSWER": "true"}):
            answer, generated = await generator.generate("query", {}, results)

        self.assertFalse(generated)
        self.assertIsNone(answer)
        self.assertEqual(results[0]["explanation"], "fallback")


if __name__ == "__main__":
    unittest.main()
