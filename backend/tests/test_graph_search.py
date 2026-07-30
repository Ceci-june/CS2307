import unittest

from src.search.graph_repository import Neo4jGraphRepository
from src.search.query_parser import RuleBasedQueryParser
from src.search.ranker import WEIGHTS, rank_candidates


class GraphSearchTests(unittest.TestCase):
    def setUp(self):
        self.parser = RuleBasedQueryParser()

    def test_graph_query_uses_amenity_traversal_and_parameters(self):
        parsed = self.parser.parse(
            "Căn hộ 2PN dưới 5 tỷ, cách metro không quá 3 km, phải có ban công"
        )
        query, params = Neo4jGraphRepository._query(parsed)
        self.assertIn("NEAR_AMENITY", query)
        self.assertIn("coalesce(l.balcony, false) = true", query)
        self.assertEqual(params["amenity_category_0"], "metro")
        self.assertEqual(params["amenity_distance_0"], 3)
        self.assertIn("khong qua", parsed.protected_constraints)

    def test_near_feature_is_backed_by_graph_category(self):
        parsed = self.parser.parse("Ưu tiên căn hộ gần metro")
        candidate = Neo4jGraphRepository._score_record(
            {
                "listing_id": "123",
                "matched_features": [],
                "amenities": [{"category": "metro", "name": "Ga A"}],
                "wards": [],
            },
            parsed,
        )
        self.assertIn("near_metro", candidate["graph_evidence"]["matched_features"])
        self.assertEqual(candidate["graph_score"], 1.0)

    def test_unrelated_amenities_do_not_change_requested_score(self):
        parsed = self.parser.parse("Cách metro không quá 3 km")
        items = [
            {
                "listing_id": 1,
                "semantic_score": 0,
                "amenity_evidence": [
                    {"category": "metro", "driving_distance_km": 1.0},
                    {"category": "hospital", "driving_distance_km": 100.0},
                ],
            }
        ]
        ranked = rank_candidates(items, parsed)
        self.assertAlmostEqual(ranked[0]["score_breakdown"]["amenity"], 2 / 3, places=4)

    def test_ranking_profiles_remain_normalized(self):
        for weights in WEIGHTS.values():
            self.assertAlmostEqual(sum(weights.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
