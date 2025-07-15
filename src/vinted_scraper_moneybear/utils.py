import json
import os
import random
import requests
import time
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserAgentManager:
    def __init__(self, agents_file: str = "agents.json"):
        """
        Initialize the UserAgentManager and load user agents from the specified file.
        
        :param agents_file: Path to the JSON file containing user agents.
        """
        self.agents_file = os.path.join(os.path.dirname(__file__), agents_file)
        self.user_agents = self._load_user_agents()

    def _load_user_agents(self) -> List[str]:
        """
        Load the list of user agents from the specified JSON file.
        
        The agents file should contain a list of strings like this:
        ["Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.3"]
        
        :return: A list of user agents.
        """
        try:
            if not os.path.exists(self.agents_file):
                logger.error(f"Agents file '{self.agents_file}' not found. Returning None")
                return None
            
            with open(self.agents_file, 'r') as file:
                user_agents = json.load(file)
                
                if not user_agents or not isinstance(user_agents, list):
                    logger.error(f"Agents file '{self.agents_file}' is empty or not a list. Returning None")
                    return None
                
                valid_agents = [agent for agent in user_agents if isinstance(agent, str) and agent]
                if not valid_agents:
                    logger.error(f"Agents file '{self.agents_file}' contains non valid agents. Returning None")
                    return None
                
                return valid_agents
        except Exception as e:
            logger.error(f"Error loading proxies: {e}. Returning None")
            return None

    def get_random_user_agent(self) -> str:
        """
        Get a random user agent from the loaded list.

        :return: A random user agent string.
        """
        if not self.user_agents:
            logger.error("No agents available to rotate. Will continue without agent")
            return None
        
        chosen_user_agent = random.choice(self.user_agents)
        logger.info(f'Succesfully loaded user agent, {chosen_user_agent}')
        return chosen_user_agent

class ProxyManager:
    def __init__(self, proxies_file: str = "proxies.json"):
        """
        Initialize the ProxyManager and load proxies from the specified file.
        
        :param proxies_file: Path to the JSON file containing proxy configurations.
        """
        self.proxies_source = os.path.join(os.path.dirname(__file__), proxies_file)
        self.proxies = self._load_proxies()

    def _load_proxies(self) -> List[Dict[str, str]]:
        """
        Load the list of proxies from the specified JSON file.
        
        The proxies file should contain a list of dictionaries like this:
        [{'http':'http://proxy_address', 'https':'https://proxy_address}]

        :return: A list of proxy dictionaries.
        """
        try:
            if not os.path.exists(self.proxies_source):
                logger.error(f"Proxies file '{self.proxies_source}' not found. Returning None")
                return None
            
            with open(self.proxies_source, 'r') as file:
                proxies = json.load(file)
                
                if not proxies or not isinstance(proxies, list):
                    logger.error(f"Proxies file '{self.proxies_source}' is empty or not a list. Returning None")
                    return None
                
                valid_proxies = [proxy for proxy in proxies if isinstance(proxy, dict) and proxy]
                if not valid_proxies:
                    logger.error(f"Proxies file '{self.proxies_source}' contains non valid proxy configurations. Returning None")
                    return None
                
                return valid_proxies # return the list of dictionaries with proxies.
        except Exception as e:
            logger.error(f"Error loading proxies: {e}. Returning None")
            return None

    def get_random_proxy(self) -> Dict[str, str]:
        """
        Randomly select a proxy from the loaded list of proxies.

        :return: A dictionary with 'http' and 'https' proxy URLs.
        """
        if not self.proxies:
            logger.error("No proxies available to rotate. Will continue without proxy")
            return None
        
        proxy = random.choice(self.proxies)
        logger.info(f'Succesfully fetched proxy, {proxy}')
        return proxy

class CookieManager:
    def __init__(self, baseurl: str, user_agent: str, proxies: dict[str, str], cookie_prefix: str, retries: int = 3):
        """
        Initialize the CookieManager with base URL and user agent.
        
        :param baseurl: The base URL to send the HTTP GET request to.
        :param user_agent: The User-Agent header to use in the request.
        :param retries: Number of retries for the HTTP request.
        """
        self.baseurl = baseurl
        self.cookie_prefix = cookie_prefix
        self.user_agent_manager = UserAgentManager()
        self.user_agent = user_agent or self.user_agent_manager.get_random_user_agent()
        self.proxy_manager = ProxyManager()
        self.proxies = proxies or self.proxy_manager.get_random_proxy()
        self.retries = retries

    def get_random_cookie(self) -> str | None:
        """
        Send an HTTP GET request to fetch the session cookie with retries.

        :return: The session cookie extracted from the HTTP response headers.
        """       
        headers = {"User-Agent": self.user_agent,
                   "Cookie": None,
                   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                   "Referer": self.baseurl,
                   "Connection": 'close',
                   "Accept-Encoding": "gzip, deflate, br"}
        
        for attempt in range(self.retries):
            try:
                response = requests.get(self.baseurl, headers=headers, proxies=self.proxies)
                
                status_code = response.status_code
                
                if status_code == 200:
                    try:
                        session_cookie = response.headers.get("Set-Cookie")
                        headers["Cookie"] = session_cookie # Use the new cookie on retries
                        if session_cookie and self.cookie_prefix in session_cookie:
                            logger.info("Succesfully fetched cookie.")
                            return session_cookie.split(self.cookie_prefix)[1].split(";")[0]
                        logger.warning('Invalid session cookie. Trying again')
                        time.sleep(random.uniform(0,1))
                        continue
                    except Exception as e:
                        logger.warning(e)
                        time.sleep(random.uniform(0,1))
                        continue
                elif status_code == 401:
                    if attempt == self.retries - 1:
                        logger.warning('Session cookie did not work. Trying without one on the last attempt')
                        headers['Cookie'] = None
                        time.sleep(random.uniform(0,1))
                        continue
                    logger.warning("Session cookie expired. Fetching a new one.")
                    self.session_cookie = self.get_random_cookie()
                    headers['Cookie'] = f'{self.cookie_prefix}{self.session_cookie}' if self.session_cookie else None
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code == 400:
                    if attempt == self.retries - 1:
                        logger.warning('User agent did not work. Trying without one on the last attempt')
                        headers['User-Agent'] = None
                        time.sleep(random.uniform(0,1))
                        continue
                    logger.warning("User agent not valid. Fetching a new one.")
                    self.user_agent = self.user_agent_manager.get_random_user_agent()
                    headers['User-Agent'] = self.user_agent
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code == 403:
                    if attempt == self.retries - 1:
                        logger.warning('Status code = 403. Retrying without a user agent the last attempt')
                        headers['User-Agent'] = None
                        continue
                    logger.warning("Status code = 403. Trying with a new user agent and proxy.")
                    self.proxies = self.proxy_manager.get_random_proxy()
                    self.user_agent = self.user_agent_manager.get_random_user_agent()
                    headers['User-Agent'] = self.user_agent
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code == 407:
                    if attempt == self.retries - 1:
                        logger.warning('Proxy did not work. Trying without one on the last attempt')
                        self.proxies = None
                        time.sleep(random.uniform(0,1))
                        continue
                    logger.warning("Proxy authentication failed. Fetching a new one")
                    self.proxies = self.proxy_manager.get_random_proxy()
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code in [502, 504]:
                    if attempt == self.retries - 1:
                        logger.warning('Proxy did not work. Trying without one on the last attempt')
                        self.proxies = None
                        continue
                    logger.warning(f"Proxy gateway problem {response.status_code}. Fetching a new one")
                    self.proxies = self.proxy_manager.get_random_proxy()
                    time.sleep(random.uniform(0,1))
                    continue
                    
                else:
                    logger.warning(f"Error {status_code} occurred: {response.content}. Trying again")
                    time.sleep(random.uniform(0,1))
                    continue
            
            except requests.exceptions.ConnectionError as con_err:
                logger.warning(f"Connection error occured: {con_err}. Trying again")
                time.sleep(random.uniform(0,1))
                continue              

            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(random.uniform(0,1))
                continue

        logger.error(f"Failed to fetch session cookie from {self.baseurl} after {self.retries} attempts. Returning None.")
        return None
        