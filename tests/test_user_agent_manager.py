import unittest
from src.vinted_scraper_moneybear.utils import UserAgentManager

class TestUserAgentManager(unittest.TestCase):

    def setUp(self):
        self.manager = UserAgentManager(agents_file="test_agents.json", use_logger=False)

    def test_load_valid_user_agents(self):
        """Test if valid agents are loaded properly."""
        self.assertIsNotNone(self.manager.user_agents)
        self.assertTrue(len(self.manager.user_agents) > 0)

    def test_get_random_user_agent(self):
        """Test fetching a random user agent."""
        user_agent = self.manager.get_random_user_agent()
        self.assertIsNotNone(user_agent)
        self.assertIn(user_agent, self.manager.user_agents)

    def test_no_agents_file(self):
        """Test behavior when the agents file doesn't exist."""
        manager = UserAgentManager(agents_file="nonexistent.json", use_logger=False)
        self.assertIsNone(manager.user_agents)