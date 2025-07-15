import json
import re
import time
import random
import logging
from cachetools import cached, TTLCache
from typing import Any, Dict, List, Optional, Tuple

import requests

from .utils import CookieManager, UserAgentManager, ProxyManager, log

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=100, ttl=300)

class VintedWrapper:
    def __init__(
        self,
        baseurl: str,
        cookie_prefix: str = "access_token_web=",
        max_request_size_kb: int = 4,
        agent: Optional[str] = None,
        session_cookie: Optional[str] = None,
        proxies: Optional[Dict[str, str]] = None,
        use_logger: bool = False
    ):
        """
        Initialize the VintedWrapper with the base URL and optional parameters.

        :param baseurl: (required) Base Vinted site URL for requests.
        :param cookie_prefix: (required) Prefix for the session cookie.
        :param max_request_size_kb: (optional) Maximum request size in kilobytes.
        :param agent: (optional) User agent to use for requests.
        :param session_cookie: (optional) Vinted session cookie.
        :param proxies: (optional) Dictionary mapping protocol and hostname to proxy URL.
        :param use_logger: (optional) Whether to use logging or not.
        """
        self.use_logger = use_logger
        self.baseurl = self._validate_baseurl(baseurl)
        self.cookie_prefix = self._validate_cookie_prefix(cookie_prefix)
        self.user_agent_manager = UserAgentManager(use_logger=self.use_logger)
        self.user_agent = agent or self.user_agent_manager.get_random_user_agent()
        self.proxy_manager = ProxyManager(use_logger=self.use_logger)
        self.proxies = proxies or self.proxy_manager.get_random_proxy()
        self.cookie_manager = CookieManager(self.baseurl, self.user_agent, self.proxies, self.cookie_prefix, 3, self.use_logger)
        self.session_cookie = session_cookie or self.cookie_manager.get_random_cookie()
        self.max_request_size_kb = max_request_size_kb
        
    @cached(cache)
    def _validate_baseurl(self, baseurl: str) -> str:
        """Validate and return the base URL."""
        if not isinstance(baseurl, str):
            log(self.use_logger, 'warning', 'Baseurl must be a string. Defaulting to "https://www.vinted.com"')
            return "https://www.vinted.com"
        
        baseurl = baseurl.rstrip('/')
        if not re.match(r"^(https?://)?(www\.)?[\w.-]+\.\w{2,}$", baseurl):
            log(self.use_logger, 'warning', f'{baseurl} is not a valid URL. Defaulting to "https://www.vinted.com"')
            return "https://www.vinted.com"
        
        if len(baseurl) > 30:
            log(self.use_logger, 'warning', f'Baseurl "{baseurl}" exceeds the maximum length of 30 characters. Defaulting to "https://www.vinted.com"')
            return "https://www.vinted.com"
        
        return baseurl
    
    @cached(cache)
    def _validate_cookie_prefix(self, prefix: str) -> str:
        """Validate and return the cookie prefix."""
        if not isinstance(prefix, str):
            log(self.use_logger, 'warning', 'Cookie prefix must be a string. Defaulting to "access_token_web="')
            return "access_token_web="
        
        if not re.match(r"^[\w-]+=.*$", prefix):
            log(self.use_logger, 'warning', f'{prefix} is not a valid cookie prefix. Defaulting to "access_token_web="')
            return "access_token_web="
        
        return prefix
    
    def _validate_request_size(self, params: Dict) -> Tuple[bool, float]:
        """Check if the request size is within the allowed limit."""
        request_size_kb = len(json.dumps(params).encode('utf-8')) / 1024
        if request_size_kb > self.max_request_size_kb:
            log(self.use_logger, 'warning', f"Request size ({request_size_kb:.2f} KB) exceeds the maximum allowed ({self.max_request_size_kb} KB).")
            return False, request_size_kb
        return True, request_size_kb
    
    def search(self, params: Optional[Dict] = None, page_limit: int = 1) -> Dict[str, Any]:
        """
        Search for items using the provided parameters and return a list of items.

        :param params: Optional dictionary containing search parameters.
        :param page_limit: Maximum number of pages to retrieve.
        :return: A dictionary containing a list of items.
        """
        page_number = 1
        params = params or {}
        
        # params = query_processor(params)

        all_items = []

        while page_number <= page_limit:
            params['page'] = page_number
            
            params_tuple = tuple(params.items())
            response = self.cached_curl("/catalog/items", params=params_tuple)

            if not response:
                log(self.use_logger, 'error', 'No response. Breaking.')
                break

            try:
                items: list[Optional[dict]] = response.get('items', [])
            except KeyError as e:
                log(self.use_logger, 'error', f'Key {e} does not exist in the response. Breaking.')
                break

            if not isinstance(items, list):
                log(self.use_logger, 'error', 'The response must be a list (with dictionaries). Breaking.')
                break

            if not items:
                break

            for item in items:
                if not isinstance(item, dict):
                    log(self.use_logger, 'warning', 'Item is not a dictionary. Skipping this item.')
                    continue
                try:
                    item['user']['feedback_url'] = item['user']['profile_url'] + '?tab=feedback'
                except KeyError as e:
                    log(self.use_logger, 'error', f'Key {e} does not exist in the item. Breaking.')
                    break
                
            all_items.extend(items)
            page_number += 1

        log(self.use_logger, 'info', f'Successfully fetched {len(all_items)} items.')
        return {'all_items': all_items}

    def item(self, item_id: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Retrieve details of a specific item on Vinted.

        :param item_id: The unique identifier of the item to retrieve.
        :param params: Optional dictionary with query parameters to append to the request.
        :return: A dictionary containing the item's details.
        """
        return self._curl(f"/items/{item_id}", params=params)

    @cached(cache)
    def cached_curl(self, endpoint: str, params: tuple, max_retries: int = 3) -> Dict[str, List[Optional[dict]]]:
        params_dict = dict(params)
        return self._curl(endpoint, params_dict, max_retries)
    
    def _curl(self, endpoint: str, params: Optional[Dict] = None, max_retries: int = 3) -> Dict[str, List[Optional[dict]]]:
        """
        Send an HTTP GET request to the specified endpoint.

        :param endpoint: The endpoint to make the request to.
        :param params: An optional dictionary with query parameters to include in the request.
        :param max_retries: Maximum number of retries for the request in case of failure.
        :return: A dictionary containing the parsed JSON response from the endpoint.
        """
        status, size = self._validate_request_size(params or {})
        if not status:
            log(self.use_logger, 'error', f"Request size too large: {size} kb. Returning dict('items': []).")
            return {"items": []}
        
        log(self.use_logger, 'info', f'Request size within limits: {size} kb.')
        
        headers = {
            "User-Agent": self.user_agent,
            "Cookie": f'{self.cookie_prefix}{self.session_cookie}' if self.session_cookie else None,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": self.baseurl,
            "Connection": 'close',
            "Accept-Encoding": "gzip, deflate, br",
        }

        for attempt in range(max_retries):
            try:
                log(self.use_logger, 'info', f'Used headers: {headers}')
                response = requests.get(
                    f"{self.baseurl}/api/v2{endpoint}",
                    params=params,
                    headers=headers,
                    proxies=self.proxies,
                )

                if response.status_code == 200:
                    return json.loads(response.content.decode("utf-8"))

                self._handle_status_code(response, headers)
            
            except requests.exceptions.ConnectionError as con_err:
                log(self.use_logger, 'warning', f"Connection error occurred: {con_err}. Trying again.")
            except requests.exceptions.RequestException as req_err:
                log(self.use_logger, 'warning', f"Request error occurred: {req_err}. Trying again.")

        log(self.use_logger, 'error', "All attempts to fetch data failed. Returning dict('items': []).")
        return {"items": []}

    def _handle_status_code(self, response, headers):
        """Handle various status codes and retry mechanisms."""
        status_code = response.status_code
        if status_code == 401:
            log(self.use_logger, 'warning', "Session cookie expired. Fetching a new one.")
            self.session_cookie = self.cookie_manager.get_random_cookie()
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

