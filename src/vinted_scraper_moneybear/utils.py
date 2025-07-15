import json
import os
import random
import requests
import time
import logging
from cachetools import cached, TTLCache
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=100, ttl=300)

def log(use_logger: bool, level: str, message: str):
    """Log a message only if logging is enabled."""
    if use_logger:
        getattr(logger, level)(message)
        
class UserAgentManager:
    def __init__(self, agents_file: str = "agents.json", use_logger: bool = True):
        """
        Initialize the UserAgentManager and load user agents from the specified file.
        
        :param agents_file: Path to the JSON file containing user agents.
        :param use_logger: Whether to enable logging.
        """
        self.agents_file = os.path.join(os.path.dirname(__file__), agents_file)
        self.use_logger = use_logger
        self.user_agents = self._load_user_agents()

    @cached(cache)
    def _load_user_agents(self) -> Optional[List[str]]:
        """
        Load the list of user agents from the specified JSON file.
        
        :return: A list of user agents or None if loading fails.
        """
        try:
            if not os.path.exists(self.agents_file):
                log(self.use_logger, "error", f"Agents file '{self.agents_file}' not found. Returning None.")
                return None

            with open(self.agents_file, 'r') as file:
                user_agents = json.load(file)
                if not user_agents or not isinstance(user_agents, list):
                    log(self.use_logger, "error", f"Agents file '{self.agents_file}' is empty or not a list. Returning None.")
                    return None

                valid_agents = [agent for agent in user_agents if isinstance(agent, str) and agent]
                if not valid_agents:
                    log(self.use_logger, "error", f"Agents file '{self.agents_file}' contains invalid entries. Returning None.")
                    return None
                
                return valid_agents

        except Exception as e:
            log(self.use_logger, "error", f"Error loading user agents: {e}. Returning None.")
            return None

    def get_random_user_agent(self) -> Optional[str]:
        """
        Get a random user agent from the loaded list.
        
        :return: A random user agent string or None if no agents are available.
        """
        if not self.user_agents:
            log(self.use_logger, "error", "No agents available to rotate. Returning None.")
            return None
        
        chosen_user_agent = random.choice(self.user_agents)
        log(self.use_logger, "info", f"Successfully selected user agent: {chosen_user_agent}")
        return chosen_user_agent


class ProxyManager:
    def __init__(self, proxies_file: str = "proxies.json", use_logger: bool = True):
        """
        Initialize the ProxyManager and load proxies from the specified file.
        
        :param proxies_file: Path to the JSON file containing proxy configurations.
        :param use_logger: Whether to enable logging.
        """
        self.proxies_source = os.path.join(os.path.dirname(__file__), proxies_file)
        self.use_logger = use_logger
        self.proxies = self._load_proxies()

    @cached(cache)
    def _load_proxies(self) -> Optional[List[Dict[str, str]]]:
        """
        Load the list of proxies from the specified JSON file.
        
        :return: A list of proxy dictionaries or None if loading fails.
        """
        try:
            if not os.path.exists(self.proxies_source):
                log(self.use_logger, "error", f"Proxies file '{self.proxies_source}' not found. Returning None.")
                return None

            with open(self.proxies_source, 'r') as file:
                proxies = json.load(file)
                if not proxies or not isinstance(proxies, list):
                    log(self.use_logger, "warning", f"Proxies file '{self.proxies_source}' is empty or not a list. Returning None.")
                    return None

                valid_proxies = [proxy for proxy in proxies if isinstance(proxy, dict) and proxy]
                if not valid_proxies:
                    log(self.use_logger, "warning", f"Proxies file '{self.proxies_source}' contains invalid entries. Returning None.")
                    return None

                return valid_proxies

        except Exception as e:
            log(self.use_logger, "error", f"Error loading proxies: {e}. Returning None.")
            return None

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get a random proxy from the loaded list.
        
        :return: A dictionary with 'http' and 'https' proxy URLs or None if no proxies are available.
        """
        if not self.proxies:
            log(self.use_logger, "error", "No proxies available to rotate. Returning None.")
            return None
        
        proxy = random.choice(self.proxies)
        log(self.use_logger, "info", f"Successfully selected proxy: {proxy}")
        return proxy


class CookieManager:
    def __init__(
        self,
        baseurl: str,
        user_agent: Optional[str],
        proxies: Optional[Dict[str, str]],
        cookie_prefix: str,
        retries: int = 3,
        use_logger: bool = True
    ):
        """
        Initialize the CookieManager with base URL and user agent.
        
        :param baseurl: The base URL to send the HTTP GET request to.
        :param user_agent: The User-Agent header to use in the request.
        :param proxies: Optional proxies for the requests.
        :param cookie_prefix: The prefix for the session cookie.
        :param retries: Number of retries for the HTTP request.
        :param use_logger: Whether to enable logging.
        """
        self.baseurl = baseurl
        self.cookie_prefix = cookie_prefix
        self.use_logger = use_logger
        self.retries = retries
        self.user_agent_manager = UserAgentManager(use_logger=use_logger)
        self.user_agent = user_agent or self.user_agent_manager.get_random_user_agent()
        self.proxy_manager = ProxyManager(use_logger=use_logger)
        self.proxies = proxies or self.proxy_manager.get_random_proxy()
        self.session_cookie = None  # Initialize session cookie

    def get_random_cookie(self) -> Optional[str]:
        """
        Send an HTTP GET request to fetch the session cookie with retries.
        
        :return: The session cookie or None if an error occurs.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": self.baseurl,
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br",
        }

        for attempt in range(self.retries):
            try:
                response = requests.get(self.baseurl, headers=headers, proxies=self.proxies)
                status_code = response.status_code

                if status_code == 200:
                    session_cookie = response.headers.get("Set-Cookie")
                    headers["Cookie"] = session_cookie
                    
                    if session_cookie and self.cookie_prefix in session_cookie:
                        log(self.use_logger, "info", "Successfully fetched session cookie.")
                        return session_cookie.split(self.cookie_prefix)[1].split(";")[0]
                    
                    log(self.use_logger, "warning", "Invalid session cookie. Retrying...")

                self._handle_status_code(response, headers)

            except requests.exceptions.ConnectionError as con_err:
                log(self.use_logger, "warning", f"Connection error: {con_err}. Retrying...")

            except requests.RequestException as e:
                log(self.use_logger, "warning", f"Request failed (attempt {attempt + 1}): {e}. Retrying...")

        log(self.use_logger, "error", f"Failed to fetch session cookie after {self.retries} attempts. Returning None.")
        return None
    
    def _handle_status_code(self, response, headers):
        """Handle various status codes and retry mechanisms."""
        status_code = response.status_code
        if status_code == 401:
            log(self.use_logger, 'warning', "Session cookie expired. Fetching a new one.")
            self.session_cookie = self.get_random_cookie()
            headers['Cookie'] = f'{self.cookie_prefix}{self.session_cookie}' if self.session_cookie else None
        elif status_code in [400, 403]:
            log(self.use_logger, 'warning', f"User agent issue ({status_code}). Fetching a new one.")
            self.user_agent = self.user_agent_manager.get_random_user_agent()
            headers['User-Agent'] = self.user_agent
        elif status_code == 407:
            log(self.use_logger, 'warning', "Proxy authentication failed. Fetching a new proxy.")
            self.proxies = self.proxy_manager.get_random_proxy()
        elif status_code in [502, 504]:
            log(self.use_logger, 'warning', "Gateway issue. Fetching a new proxy.")
            self.proxies = self.proxy_manager.get_random_proxy()
        else:
            log(self.use_logger, 'warning', f"Unexpected error {status_code}. Retrying.")