import unittest
from time import sleep

from src.vinted_scraper_moneybear.vintedScraper import VintedScraper
from src.vinted_scraper_moneybear.vintedWrapper import VintedWrapper


class TestQuickstarts(unittest.TestCase):
    def setUp(self):
        self.baseurl = "https://www.vinted.com"

    def test_raw_quick_start(self):
        """
        Ensure that the wrapper quickstart doesn't raise any exceptions
        """
        try:
            wrapper = VintedWrapper(self.baseurl)
            params = {"search_text": "board games"}
            items = wrapper.search(params)
            if len(items["items"]) > 0:
                wrapper.item(items["items"][0]["id"])
            else:
                # when you call multiple times the search sometimes returns an empty result
                sleep(1)
                self.test_raw_quick_start()
        except Exception as e:
            self.fail(f"Quick raised an exception: {e}")

    def test_quick_start(self):
        """
        Ensure that the scrapper quickstart doesn't raise any exceptions
        """
        try:
            scraper = VintedScraper(self.baseurl)
            params = {"search_text": "board games"}
            items = scraper.search(params)
            if len(items) > 0:
                scraper.item(items[0].id)
            else:
                # when you call multiple times the search sometimes returns an empty result
                sleep(1)
                self.test_quick_start()
        except Exception as e:
            self.fail(f"Quick raised an exception: {e}")

    def test_cookies_retry(self):
        try:
            wrapper = VintedWrapper(self.baseurl, session_cookie="invalid_cookie")
            wrapper.search()
        except Exception as e:
            self.fail(f"exception: {e}")


if __name__ == "__main__":
    unittest.main()
