import hashlib, hmac, base64, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')
from curl_cffi import requests

SKEY = "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"
API_URL = "https://api.qiandao.com/c2c-web/v1/currency/buy-direction/spu-list-v2"
API_PATH = "/c2c-web/v1/currency/buy-direction/spu-list-v2"
JWT_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEwMDc0MzYxODIyMzUxNjQxNDAiLCJ0eXBlIjoiVVNFUiIsImV4cCI6MTc4NTA1OTc0OCwiaWF0IjoxNzg0ODAwNTQ4fQ.IeattRTmjB8vl1Jt4qm6eI0Mb-T9VedS3VaI8V5qhwhNjntw2y346RBkVxcgPe2Muqq8HdkYh5g-_aY9kExLMYlAzpVNLl3-vb55Uu58Hr4a002DHkU4yFZtskFfc39MgwhzPI_zx_XsVzp1RzP0wmEmIYBfYOg4qOU-ho4dU7bOgFKDX-wdWlrjmddPUuoPLSFD-mjbcgoDu3SSh6RTn6u0C7Y2ll4fDbZy5JBg85RQhoKspKlUEklsCrku4FJnzN3AbZPuQQeJVoBNZAuQUwci5ESNHMXr9tlaFoXKbr4nshZFKbH4W4dAa3CvRTTrZub-QAgqegISock7ivESIA"

def generate_sign(path, timestamp_ms):
    msg = path + str(timestamp_ms)
    hex_hash = hmac.new(SKEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    return base64.b64encode(hex_hash.encode('utf-8')).decode('utf-8')

body = {"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":False,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"\u666e\u901a","value":"269603"}]}}],"sortBy":"BEST_RATIO"}

timestamp = str(int(time.time() * 1000))
sign = generate_sign(API_PATH, timestamp)

headers = {
    'accept': 'application/json',
    'content-type': 'application/json',
    'authorization': f'Bearer {JWT_TOKEN}',
    'origin': 'https://qiandao.com',
    'referer': 'https://qiandao.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/150.0.0.0',
    'x-echo-region': 'CN',
    'x-request-package-id': '1044',
    'x-request-package-sign-version': '0.0.1',
    'x-request-sign': sign,
    'x-request-sign-type': 'HMAC_SHA256',
    'x-request-sign-version': 'v1',
    'x-request-timestamp': timestamp,
}

print(f"Timestamp: {timestamp}")
print(f"Generated sign: {sign}")
print()

resp = requests.post(API_URL, headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), impersonate="chrome120", timeout=10)
print(f"STATUS: {resp.status_code}")

data = resp.json()
print(f"CODE: {data.get('code')}")

if data.get('code') == 0:
    items = data.get('data', {}).get('list', [])
    print(f"Got {len(items)} sellers!")
    for i, item in enumerate(items[:5]):
        print(f"  [{i+1}] {json.dumps(item, ensure_ascii=False)[:200]}")
else:
    print(f"ERROR: {data}")
