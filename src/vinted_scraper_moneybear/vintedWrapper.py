import json
import re
import time
import random
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from .utils import CookieManager, UserAgentManager, ProxyManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VintedWrapper:
    def __init__(
        self,
        baseurl: str,
        cookie_prefix: str = "_vinted_fr_session=",
        max_request_size_kb: int = 4,
        agent: Optional[str] = None,
        session_cookie: Optional[str] = None,
        proxies: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the VintedWrapper with the base URL and optional parameters.

        :param baseurl: (required) Base Vinted site URL for requests.
        :param agent: (optional) User agent to use for requests.
        :param session_cookie: (optional) Vinted session cookie.
        :param proxies: (optional) Dictionary mapping protocol and hostname to proxy URL.
        """
        self.baseurl = self._validate_baseurl(baseurl)
        self.cookie_prefix = self._validate_cookie_prefix(cookie_prefix)
        self.user_agent_manager = UserAgentManager()
        self.user_agent = agent or self.user_agent_manager.get_random_user_agent()
        self.proxy_manager = ProxyManager()
        # If there are no proxies in proxies.json, you should change this to self.proxies = proxies else None
        self.proxies = proxies or self.proxy_manager.get_random_proxy()
        self.cookie_manager = CookieManager(self.baseurl, self.user_agent, self.proxies, self.cookie_prefix)
        self.session_cookie = session_cookie or self.cookie_manager.get_random_cookie()
        self.max_request_size_kb = max_request_size_kb

    def _validate_baseurl(self, baseurl: str) -> Optional[str]:
        """Validate and return the base URL."""
        if not isinstance(baseurl, str):
            logger.warning('Baseurl must be a string. Defaulting to "https://www.vinted.com"')
            # Only works for Vinted
            return "https://www.vinted.com"
        
        baseurl = baseurl.rstrip('/')
        if not re.match(r"^(https?://)?(www\.)?[\w.-]+\.\w{2,}$", baseurl):
            logger.warning(f'{baseurl} is not a valid URL. Defaulting to "https://www.vinted.com"')
            # Only works for Vinted
            return "https://www.vinted.com"
        
        return baseurl
    
    def _validate_cookie_prefix(self, prefix: str) -> Optional[str]:
        """Validate and return the cookie prefix."""
        if not isinstance(prefix, str):
            logger.warning('Cookie prefix must be a string. Defaulting to _vinted_fr_session=')
            # Only works for Vinted
            return "_vinted_fr_session="
        
        if not re.match(r"^_[\w-]+=.*$", prefix):
            logger.warning(f'{prefix} is not a valid cookie prefix. Defaulting to _vinted_fr_session=')
            # Only works for Vinted
            return "_vinted_fr_session="
        
        return prefix
    
    def _validate_request_size(self, params: Dict) -> Tuple[bool, float]:
        """Check if the request size is within the allowed limit."""
        # Estimate request size (assuming UTF-8 encoding, each character is 1 byte)
        request_size_kb = len(json.dumps(params).encode('utf-8')) / 1024
        if request_size_kb > self.max_request_size_kb:
            logger.warning(f"Request size ({request_size_kb:.2f} KB) exceeds the maximum allowed ({self.max_request_size_kb} KB).")
            return False, request_size_kb
        return True, request_size_kb

    def search(self, params: Optional[Dict] = None, page_limit: int = 5) -> Dict[str, Dict[str, Any]]:
        """
        Search for items using the provided parameters and return a list of items.

        :param params: Optional dictionary containing search parameters.
        :param page_limit: Maximum number of pages to retrieve.
        :return: A list of dictionaries containing item details.
        """
        # starting page
        page_number = 1
        
        if not params:
            logger.error('No search parameters found. Continuing without parameters')
            params = {}
        
        if not isinstance(params, dict):
            logger.error('Parameters must be in a dictionary. Continuing without parameters')
            params = {}
            
        all_items = []

        while page_number <= page_limit:
            params['page'] = page_number
            # This endpoint only works for Vinted
            response = self._curl("/catalog/items", params=params)

            if not response:
                logger.error('No response. Breaking')
                break

            try:
                items: list[Optional[dict]] = response['items']
            
            except KeyError as e:
                logger.error(f'Key {e} does not exist in the response. Breaking')
                break
            
            if not isinstance(items, list):
                logger.error('The response must be a list (with dictionaries). Breaking')
                break
            
            # If the page has no items, it is the last page, so we break
            if not items:
                break
            
            for item in items:
                if not isinstance(item, dict):
                    logger.warning('Item is not a dictionary. Skipping this item.')
                    continue
                try:
                    # Only works for Vinted
                    item['user']['feedback_url'] = item['user']['profile_url'] + '?tab=feedback'
                except KeyError as e:
                    logger.error(f'Key {e} does not exist in the response. Breaking')
                    break
                
            all_items.extend(items)
            page_number += 1
          
        result = {'all_items' : all_items}
        logger.info(f'Successfully fetched {len(all_items)} items')
        return result

    def item(self, item_id: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Retrieve details of a specific item on Vinted.

        :param item_id: The unique identifier of the item to retrieve.
        :param params: Optional dictionary with query parameters to append to the request.
        :return: A dictionary containing the item's details.
        """
        # This endpoint only works on Vinted
        return self._curl(f"/items/{item_id}", params=params)

    def _curl(self, endpoint: str, params: Optional[Dict] = None, max_retries = 3) -> Dict[str, List[Optional[dict]]]:
        """
        Send an HTTP GET request to the specified endpoint.

        :param endpoint: The endpoint to make the request to.
        :param params: An optional dictionary with query parameters to include in the request.
        :return: A dictionary containing the parsed JSON response from the endpoint.
        """
        status, size = self._validate_request_size(params)
        if not status:
            logger.error(f"Request size too large: {size} kb. Returning dict('items': []).")
            return {"items": []}
        logger.info(f'Request size within limits: {size} kb.')
        
        headers = {
            "User-Agent": self.user_agent,
            "Cookie": f'{self.cookie_prefix}{self.session_cookie}' if self.session_cookie else None,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": self.baseurl,
            "Connection": 'close',
            "Accept-Encoding": "gzip, deflate, br"}
        
        if not endpoint:
            logger.warning('No endpoint specified. Defaulting to "/catalog/items" (Works on Vinted)')
            # Only works for Vinted and is for searching
            endpoint = "/catalog/items"
            
        if not params:
            logger.warning('No search parameters specified. Continuing without parameters')
            params = {}
            
        if not self.baseurl:
            logger.warning('No baseurl specified. Defaulting to "https://www.vinted.com"')
            self.baseurl = "https://www.vinted.com"

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    # Only works for Vinted
                    f"{self.baseurl}/api/v2{endpoint}",
                    params=params,
                    headers=headers,
                    proxies=self.proxies,
                )
                
                status_code = response.status_code

                if status_code == 200:
                    return json.loads(response.content.decode("utf-8"))
                elif status_code == 401:
                    if attempt == max_retries - 1:
                        logger.warning('Session cookie did not work. Trying without on on the last attempt')
                        headers['Cookie'] = None
                        time.sleep(random.uniform(0,1))
                        continue
                    logger.warning("Session cookie expired. Fetching a new one.")
                    self.session_cookie = self.cookie_manager.get_random_cookie()
                    headers['Cookie'] = f'{self.cookie_prefix}{self.session_cookie}' if self.session_cookie else None
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code == 400:
                    if attempt == max_retries - 1:
                        logger.warning('User agent did not work. Trying without on on the last attempt')
                        headers['User-Agent'] = None
                        time.sleep(random.uniform(0,1))
                        continue
                    logger.warning("User agent not valid. Fetching a new one.")
                    self.user_agent = self.user_agent_manager.get_random_user_agent()
                    headers['User-Agent'] = self.user_agent
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code == 403:
                    if attempt == max_retries - 1:
                        logger.warning('User agent did not work. Trying without on on the last attempt')
                        headers['User-Agent'] = None
                        time.sleep(random.uniform(0,1))
                        continue
                    logger.warning("User agent banned. Fetching a new one.")
                    self.user_agent = self.user_agent_manager.get_random_user_agent()
                    headers['User-Agent'] = self.user_agent
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code == 407:
                    if attempt == max_retries - 1:
                        logger.warning('Proxy did not work. Trying without on on the last attempt')
                        self.proxies = None
                        time.sleep(random.uniform(0,1))
                        continue
                    logger.warning("Proxy authentication failed. Fetching a new one")
                    self.proxies = self.proxy_manager.get_random_proxy()
                    time.sleep(random.uniform(0,1))
                    continue
                elif status_code in [502, 504]:
                    if attempt == max_retries - 1:
                        logger.warning('Proxy did not work. Trying without on on the last attempt')
                        self.proxies = None
                        time.sleep(random.uniform(0,1))
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
            
            except requests.exceptions.RequestException as req_err:
                logger.warning(f"Request error occurred: {req_err}. Trying again")
                time.sleep(random.uniform(0,1))
                continue

        logger.error("All attempts to fetch data failed. Returning an dict('items': [])")
        return {"items": []}