import logging
import time
from typing import List, Dict, Any, Optional
from curl_cffi import requests

logger = logging.getLogger("g2g_engine")

API_BASE = "https://sls.g2g.com/offer/search"

HEADERS = {
    "authority": "sls.g2g.com",
    "accept": "application/json, text/plain, */*",
    "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://www.g2g.com",
    "referer": "https://www.g2g.com/",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scan_g2g_item(item_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    name = item_config.get('name', 'Unknown')
    keyword = item_config.get('keyword', '').strip().lower()
    
    logger.info(f"[G2G Engine] Scanning {name} (keyword: '{keyword}')...")
    
    params = {
        'service_id': item_config.get('service_id', ''),
        'brand_id': item_config.get('brand_id', ''),
        'filter_attr': item_config.get('filter_attr', ''),
        'sort': 'lowest_price',
        'page_size': '48',
        'group': '0',
        'currency': 'USD',
        'country': 'VN',
        'v': 'v2'
    }

    all_raw_results = []
    try:
        with requests.Session(impersonate="chrome120") as s:
            for page in range(1, 4):
                p = params.copy()
                p['page'] = str(page)
                try:
                    resp = s.get(API_BASE, params=p, headers=HEADERS, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        payload = data.get('payload', {})
                        results = payload.get('results', [])
                        if not results:
                            break
                        all_raw_results.extend(results)
                    else:
                        logger.warning(f"[G2G Engine] Page {page} returned status {resp.status_code}")
                        break
                except Exception as e:
                    logger.error(f"[G2G Engine] Error fetching page {page}: {e}")
                    break

        clean_results = []
        for item in all_raw_results:
            title = (item.get('title') or "").lower()
            description = (item.get('description') or "").lower()
            prod_name = (item.get('product_name') or "").lower()
            
            if keyword and (keyword not in title and keyword not in description and keyword not in prod_name):
                continue
                
            display_name = (
                item.get('username') or 
                item.get('user_name') or 
                item.get('seller_name') or 
                item.get('display_name') or 
                (item.get('seller', {}).get('username') if isinstance(item.get('seller'), dict) else item.get('seller')) or 
                "G2G Seller"
            )
            
            converted_unit_price = float(
                item.get('converted_unit_price') or 
                item.get('unit_price') or 
                item.get('display_price') or 0
            )
            available_qty = int(item.get('available_qty', 0))
            sold_total = int(item.get('total_success_order') or item.get('total_completed_orders') or item.get('sold_qty') or 0)
            online_status = "Online" if item.get('is_online') == 1 or item.get('is_online') is True else "Offline"
            
            if converted_unit_price > 0:
                clean_results.append({
                    'seller': str(display_name),
                    'unit_price': converted_unit_price,
                    'stock': available_qty,
                    'sold_total': sold_total,
                    'online': online_status,
                    'source': 'g2g'
                })
            
        clean_results.sort(key=lambda x: x['unit_price'])
        logger.info(f"[G2G Engine] Found {len(clean_results)} items for {name}")
        return clean_results
        
    except Exception as e:
        logger.error(f"[G2G Engine] Scan error for {name}: {e}")
        return []
