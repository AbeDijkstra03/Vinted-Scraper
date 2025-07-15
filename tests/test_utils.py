import unittest
from src.vinted_scraper_moneybear.utils import query_to_filters

class TestQueryToFilters(unittest.TestCase):

    def test_query_with_size(self):
        """Test parsing size from query."""
        params = {'search_text': 'size 10'}
        updated = query_to_filters(params)
        self.assertIn('size_ids[]', updated)
        self.assertEqual(updated['size_ids[]'], ['5', '1412', '61', '1423'])

    def test_query_with_price(self):
        """Test parsing price from query."""
        params = {'search_text': '$50'}
        updated = query_to_filters(params)
        self.assertIn('price_from', updated)
        self.assertIn('price_to', updated)
        self.assertEqual(updated['price_from'], 35.0)
        self.assertEqual(updated['price_to'], 44.5)
