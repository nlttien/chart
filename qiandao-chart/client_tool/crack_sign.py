import json, re, base64, time, hashlib, hmac
from curl_cffi import requests

url = "https://api.qiandao.com/c2c-web/v1/currency/spu-list-v2"
jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEwMDc0MzYxODIyMzUxNjQxNDAiLCJ0eXBlIjoiVVNFUiIsImV4cCI6MTc4NTA2MDE1NSwiaWF0IjoxNzg0ODAwOTU1fQ.oT6T-yj8-8byoqPhVUnwcd32We9WWBQdTmhU6ZnS_CXrqP4C4tyWLnoPszMx9O8e4z_Lch0iQCwFuCQF9IHetqmNmAjy2BiddHtrEsqKhkuFGUlFh3T2oHZvLP_0pj-Bqmhx6sNWrXgSKsGOHtgrJDCmTpHVx5uxtozo3dJsGsTUXjHFExaL7ev2_aw8-kXB0PcHRT5yGNXgJkScBIqeQwB-jcs3WJA78xTNyO7qRMndqoFLmGv10Wsb06cdwx8YMsF8NSII_HZxyS0K0b5LEHoOCJkFZnsU6D6SdSgWkN6afIXbRWXt31vtKPIpNStQ5B7N3mIMd0NB9x1GUOBIcQ"

body_dict = {"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":False,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"\u666e\u901a","value":"269603"}]}}],"sortBy":""}

# Known values from a working request
known_timestamp = "1784801029073"
known_sign_hex = "640e57767dc89101ceec827e3152f25d0a1b0b0fac77b893f3383e3a1726e9cf"
known_body = '{"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":false,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"\u666e\u901a","value":"269603"}]}}],"sortBy":""}'

# API path
api_path = "/c2c-web/v1/currency/spu-list-v2"

# Try various common HMAC key candidates
possible_keys = [
    "",
    "qiandao",
    "qiandao.com",
    "c2c-web",
    "1044",  # package-id
    "0.0.1",
    "v1",
    known_timestamp,
    jwt_token,
    "qiandao_secret",
    "qiandao_key",
    "c2c_secret_key",
]

# Try various message formats
def try_sign(key_str, msg_str):
    try:
        h = hmac.new(key_str.encode('utf-8'), msg_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return h
    except:
        return None

print("=== Trying to crack HMAC_SHA256 signature ===")
print(f"Target hex: {known_sign_hex}")
print()

# Common message formats
messages = [
    known_body,
    known_timestamp,
    known_timestamp + known_body,
    known_body + known_timestamp,
    api_path + known_timestamp,
    api_path + known_body,
    api_path + known_timestamp + known_body,
    known_timestamp + api_path + known_body,
    known_timestamp + api_path,
    "POST" + api_path + known_timestamp,
    "POST" + api_path + known_body,
    "POST" + api_path + known_timestamp + known_body,
    known_timestamp + "POST" + api_path + known_body,
    f"POST\n{api_path}\n{known_timestamp}\n{known_body}",
    f"{known_timestamp}\n{api_path}\n{known_body}",
    f"{api_path}\n{known_timestamp}\n{known_body}",
]

for key in possible_keys:
    for i, msg in enumerate(messages):
        result = try_sign(key, msg)
        if result == known_sign_hex:
            print(f"!!! MATCH FOUND !!!")
            print(f"Key: '{key}'")
            print(f"Message format #{i}: {msg[:100]}...")
            break
    else:
        continue
    break
else:
    print("No match found with common keys/formats.")
    print()
    
    # Now let's try to find JS and extract the key
    print("=== Fetching Qiandao JS to find sign logic ===")
    
    resp = requests.get('https://qiandao.com/', impersonate="chrome120", timeout=10)
    html = resp.text
    
    # Find all JS file URLs
    js_urls = []
    for match in re.findall(r'src="([^"]+\.js[^"]*)"', html):
        full_url = match if match.startswith('http') else 'https://qiandao.com' + match
        js_urls.append(full_url)
    
    print(f"Found {len(js_urls)} JS files")
    
    for js_url in js_urls:
        try:
            js_resp = requests.get(js_url, impersonate="chrome120", timeout=10)
            js_text = js_resp.text
            
            # Search for signature-related keywords
            if any(kw in js_text for kw in ['x-request-sign', 'HMAC', 'hmac', 'sha256', 'request-sign']):
                print(f"\n[+] Found sign logic in: {js_url}")
                
                # Extract surrounding context
                for kw in ['x-request-sign', 'HMAC', 'request-sign', 'sha256']:
                    for m in re.finditer(kw, js_text):
                        start = max(0, m.start() - 300)
                        end = min(len(js_text), m.end() + 300)
                        snippet = js_text[start:end]
                        print(f"\n--- Snippet around '{kw}' ---")
                        print(snippet)
                        print("---")
                        break  # Only first match per keyword
                break
        except Exception as e:
            continue
