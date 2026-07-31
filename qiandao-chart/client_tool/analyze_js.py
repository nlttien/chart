import re
from curl_cffi import requests

# Download the JS file containing sign logic
js_url = "https://assets.qiandaocdn.com/web-bundle-pc/_nuxt/7a7tmuLF.js"
resp = requests.get(js_url, impersonate="chrome120", timeout=10)
js_text = resp.text

# Save the full JS for manual inspection
with open("qiandao_sign.js", "w", encoding="utf-8") as f:
    f.write(js_text)

print(f"JS file size: {len(js_text)} chars")

# Find all occurrences of sign-related code
keywords = ['X-Request-Sign', 'x-request-sign', 'HMAC', 'sha256', 'SHA256', 'Ug(', 'Bg(', 'fetchSkey', 'signVersion', 'request-sign', 'hmac']

for kw in keywords:
    positions = [m.start() for m in re.finditer(re.escape(kw), js_text)]
    if positions:
        print(f"\n=== '{kw}' found {len(positions)} times ===")
        for pos in positions[:3]:  # Show first 3
            start = max(0, pos - 500)
            end = min(len(js_text), pos + 500)
            snippet = js_text[start:end]
            print(f"\n--- At position {pos} ---")
            print(snippet)
            print("---")
