"""
Debug script: Test G2G and Eldorado API for Chaos Orb
"""
import json
import re
import sys
import os

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

from curl_cffi import requests

# ============= G2G TEST =============
print("=" * 60)
print("TEST 1: G2G API - PoE 1 Chaos Orb")
print("=" * 60)

G2G_API = "https://sls.g2g.com/offer/search"
G2G_HEADERS = {
    "authority": "sls.g2g.com",
    "accept": "application/json, text/plain, */*",
    "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://www.g2g.com",
    "referer": "https://www.g2g.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

g2g_params = {
    'service_id': 'lgc_service_1',
    'brand_id': 'lgc_game_19398',
    'filter_attr': 'lgc_19398_server:lgc_19398_server_63274|lgc_19398_tier:lgc_19398_tier_42689',
    'sort': 'lowest_price',
    'page_size': '10',
    'page': '1',
    'group': '0',
    'currency': 'USD',
    'country': 'VN',
    'v': 'v2'
}

try:
    with requests.Session(impersonate="chrome120") as s:
        print("\n--- Test with group=0 ---")
        resp = s.get(G2G_API, params=g2g_params, headers=G2G_HEADERS, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('payload', {}).get('results', [])
            print(f"Results count (group=0): {len(results)}")
            
            if results:
                for i, item in enumerate(results[:3]):
                    title = item.get('title', 'N/A')
                    prod = item.get('product_name', 'N/A')
                    price = item.get('converted_unit_price') or item.get('unit_price')
                    seller = item.get('username', 'N/A')
                    print(f"\n  [{i+1}] Seller: {seller}")
                    print(f"      Title: {title}")
                    print(f"      Product Name: {prod}")
                    print(f"      Price: {price}")
                    
                    kw = "chaos orb"
                    match_title = kw in title.lower()
                    match_prod = kw in prod.lower()
                    print(f"      Keyword '{kw}' in title? {match_title}")
                    print(f"      Keyword '{kw}' in product_name? {match_prod}")
            else:
                print("  -> NO RESULTS with group=0!")
        else:
            print(f"Response: {resp.text[:300]}")
            
        # Also test with group=1
        print("\n--- Test with group=1 ---")
        g2g_params2 = g2g_params.copy()
        g2g_params2['group'] = '1'
        resp2 = s.get(G2G_API, params=g2g_params2, headers=G2G_HEADERS, timeout=15)
        print(f"HTTP Status: {resp2.status_code}")
        if resp2.status_code == 200:
            data2 = resp2.json()
            results2 = data2.get('payload', {}).get('results', [])
            print(f"Results count (group=1): {len(results2)}")
            if results2:
                for i, item in enumerate(results2[:3]):
                    title = item.get('title', 'N/A')
                    prod = item.get('product_name', 'N/A')
                    price = item.get('converted_unit_price') or item.get('unit_price')
                    seller = item.get('username', 'N/A')
                    print(f"\n  [{i+1}] Seller: {seller}")
                    print(f"      Title: {title}")
                    print(f"      Product Name: {prod}")
                    print(f"      Price: {price}")
                    
                    kw = "chaos orb"
                    match_title = kw in title.lower()
                    match_prod = kw in prod.lower()
                    print(f"      Keyword '{kw}' in title? {match_title}")
                    print(f"      Keyword '{kw}' in product_name? {match_prod}")
            else:
                print("  -> NO RESULTS with group=1 either!")
                
        # Also test without keyword filter (empty keyword)
        print("\n--- Test without keyword filter ---")
        print("(If the tier filter already narrows to chaos, keyword may be unnecessary)")
                
except Exception as e:
    print(f"G2G ERROR: {e}")
    import traceback
    traceback.print_exc()


# ============= ELDORADO TEST =============
print("\n\n" + "=" * 60)
print("TEST 2: ELDORADO API - PoE 1 Chaos Orb")
print("=" * 60)

try:
    eldo_client_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eldo-chart", "client_tool", "sniper_client.py")
    with open(eldo_client_path, "r", encoding="utf-8") as f:
        content = f.read()
    cookie_match = re.search(r"MY_COOKIE\s*=\s*['\"](.+?)['\"]", content)
    MY_COOKIE = cookie_match.group(1) if cookie_match else ""
    xsrf_match = re.search(r'__Host-XSRF-TOKEN=([a-zA-Z0-9]+)', MY_COOKIE)
    XSRF_TOKEN = xsrf_match.group(1) if xsrf_match else ""
    print(f"Cookie loaded: {'YES' if MY_COOKIE else 'NO'}")
    print(f"XSRF Token: {'YES' if XSRF_TOKEN else 'NO'}")
except Exception as e:
    MY_COOKIE = ""
    XSRF_TOKEN = ""
    print(f"WARNING: Cannot load Eldorado cookie: {e}")

ELDO_API = "https://www.eldorado.gg/api/predefinedOffers/augmentedGame/offers"
ELDO_HEADERS = {
    "authority": "www.eldorado.gg",
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8",
    "referer": "https://www.eldorado.gg/",
    "origin": "https://www.eldorado.gg",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "cookie": MY_COOKIE,
    "x-xsrf-token": XSRF_TOKEN
}

eldo_params = {
    'gameId': '2',
    'category': 'Currency',
    'pageSize': '10',
    'pageIndex': '1',
    'offerSortingCriterion': 'Price',
    'tradeEnvironmentValue0': 'PC',
    'tradeEnvironmentValue1': 'Curse of The Allflames SC',
    'offerAttributeIdsCsv': '0-0'
}

try:
    with requests.Session(impersonate="chrome120") as s:
        print(f"\n--- Test offerAttributeIdsCsv=0-0 ---")
        resp = s.get(ELDO_API, params=eldo_params, headers=ELDO_HEADERS, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            print(f"Results count: {len(results)}")
            
            if results:
                keyword = "Chaos Orb"
                chaos_found = 0
                all_attr_values = set()
                
                for i, item in enumerate(results[:10]):
                    offer = item.get('offer', {})
                    user = item.get('user', {})
                    
                    attrs = offer.get('offerAttributeIdValues', [])
                    attr_values = [str(a.get('value', '')) for a in attrs]
                    for v in attr_values:
                        all_attr_values.add(v)
                    
                    price_obj = offer.get('pricePerUnit', {})
                    price = price_obj.get('amount', 0)
                    
                    if i < 3:
                        print(f"\n  [{i+1}] Seller: {user.get('username', 'N/A')}")
                        print(f"      Price: ${price}")
                        print(f"      Attributes: {attr_values}")
                    
                    is_match = any(keyword.lower() == v.lower() for v in attr_values)
                    if is_match:
                        chaos_found += 1
                
                print(f"\n  -> Chaos Orb matched: {chaos_found}/{min(10, len(results))}")
                print(f"  -> ALL unique attribute values in results: {all_attr_values}")
                
                if chaos_found == 0:
                    print("  -> KEYWORD MISMATCH! Need to find correct keyword.")
            else:
                print("  -> NO RESULTS!")
        else:
            print(f"Response: {resp.text[:300]}")
except Exception as e:
    print(f"ELDORADO ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n\nDONE!")
