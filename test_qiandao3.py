import sys
import json
import time

from curl_cffi import requests

print("=" * 60)
print("TEST QIANDAO API 3")
print("=" * 60)

url = "https://api.qiandao.com/c2c-web/v1/common/currency-spu-price-list"

headers = {
    "accept": "application/json",
    "accept-language": "en-US",
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

def test_req(method, with_body=True, update_time=False):
    h = headers.copy()
    if update_time:
        h["x-request-timestamp"] = str(int(time.time() * 1000))
        
    try:
        with requests.Session(impersonate="chrome120") as s:
            if method == "POST":
                resp = s.post(url, json=payload if with_body else None, headers=h, timeout=10)
            elif method == "GET":
                resp = s.get(url, params=payload if with_body else None, headers=h, timeout=10)
            elif method == "OPTIONS":
                resp = s.options(url, headers=h, timeout=10)
                
            print(f"[{method}] (Update Time: {update_time}) Status Code: {resp.status_code}")
            if resp.status_code == 200:
                print(resp.text[:300])
            else:
                print(f"Response: {resp.text[:300]}")
    except Exception as e:
        print(f"Error: {e}")

test_req("OPTIONS", False, False)
