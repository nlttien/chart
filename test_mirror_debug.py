import json
import re
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
from curl_cffi import requests

print("=" * 60)
print("TEST ELDORADO API - PoE 2 Mirror")
print("=" * 60)

try:
    eldo_client_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eldo-chart", "client_tool", "sniper_client.py")
    with open(eldo_client_path, "r", encoding="utf-8") as f:
        content = f.read()
    cookie_match = re.search(r"MY_COOKIE\s*=\s*['\"](.+?)['\"]", content)
    MY_COOKIE = cookie_match.group(1) if cookie_match else ""
    xsrf_match = re.search(r'__Host-XSRF-TOKEN=([a-zA-Z0-9]+)', MY_COOKIE)
    XSRF_TOKEN = xsrf_match.group(1) if xsrf_match else ""
except Exception as e:
    MY_COOKIE = ""
    XSRF_TOKEN = ""

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

# The link: https://www.eldorado.gg/poe-2-currency/g/220?path-of-exile-2-orbs=mirror-of-kalandra&te_v0=Runes%20of%20Aldur%20Standard&offerSortingCriterion=Cheapest
eldo_params = {
    'gameId': '220',
    'category': 'Currency',
    'pageSize': '20',
    'pageIndex': '1',
    'offerSortingCriterion': 'Price',
    'tradeEnvironmentValue0': 'Runes of Aldur Standard',
    'offerAttributeIdsCsv': '0-0'
}

try:
    with requests.Session(impersonate="chrome120") as s:
        resp = s.get(ELDO_API, params=eldo_params, headers=ELDO_HEADERS, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            print(f"Results count: {len(results)}")
            
            if results:
                keyword = "Mirror of Kalandra"
                mirror_found = 0
                all_attr_values = set()
                
                for i, item in enumerate(results):
                    offer = item.get('offer', {})
                    user = item.get('user', {})
                    
                    attrs = offer.get('offerAttributeIdValues', [])
                    attr_values = [str(a.get('value', '')) for a in attrs]
                    for v in attr_values:
                        all_attr_values.add(v)
                    
                    price_obj = offer.get('pricePerUnit', {})
                    price = price_obj.get('amount', 0)
                    
                    # Print first 5 items to see what they look like
                    if i < 5:
                        print(f"\n  [{i+1}] Seller: {user.get('username', 'N/A')}")
                        print(f"      Price: ${price}")
                        print(f"      Attributes: {attr_values}")
                    
                    is_match = any(keyword.lower() == v.lower() for v in attr_values)
                    if is_match:
                        mirror_found += 1
                
                print(f"\n  -> '{keyword}' matched: {mirror_found}/{len(results)}")
                print(f"  -> ALL unique attribute values in first page: {all_attr_values}")
                
            else:
                print("  -> NO RESULTS!")
        else:
            print(f"Response: {resp.text[:300]}")
except Exception as e:
    print(f"ELDORADO ERROR: {e}")
