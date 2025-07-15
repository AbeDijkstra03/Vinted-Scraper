import unittest
from unittest.mock import patch
import requests
from tests.utils import get_200_response, get_404_response, BASE_URL
from src.vinted_scraper_moneybear import VintedWrapper

class TestVintedWrapper(unittest.TestCase):
    @patch("requests.get", return_value=get_200_response())
    def test_wrapper_initialization(self, mock_get):
        wrapper = VintedWrapper(BASE_URL)
        self.assertEqual(wrapper.baseurl, BASE_URL)
        self.assertIsNotNone(wrapper.session_cookie)
        self.assertIsNotNone(wrapper.user_agent)
        self.assertIsNotNone(wrapper.proxies)
        mock_get.assert_called_once()

    def test_validate_baseurl(self):
        wrapper = VintedWrapper(BASE_URL)

        # Valid URL
        valid_url = "https://valid.com"
        self.assertEqual(wrapper._validate_baseurl(valid_url), "https://valid.com")

        # Invalid URL
        invalid_url = "not-a-url"
        self.assertEqual(wrapper._validate_baseurl(invalid_url), "https://www.vinted.com")

    def test_validate_cookie_prefix(self):
        wrapper = VintedWrapper(BASE_URL)

        # Valid prefix
        valid_prefix = "access_token_web="
        self.assertEqual(wrapper._validate_cookie_prefix(valid_prefix), "access_token_web=")

        # Invalid prefix
        invalid_prefix = "invalid=prefix"
        self.assertEqual(wrapper._validate_cookie_prefix(invalid_prefix), "access_token_web=")

    @patch("src.vinted_scraper_moneybear.VintedWrapper._curl")
    def test_search(self, mock_curl):
        mock_curl.return_value = {"items": [{"id": "1234"}, {"id": "5678"}]}
        wrapper = VintedWrapper(BASE_URL)

        # Perform search
        results = wrapper.search(params={"query": "dress"}, page_limit=1)
        self.assertEqual(len(results["all_items"]), 2)
        mock_curl.assert_called_once_with("/catalog/items", params={"query": "dress", "page": 1})

        # No items found
        mock_curl.return_value = {"items": []}
        results = wrapper.search(params={"query": "nonexistent"}, page_limit=1)
        self.assertEqual(len(results["all_items"]), 0)

    @patch("src.vinted_scraper_moneybear.VintedWrapper._curl")
    def test_item(self, mock_curl):
        mock_curl.return_value = {"item": {"id": "1234", "name": "Test Item"}}
        wrapper = VintedWrapper(BASE_URL)

        # Fetch item
        item_data = wrapper.item(item_id="1234")
        self.assertEqual(item_data["item"]["id"], "1234")
        mock_curl.assert_called_once_with("/items/1234", params=None)

        # Item not found
        mock_curl.return_value = None
        item_data = wrapper.item(item_id="invalid")
        self.assertIsNone(item_data)

    @patch("requests.get")
    def test_curl_success(self, mock_get):
        mock_get.return_value = get_200_response()
        wrapper = VintedWrapper(BASE_URL)

        # Successful request
        response = wrapper._curl("/catalog/items", params={"query": "dress"})
        self.assertEqual(response["items"], [{"id": "1234"}, {"id": "5678"}])
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_curl_failure(self, mock_get):
        mock_get.return_value = get_404_response()
        wrapper = VintedWrapper(BASE_URL)

        # Failed request
        response = wrapper._curl("/catalog/items", params={"query": "dress"})
        self.assertEqual(response, {"items": []})
        mock_get.assert_called_once()

    @patch("requests.get", side_effect=requests.exceptions.ConnectionError)
    def test_curl_connection_error(self, mock_get):
        wrapper = VintedWrapper(BASE_URL)

        # Connection error handling
        response = wrapper._curl("/catalog/items", params={"query": "dress"})
        self.assertEqual(response, {"items": []})
        self.assertEqual(mock_get.call_count, 3)  # Retries

    @patch("requests.get", return_value=get_200_response())
    def test_large_request_size(self, mock_get):
        wrapper = VintedWrapper(BASE_URL)

        # Exceed max request size
        large_params = {"key": "value" * 1000}  # Oversized params
        status, size = wrapper._validate_request_size(large_params)
        self.assertFalse(status)
        self.assertGreater(size, wrapper.max_request_size_kb)
