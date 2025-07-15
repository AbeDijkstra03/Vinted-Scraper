import logging
from flask import Flask, request, jsonify, g, Response
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from vinted_scraper_moneybear import VintedWrapper
from vinted_scraper_moneybear.utils import log
from time import sleep
import requests
from typing import List, Dict, Optional, Any
import time
import bleach
import base64
from cachetools import cached, TTLCache
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=100, ttl=300)

use_logger = False
time_it = False

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://moneytestbear.netlify.app"}})
CSRFProtect(app)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

if time_it:
    @app.before_request
    def start_timer():
        g.start = time.time()

    @app.after_request
    def log_request(response):
        duration = time.time() - g.start
        logging.info(f"{request.remote_addr} - - [{time.strftime('%d/%b/%Y %H:%M:%S')}] \"{request.method} {request.path} HTTP/{request.environ['SERVER_PROTOCOL']}\" {response.status} {duration:.2f}s")
        return response

@cached(cache)
def sanitize_input(user_input):
        """Allow only specific tags and attributes"""
        allowed_tags = []
        allowed_attributes = {}
        return bleach.clean(user_input, tags=allowed_tags, attributes=allowed_attributes)
    
@cached(cache)
def encode_image(url: Optional[str]) -> str:
    """
    Cached image encoding function with memoization.
    Prevents redundant downloads and encoding of the same image.
    """
    if not url:
        return ''
    try:
        response = requests.get(url)
        return base64.b64encode(response.content).decode('utf-8')
    except Exception:
        return ''

def process_item(item: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Process a single item with safe nested dictionary access.
    """
    return {
        "title": item.get('title'),
        "price": (item.get('price') or {}).get('amount'),
        "currency": (item.get('price') or {}).get('currency_code'),
        # "photo": encode_image((((item.get('photo') or {}).get('thumbnails') or [{}])[-1]).get('url')),
        "photo": encode_image((item.get('photo') or {}).get('url')),
        "url": item.get('url'),
        "seller_name": (item.get('user') or {}).get('login'),
        "seller_url": (item.get('user') or {}).get('profile_url'),
        "seller_photo": encode_image(((item.get('user') or {}).get('photo') or {}).get('url')),
        "brand": item.get('brand_title'),
        "size_or_status": (item.get('item_box') or {}).get('second_line'),
        "status": item.get('status'),
    }

def parallel_process_items(filtered_items: List[Dict[Any, Any]], amount: int) -> List[Dict[str, Any]]:
    """
    Process items in parallel with optional limiting.
    
    Args:
        filtered_items: List of items to process
        amount: Maximum number of items to process
    
    Returns:
        Processed list of items
    """
    # Limit items to specified amount
    items_to_process = filtered_items[:amount]
    
    # Use ThreadPoolExecutor for I/O bound tasks like image encoding
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = list(executor.map(process_item, items_to_process))
    
    return result

@cached(cache)
def cached_main(country_suffix: str, query: str, page_limit: int, amount: int) -> Dict[str, Any]:
    sanitized_country = sanitize_input(country_suffix)
    if len(sanitized_country) > 10:
        log(use_logger, 'warning', 'Invalid country suffix. Used suffix = "com"')
        sanitized_country = 'com'
    
    try:        
        scraper = VintedWrapper(f"https://www.vinted.{sanitized_country}", use_logger=use_logger)
        log(use_logger, 'info', f'Used country suffix = {sanitized_country}')
    except Exception as e:
        scraper = VintedWrapper("https://www.vinted.com", use_logger=use_logger)
        log(use_logger, 'warning', f'{e}. Used suffix = com')

    sanitized_query = sanitize_input(query) if query else ''
    if not sanitized_query:
        log(use_logger, 'warning', 'Invalid query. Continuing without a query.')
    
    params = {"search_text": sanitized_query}

    # Set a limit on the number of retries
    max_retries = 3

    for attempt in range(max_retries):
        try:
            log(use_logger, 'info', f"Attempting to fetch items with params: {params}, page_limit: {page_limit}")
            items = scraper.search(params, page_limit)
            break  # Exit loop if successful
        except Exception as e:
            log(use_logger, 'warning', f"Error fetching items on attempt {str(attempt + 1)}: {e}")
            if attempt < max_retries - 1:  # Retry only if attempts remain
                time.sleep(2 ** attempt)  # Wait before retrying
    else:
        # This executes if the number of attempts > max_retries
        log(use_logger, 'error', 'Not been able to fetch items. Returning an empty list')
        return []

    try:
        # Ensure amount does not exceed the number of available items
        amount = min(amount, len(items.get('all_items', [])))
        
        filtered_items = [item for item in items.get('all_items', []) if isinstance(item, dict)]
        
        # Extract item details if there are items available
        result = parallel_process_items(filtered_items, amount)
        
        result.insert(0, {'responses_count': len(filtered_items)})

        # Check if the result is empty after processing
        if not result:
            log(use_logger, 'error', 'No valid items found. Returning an empty list')
            return []
        
    except KeyError as e:
        log(use_logger, 'error', f'Key {e} does not exist. Returning an empty list')
        return []
    
    except Exception as e:
        log(use_logger, 'error', f'{e}. Returning an empty list')
        return []

    return result

@app.route('/', methods=['GET'])
def main() -> Response:
    country_suffix = request.args.get('country', 'com')
    query = request.args.get('query', '')
    try:
        page_limit = int(request.args.get('page_limit', 1))
        page_limit = min(10, page_limit)
    except ValueError:
        log(use_logger, 'warning', '"page_limit" should be an integer. Defaulting to 1.')
        page_limit = 1

    try:
        amount = int(request.args.get('amount', 1))
        amount = min(100, amount)
    except ValueError:
        log(use_logger, 'warning', '"amount" should be an integer. Defaulting to 1.')
        amount = 1

    result = cached_main(country_suffix, query, page_limit, amount)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=False)
