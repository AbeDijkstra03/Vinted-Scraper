import unittest
from src.vinted_scraper_moneybear.utils import ProxyManager

class TestProxyManager(unittest.TestCase):

    def setUp(self):
        self.manager = ProxyManager(proxies_file="test_proxies.json", use_logger=False)

    def test_load_valid_proxies(self):
        """Test if valid proxies are loaded properly."""
        proxy = self.manager.get_random_proxy()
        self.assertIsNotNone(proxy)
        self.assertTrue(len(proxy) > 0)

    def test_get_random_proxy(self):
        """Test fetching a random proxy."""
        proxy = self.manager.get_random_proxy()
        self.assertIsNotNone(proxy)
        self.assertIn(proxy, self.manager.proxies)

    def test_no_proxies_file(self):
        """Test behavior when the proxies file doesn't exist."""
        manager = ProxyManager(proxies_file="nonexistent.json", use_logger=False)
        self.assertIsNone(manager.proxies)

