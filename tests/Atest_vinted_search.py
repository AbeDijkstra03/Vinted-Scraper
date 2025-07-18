import json
import unittest
from unittest.mock import Mock, patch

from src.vinted_scraper_moneybear.models import VintedItem

# isort: split
from tests.utils import (
    BASE_URL,
    read_data_from_file,
    get_200_response,
    get_scraper,
    get_wrapper,
)


class TestVintedSearch(unittest.TestCase):
    def setUp(self):
        self.baseurl = BASE_URL
        self.response_200 = get_200_response()
        self.wrapper = get_wrapper(self.baseurl)
        self.scrapper = get_scraper(self.baseurl)

    def test_raw_search_with_params(self):
        """
        Test if the search method call the _curl method with the right params
        """
        obj = {"items": []}
        self.wrapper._curl = Mock(return_value=obj)

        params = {"search_text": "games"}

        for x in [params, None]:
            self.wrapper._curl = Mock(return_value=obj)
            result = self.wrapper.search(x)
            self.wrapper._curl.assert_called_once_with("/catalog/items", params=x)
            self.assertEqual(result, obj)

    def test_search_error(self):
        """
        Test the search method.
        """
        data = read_data_from_file("search_item_dummy")
        self.response_200.content = json.dumps(data)

        with patch("requests.get", return_value=self.response_200):
            params = {"search_text": "unit_test"}
            self.assertEqual(data, self.wrapper.search(params))
            self.assertEqual(
                [VintedItem(item) for item in data["items"]],
                self.scrapper.search(params),
            )

    def test_status_code_error(self):
        """
        Test the case when a status code different from 200 is returned by the web service
        """
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}

        with patch("requests.get", return_value=mock_response):
            self.assertRaises(RuntimeError, lambda: self.wrapper.search())
