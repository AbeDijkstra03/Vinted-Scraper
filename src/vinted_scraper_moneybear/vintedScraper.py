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
    ):
        """
        :param baseurl: (required) Base Vinted site url to use in the requests
        :param agent: (optional) User agent to use on the requests
        :param session_cookie: (optional) Vinted session cookie
        :param proxies: (optional) Dictionary mapping protocol or protocol and
        hostname to the URL of the proxy. For more info see:
        https://requests.readthedocs.io/en/latest/user/advanced/#proxies
        """
        super().__init__(baseurl, cookie_prefix, agent, session_cookie, proxies)

    def search(self, params: Optional[Dict] = None, page_limit = 5) -> List[VintedItem]:  # type: ignore
        """
        Search for items on Vinted.

        :param params: an optional Dictionary with all the query parameters to append to the request.
            Vinted supports a search without any parameters, but to perform a search,
            you should add the `search_text` parameter.
            Default value: None.
        :return: A list of VintedItem instances representing search results.
        """
        try:
            return [VintedItem(item) for item in super().search(params, page_limit)["all_items"]]
            
        except KeyError:
            logger.error('Key "items" not found. returning an empty list.')
            return []
        
        except Exception as e:
            logger.error(f'{e}. Returning an empty list')
            return []

    def item(self, item_id: str, params: Optional[Dict] = None) -> VintedItem:  # type: ignore
        """
        Retrieve details of a specific item on Vinted.

        :param item_id: The unique identifier of the item to retrieve.
        :param params: an optional Dictionary with all the query parameters to append to the request.
            Default value: None.
        :return: A VintedItem instance representing the item's details.
        """
        try:
            return VintedItem(super().item(item_id, params)["item"])
        
        except KeyError:
            logger.error('Key "item" not found. returning an empty list.')
            return []
        
        except Exception as e:
            logger.error(f'{e}. Returning an empty list')
            return []