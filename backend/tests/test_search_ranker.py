import unittest

from src.search.query_parser import RuleBasedQueryParser
from src.search.ranker import diversify, rank_candidates


class RankerTests(unittest.TestCase):
    def test_semantic_and_target_fit_rank_first(self):
        parsed = RuleBasedQueryParser().parse("Căn hộ khoảng 5 tỷ, yên tĩnh")
        items = [
            {"listing_id": 1, "price_range": 5, "area": 70, "semantic_score": .9, "posted_date": "2026-01-01"},
            {"listing_id": 2, "price_range": 10, "area": 70, "semantic_score": .2, "posted_date": "2026-01-01"},
        ]
        ranked = rank_candidates(items, parsed)
        self.assertEqual(ranked[0]["listing_id"], 1)
        self.assertIn("semantic", ranked[0]["score_breakdown"])

    def test_diversity_caps_cluster(self):
        items = [{"listing_id": i, "geo_cluster_150m": "same", "final_score": 1 - i / 10} for i in range(5)]
        items.append({"listing_id": 99, "geo_cluster_150m": "other", "final_score": .1})
        result = diversify(items, limit=10, max_per_cluster=3)
        self.assertEqual(len([x for x in result if x["geo_cluster_150m"] == "same"]), 3)
        self.assertIn(99, [x["listing_id"] for x in result])


if __name__ == "__main__":
    unittest.main()
