import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
from curl_cffi import requests

print("=" * 60)
print("TEST ELDORADO API - FIND POE 1 MIRROR ID")
print("=" * 60)

ELDO_API = "https://www.eldorado.gg/api/predefinedOffers/augmentedGame/offers"
ELDO_HEADERS = {
    "authority": "www.eldorado.gg",
    "accept": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

def test_id(attr_id):
    eldo_params = {
        'gameId': '2',
        'category': 'Currency',
        'pageSize': '1',
        'pageIndex': '1',
        'offerSortingCriterion': 'Price',
        'tradeEnvironmentValue0': 'PC',
        'tradeEnvironmentValue1': 'Curse of The Allflames SC',
        'offerAttributeIdsCsv': attr_id
    }
    try:
        with requests.Session(impersonate="chrome120") as s:
            resp = s.get(ELDO_API, params=eldo_params, headers=ELDO_HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                if results:
                    attrs = results[0].get('offer', {}).get('offerAttributeIdValues', [])
                    attr_values = [str(a.get('value', '')) for a in attrs]
                    print(f"ID {attr_id} => {attr_values[0] if attr_values else 'None'}")
                    if attr_values and "Mirror of Kalandra" in attr_values[0]:
                        return attr_id
                else:
                    print(f"ID {attr_id} => No results")
            else:
                print(f"ID {attr_id} => Failed HTTP {resp.status_code}")
    except Exception as e:
        print(f"Error {attr_id}: {e}")
    return None

for i in range(0, 15):
    attr_id = f"0-{i}"
    found = test_id(attr_id)
    if found:
        print(f"\nFOUND MIRROR AT ID: {found}")
        break
