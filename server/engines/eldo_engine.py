import logging
import re
import time
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger("eldo_engine")

API_BASE = "https://www.eldorado.gg/api/predefinedOffers/augmentedGame/offers"
PAGE_SIZE = 30

MY_COOKIE = 'eldoradogg_currencyPreference=USD; cr-homepage-usp=1; p-checkout-test=1; cr-currency-aa=0; cr-homepage-aa=0; cr-top-up-aa=1; p-primer-update=1; curr-homepage-trending-games=1; cr-smaller-other-sellers-list=1; or-non-instant-redesign=1; p-c-badges=1; cr-top-up-swipeable=1; cr-homepage-popular-products=0; curr-offer-head-check=1; cr-tally-roblox-survey=1; it-product-aa=1; cr-topup-discount=0; p-billing-descriptor=0; it-abc=0; ac-gs-aa=1; cr-global-sec-button=0; cr-top-up-seller-reviews=0; pseudoId=14ea29d1-5f9d-42dd-bb2c-4d6b8aeb135f; cr-offer-sorting-v2=0; ac-score-p-g=1; cr-dark-theme=1; ac-more-like-v3=0; it-offer-listing-aa=0; ac-offer-listing-aa=1; ac-offer-p-aa=1; ac-price-mb=1; __Host-XSRF-TOKEN=d02a33864d608bcbfa8b55f5e9add2dd308fce976898937ffe8c4f8be751b098; eldoradogg_locale=en-US'

xsrf_match = re.search(r'__Host-XSRF-TOKEN=([a-zA-Z0-9]+)', MY_COOKIE)
XSRF_TOKEN = xsrf_match.group(1) if xsrf_match else ""

HEADERS = {
    "authority": "www.eldorado.gg",
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8",
    "referer": "https://www.eldorado.gg/",
    "origin": "https://www.eldorado.gg",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "cookie": MY_COOKIE,
    "x-xsrf-token": XSRF_TOKEN
}

def scan_eldo_item(item_config: Dict[str, Any], custom_cookie: Optional[str] = None) -> List[Dict[str, Any]]:
    name = item_config.get('name', 'Unknown')
    keyword = item_config.get('keyword', '').strip().lower()
    game_id = str(item_config.get('service_id', ''))
    server_name = item_config.get('brand_id', '')
    category = item_config.get('filter_attr', '')
    
    headers = HEADERS.copy()
    if custom_cookie:
        headers['cookie'] = custom_cookie
        xsrf = re.search(r'__Host-XSRF-TOKEN=([a-zA-Z0-9]+)', custom_cookie)
        if xsrf:
            headers['x-xsrf-token'] = xsrf.group(1)

    logger.info(f"[Eldorado Engine] Scanning {name} (Server: {server_name})...")
    
    params = {
        'gameId': game_id,
        'category': category,
        'pageSize': str(PAGE_SIZE),
        'offerSortingCriterion': 'Price'
    }

    if game_id == '2':
        params['tradeEnvironmentValue0'] = 'PC'
        params['tradeEnvironmentValue1'] = server_name
        if 'divine' in keyword:
            params['offerAttributeIdsCsv'] = '0-1'
        elif 'mirror' in keyword:
            params['offerAttributeIdsCsv'] = '0-3'
        else:
            params['offerAttributeIdsCsv'] = '0-0'
    else:
        params['tradeEnvironmentValue0'] = server_name
        if 'mirror' in keyword:
            params['offerAttributeIdsCsv'] = '0-3'
        else:
            params['offerAttributeIdsCsv'] = '0-0'

    all_raw_results = []
    try:
        for page in range(1, 3):
            p = params.copy()
            p['pageIndex'] = str(page)
            try:
                resp = requests.get(API_BASE, params=p, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get('results', [])
                    if not results:
                        break
                    all_raw_results.extend(results)
                else:
                    logger.warning(f"[Eldorado Engine] Page {page} status {resp.status_code}")
                    break
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"[Eldorado Engine] Error fetching page {page}: {e}")
                break

        clean_results = []
        for item in all_raw_results:
            offer = item.get('offer', {})
            seller_obj = item.get('seller') or item.get('user') or offer.get('seller') or offer.get('user') or {}
            seller_name = (
                (seller_obj.get('username') or seller_obj.get('userName')) if isinstance(seller_obj, dict) else seller_obj
            ) or item.get('sellerName') or item.get('userName') or item.get('sellerUsername') or offer.get('sellerName') or "Eldorado Seller"
            
            price_info = offer.get('pricePerUnit', {})
            unit_price = float(price_info.get('amount', 0))
            quantity = int(offer.get('quantity', 0))
            delivery_time = offer.get('deliveryTime', 'Instant')
            
            if unit_price > 0:
                clean_results.append({
                    'seller': str(seller_name),
                    'unit_price': unit_price,
                    'stock': quantity,
                    'sold_total': 0,
                    'online': str(delivery_time),
                    'source': 'eldorado'
                })

        clean_results.sort(key=lambda x: x['unit_price'])
        logger.info(f"[Eldorado Engine] Found {len(clean_results)} items for {name}")
        return clean_results
        
    except Exception as e:
        logger.error(f"[Eldorado Engine] Scan error for {name}: {e}")
        return []
