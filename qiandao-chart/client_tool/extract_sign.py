import re
from curl_cffi import requests

js_url = "https://assets.qiandaocdn.com/web-bundle-pc/_nuxt/7a7tmuLF.js"
resp = requests.get(js_url, impersonate="chrome120", timeout=10)
js_text = resp.text

# Find the sign function block - extract a wider snippet
# Key line: _=v[p(488)+"h"]+v[p(459)+"e"]+i[p(473)+"Kk"](u,b)+w+h
# This builds the message: pathname + ? + query_string + body + timestamp
# Bg(Ug(g, _)) = base64(hmac_sha256(g, _))
# g = skey from fetchSkey which returns hv = {production: "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"}

# Let's find the sign function more completely
idx = js_text.find('sign:function(e){return ue(this,arguments')
if idx == -1:
    idx = js_text.find('sign:function(e)')
    
if idx >= 0:
    start = max(0, idx - 200)
    end = min(len(js_text), idx + 3000)
    snippet = js_text[start:end]
    print("=== SIGN FUNCTION ===")
    print(snippet)
    print()

# Find Bg and Ug functions
for func_name in ['function Bg(', 'function Ug(', 'Bg=', 'Ug=']:
    idx = js_text.find(func_name)
    if idx >= 0:
        start = max(0, idx - 100)
        end = min(len(js_text), idx + 500)
        print(f"\n=== {func_name} ===")
        print(js_text[start:end])

# Find the actual key resolution
# fetchSkey returns hv which is: {production: "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"}
# The sign function does: g = yield c() which calls fetchSkey
# Let's look for how g is extracted from hv
idx = js_text.find('production')
if idx >= 0:
    start = max(0, idx - 300)
    end = min(len(js_text), idx + 300)
    print(f"\n=== PRODUCTION KEY CONTEXT ===")
    print(js_text[start:end])

# Look for the actual message construction more carefully
# "_=v[p(488)+"h"]+v[p(459)+"e"]+i[p(473)+"Kk"](u,b)+w+h"
# This means: _ = v.path + v.??e + u(b) + w + h
# where h = timestamp, w = body or "", v = parsed URL
# Let's find what p(488), p(459) resolve to
idx = js_text.find('v[p(488)')
if idx >= 0:
    start = max(0, idx - 500)
    end = min(len(js_text), idx + 200)
    print(f"\n=== MESSAGE CONSTRUCTION ===")
    print(js_text[start:end])
