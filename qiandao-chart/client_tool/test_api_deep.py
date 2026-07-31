import json, re, base64, time
from curl_cffi import requests

# === 1. Test cURL trực tiếp ===
url = "https://api.qiandao.com/c2c-web/v1/currency/spu-list-v2"
headers = {
    'accept': 'application/json',
    'accept-language': 'en-US',
    'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEwMDc0MzYxODIyMzUxNjQxNDAiLCJ0eXBlIjoiVVNFUiIsImV4cCI6MTc4NTA2MDE1NSwiaWF0IjoxNzg0ODAwOTU1fQ.oT6T-yj8-8byoqPhVUnwcd32We9WWBQdTmhU6ZnS_CXrqP4C4tyWLnoPszMx9O8e4z_Lch0iQCwFuCQF9IHetqmNmAjy2BiddHtrEsqKhkuFGUlFh3T2oHZvLP_0pj-Bqmhx6sNWrXgSKsGOHtgrJDCmTpHVx5uxtozo3dJsGsTUXjHFExaL7ev2_aw8-kXB0PcHRT5yGNXgJkScBIqeQwB-jcs3WJA78xTNyO7qRMndqoFLmGv10Wsb06cdwx8YMsF8NSII_HZxyS0K0b5LEHoOCJkFZnsU6D6SdSgWkN6afIXbRWXt31vtKPIpNStQ5B7N3mIMd0NB9x1GUOBIcQ',
    'content-type': 'application/json',
    'origin': 'https://qiandao.com',
    'referer': 'https://qiandao.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    'x-echo-region': 'CN',
    'x-request-package-id': '1044',
    'x-request-package-sign-version': '0.0.1',
    'x-request-sign': 'NjQwZTU3NzY3ZGM4OTEwMWNlZWM4MjdlMzE1MmYyNWQwYTFiMGIwZmFjNzdiODkzZjMzODNlM2ExNzI2ZTljZg==',
    'x-request-sign-type': 'HMAC_SHA256',
    'x-request-sign-version': 'v1',
    'x-request-timestamp': '1784801029073',
}
body = '{"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":false,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"\u666e\u901a","value":"269603"}]}}],"sortBy":""}'

print("=== TEST 1: Original cURL (with original timestamp/sign) ===")
resp = requests.post(url, headers=headers, data=body.encode('utf-8'), impersonate="chrome120", timeout=10)
print(f"STATUS: {resp.status_code}")
resp_data = resp.json()
print(f"CODE: {resp_data.get('code')}, errCode: {resp_data.get('errCode', 'N/A')}")
if resp_data.get('code') == 0:
    data = resp_data.get('data', {})
    items = data.get('list', []) if isinstance(data, dict) else data
    print(f"ITEMS COUNT: {len(items)}")
    if items:
        print(f"FIRST ITEM KEYS: {list(items[0].keys())}")
        print(f"FIRST ITEM (truncated): {json.dumps(items[0], ensure_ascii=False)[:500]}")

# === 2. Decode JWT to check expiry ===
print("\n=== JWT TOKEN ANALYSIS ===")
jwt_token = headers['authorization'].split(' ')[1]
parts = jwt_token.split('.')
payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
payload = json.loads(base64.urlsafe_b64decode(payload_b64))
print(f"JWT Payload: {payload}")
exp_time = payload.get('exp', 0)
now = int(time.time())
remaining = exp_time - now
print(f"Token expires in: {remaining} seconds ({remaining/3600:.1f} hours)")

# === 3. Test WITHOUT x-request-sign (just JWT) ===
print("\n=== TEST 2: Without x-request-sign (just JWT token) ===")
headers_no_sign = {k: v for k, v in headers.items() if not k.startswith('x-request-sign') and k != 'x-request-timestamp'}
resp2 = requests.post(url, headers=headers_no_sign, data=body.encode('utf-8'), impersonate="chrome120", timeout=10)
print(f"STATUS: {resp2.status_code}")
resp2_data = resp2.json()
print(f"CODE: {resp2_data.get('code')}, errCode: {resp2_data.get('errCode', 'N/A')}")

# === 4. Test with NEW timestamp but SAME sign ===
print("\n=== TEST 3: New timestamp + old sign ===")
headers_new_ts = dict(headers)
headers_new_ts['x-request-timestamp'] = str(int(time.time() * 1000))
resp3 = requests.post(url, headers=headers_new_ts, data=body.encode('utf-8'), impersonate="chrome120", timeout=10)
print(f"STATUS: {resp3.status_code}")
resp3_data = resp3.json()
print(f"CODE: {resp3_data.get('code')}, errCode: {resp3_data.get('errCode', 'N/A')}")

# === 5. Decode the sign to see what it is ===
print("\n=== SIGN ANALYSIS ===")
sign_b64 = headers['x-request-sign']
sign_decoded = base64.b64decode(sign_b64).decode('utf-8')
print(f"Decoded sign (hex): {sign_decoded}")
print(f"Sign length: {len(sign_decoded)} chars = {len(sign_decoded)//2} bytes")
