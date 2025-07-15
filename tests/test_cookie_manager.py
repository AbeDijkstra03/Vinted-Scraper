import unittest
from src.vinted_scraper_moneybear.utils import CookieManager

class TestCookieManager(unittest.TestCase):

    def setUp(self):
        self.manager = CookieManager(
            baseurl="https://vinted.com",
            user_agent=None,
            proxies=None,
            cookie_prefix="access_token_web=",
            retries=2,
            use_logger=False
        )

    def test_get_random_cookie(self):
        """Test if a cookie is fetched successfully."""
        cookie = self.manager.get_random_cookie()
        self.assertIsNotNone(cookie)
        self.assertTrue(len('cookie') > 0)
