from typing import Dict, List, Optional

from .models import VintedItem
from .vintedWrapper import VintedWrapper

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VintedScraper(VintedWrapper):
    def __init__(
        self,
        baseurl: str,
        cookie_prefix: str = "_vinted_fr_session=",
        agent: Optional[str] = None,
        session_cookie: Optional[str] = None,
        proxies: Optional[Dict[str, str]] = None,
        use_logger: bool = False
    ):
        """
        :param baseurl: (required) Base Vinted site URL to use in the requests.
        :param cookie_prefix: (optional) Prefix for the session cookie.
        :param agent: (optional) User agent to use for the requests.
        :param session_cookie: (optional) Vinted session cookie.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
        hostname to the URL of the proxy.
        :param use_logger: (optional) Boolean to enable/disable logging.
        """
        super().__init__(baseurl, cookie_prefix, 4, agent, session_cookie, proxies, use_logger)
        self.use_logger = use_logger

    def _log(self, level: str, message: str):
        """Log a message only if logging is enabled."""
        if self.use_logger:
            getattr(logger, level)(message)

    def search(self, params: Optional[Dict] = None, page_limit: int = 5) -> List[VintedItem]: # type: ignore
        """
        Search for items on Vinted.

        :param params: Optional dictionary with query parameters for the request.
            Vinted supports a search without any parameters, but for targeted searches,
            you should use parameters like 'search_text'.
        :param page_limit: Maximum number of pages to fetch (default is 5).
        :return: A list of VintedItem instances representing search results.
        """
        try:
            items = super().search(params, page_limit)["all_items"]
            return [VintedItem(item) for item in items]
        
        except KeyError:
            self._log('error', 'Key "items" not found in the search results. Returning an empty list.')
            return []
        
        except Exception as e:
            self._log('error', f'Error during search: {e}. Returning an empty list.')
            return []

    def item(self, item_id: str, params: Optional[Dict] = None) -> Optional[VintedItem]: # type: ignore
        """
        Retrieve details of a specific item on Vinted.

        :param item_id: The unique identifier of the item to retrieve.
        :param params: Optional dictionary with additional query parameters for the request.
        :return: A VintedItem instance representing the item's details, or None if an error occurs.
        """
        try:
            item_data = super().item(item_id, params)["item"]
            return VintedItem(item_data)
        
        except KeyError:
            self._log('error', 'Key "item" not found in the item details. Returning None.')
            return None
        
        except Exception as e:
            self._log('error', f'Error retrieving item {item_id}: {e}. Returning None.')
            return None
