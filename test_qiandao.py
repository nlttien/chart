import requests
import json
import time

url = "https://api.qiandao.com/c2c-web/v1/common/currency-spu-price-list"
headers = {
    "accept": "application/json",
    "accept-language": "en-US",
    "authorization": "Bearer undefined",
    "content-type": "application/json",
    "origin": "https://qiandao.com",
    "referer": "https://qiandao.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "x-echo-region": "CN",
    "x-request-package-id": "1044",
    "x-request-package-sign-version": "0.0.1",
    "x-request-sign": "YWU1ZmVjOWRkZTNhODVjNzQwOTQxZjExYjY1ZTdkMWFlYTRjNDI2NmIxZDlhNGU5OGYwMjFhOGNlMTJhZmJiZg==",
    "x-request-sign-type": "HMAC_SHA256",
    "x-request-sign-version": "v1",
    "x-request-timestamp": "1784789745022"
}
payload = {
    "tagId": "1707645",
    "offset": 0,
    "limit": 20,
    "specIds": ["269615"]
}

try:
    print(f"Testing with exact signature and timestamp...")
    resp = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    else:
        print(f"Response: {resp.text}")
        
    print("\n" + "="*50 + "\n")
    print(f"Testing with updated timestamp (and old signature)...")
    headers["x-request-timestamp"] = str(int(time.time() * 1000))
    resp = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Success! Signatures might not be strictly checked or tied to timestamp.")
    else:
        print(f"Response: {resp.text}")
        
except Exception as e:
    print(f"Error: {e}")
