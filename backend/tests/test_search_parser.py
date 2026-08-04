import unittest

from src.search.query_parser import RuleBasedQueryParser
from src.search.schemas import RankingProfile


class QueryParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = RuleBasedQueryParser()

    def test_hybrid_query(self):
        parsed = self.parser.parse(
            "Tìm căn hộ 2PN dưới 5 tỷ ở Thủ Đức, cách metro không quá 3 km, "
            "ưu tiên yên tĩnh và nhiều cây xanh"
        )
        self.assertEqual(parsed.hard_filters.property_types, ["Căn hộ"])
        self.assertEqual(parsed.hard_filters.bedrooms.min, 2)
        self.assertEqual(parsed.hard_filters.price.max, 5)
        self.assertIn("Thành Phố Thủ Đức", parsed.hard_filters.former_admin_areas)
        self.assertIn("Quận 9", parsed.hard_filters.former_admin_areas)
        self.assertEqual(parsed.amenity_filters[0].amenity_category, "metro")
        self.assertEqual(parsed.amenity_filters[0].max_driving_distance_km, 3)

    def test_district_name_without_old_keyword_uses_former_area(self):
        parsed = self.parser.parse("tôi muốn mua nàh quận 2")
        self.assertEqual(parsed.hard_filters.districts, [])
        self.assertEqual(parsed.hard_filters.former_admin_areas, ["Quận 2"])

    def test_old_huyen_and_city_are_former_areas(self):
        huyen = self.parser.parse("mua nhà huyện hóc môn")
        city = self.parser.parse("căn hộ thành phố dĩ an")
        self.assertEqual(huyen.hard_filters.districts, [])
        self.assertEqual(huyen.hard_filters.former_admin_areas, ["Huyện Hoc Mon"])
        self.assertEqual(city.hard_filters.districts, [])
        self.assertEqual(city.hard_filters.former_admin_areas, ["Thành Phố Di An"])

    def test_units_and_required_feature(self):
        parsed = self.parser.parse("Nhà đất dưới 5000 triệu, diện tích trên 80 m2, phải có ban công")
        self.assertEqual(parsed.hard_filters.price.max, 5)
        self.assertEqual(parsed.hard_filters.area.min, 80)
        self.assertIn("balcony", parsed.hard_filters.required_features)

    def test_negative_property_type(self):
        parsed = self.parser.parse("Bất động sản dưới 6 tỷ, không lấy nhà đất")
        self.assertEqual(parsed.hard_filters.excluded_property_types, ["Nhà đất"])

    def test_explicit_filters_override_query(self):
        parsed = self.parser.parse(
            "Tìm nơi ở yên tĩnh",
            explicit_filters={"max_price": 4.5, "district": "Phường An Khánh", "pool": True},
        )
        self.assertEqual(parsed.hard_filters.price.max, 4.5)
        self.assertEqual(parsed.hard_filters.districts, ["Phường An Khánh"])
        self.assertIn("pool", parsed.hard_filters.required_features)

    def test_family_profile(self):
        parsed = self.parser.parse("Căn hộ phù hợp gia đình trẻ gần trường học")
        self.assertEqual(parsed.ranking_profile, RankingProfile.FAMILY)

    def test_maximum_distance_is_not_a_negative_preference(self):
        parsed = self.parser.parse("Căn hộ cách metro không quá 3 km")
        self.assertEqual(parsed.negative_preferences, [])


if __name__ == "__main__":
    unittest.main()
