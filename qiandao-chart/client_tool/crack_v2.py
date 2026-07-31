import hashlib, hmac, base64, json, time, urllib.parse
from curl_cffi import requests

# === THÔNG TIN ĐÃ GIẢI MÃ TỪ JAVASCRIPT ===
# Secret key (production): "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"
# Sign formula: base64(hmac_sha256(skey, message))
# Message = path + "?" + sorted_query_string + request_body + timestamp
# Ug = hmac_sha256, Bg = base64encode
# _ = v.path + v.??e + u(b) + w + h
#   v = parsed URL -> v.path = pathname, v.??e = likely ".name" or search
#   b = query string (sorted, formatted as bracket arrays)
#   w = requestId (usually "")
#   h = timestamp string

SKEY = "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"

# Known values from a working request
known_timestamp = "1784801029073"
known_sign_b64 = "NjQwZTU3NzY3ZGM4OTEwMWNlZWM4MjdlMzE1MmYyNWQwYTFiMGIwZmFjNzdiODkzZjMzODNlM2ExNzI2ZTljZg=="
known_sign_hex = base64.b64decode(known_sign_b64).decode('utf-8')
print(f"Target sign hex: {known_sign_hex}")

api_path = "/c2c-web/v1/currency/spu-list-v2"
body_str = '{"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":false,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"\u666e\u901a","value":"269603"}]}}],"sortBy":""}'

# The JS code does: _ = v[p(488)+"h"] + v[p(459)+"e"] + i[p(473)+"Kk"](u,b) + w + h
# v = parsed URL object. p(488)+"h" likely = "path" (pathname), p(459)+"e" is likely "?" or search
# u is a function that stringifies query params, b = sorted query string
# w = requestId (empty string ""), h = timestamp
# Since this is a POST with no query params, b should be empty

# Try various message combos
messages = {
    "path+timestamp":                       api_path + known_timestamp,
    "path+?+timestamp":                     api_path + "?" + known_timestamp,
    "path+body+timestamp":                  api_path + body_str + known_timestamp,
    "path+?+body+timestamp":                api_path + "?" + body_str + known_timestamp,
    "path+?++body+timestamp":               api_path + "?" + "" + body_str + known_timestamp,
    "path+++timestamp":                     api_path + "" + "" + known_timestamp,
    # Maybe v.search = "" for POST with no query
    "path+empty+empty+empty+timestamp":     api_path + "" + "" + "" + known_timestamp,
    # Maybe the body is included differently
    "path+body_as_query+timestamp":         api_path + body_str + "" + known_timestamp,
    # The key insight: w=requestId (always ""), u(b) is sorted query (empty for POST)
    # So message = pathname + "?" + "" + "" + timestamp = path + "?" + timestamp
    "path_q_ts":                            api_path + "?" + "" + "" + known_timestamp,
    # Or without "?"
    "path_ts":                              api_path + "" + "" + "" + known_timestamp,
    # v.path = /c2c-web/v1/currency/spu-list-v2, v["??e"] could be empty for POST
    # Maybe the body (a) gets appended as w
    "path_body_ts":                         api_path + body_str + known_timestamp,
}

print(f"\nTrying {len(messages)} message formats with SKEY={SKEY}...")
for name, msg in messages.items():
    h = hmac.new(SKEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    match = "✅ MATCH!" if h == known_sign_hex else ""
    if match:
        print(f"\n🎉🎉🎉 {name}: {h} {match}")
        print(f"Message: {msg[:200]}...")
    # Print all for debugging
    # print(f"  {name}: {h[:16]}... {match}")

# If no match, try with different body serializations
print("\n=== Trying body JSON variations ===")
body_dict = {"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":False,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"\u666e\u901a","value":"269603"}]}}],"sortBy":""}

# json.dumps with different settings
body_variants = [
    body_str,  # original
    json.dumps(body_dict, ensure_ascii=False, separators=(',', ':')),
    json.dumps(body_dict, ensure_ascii=True, separators=(',', ':')),
    json.dumps(body_dict, ensure_ascii=False),
    json.dumps(body_dict, ensure_ascii=True),
]

for bv in body_variants:
    for fmt_name, fmt in [
        ("path+body+ts", api_path + bv + known_timestamp),
        ("path+body+empty+ts", api_path + bv + "" + known_timestamp),
    ]:
        h = hmac.new(SKEY.encode('utf-8'), fmt.encode('utf-8'), hashlib.sha256).hexdigest()
        if h == known_sign_hex:
            print(f"🎉 MATCH with body variant! Format: {fmt_name}")
            print(f"Body: {bv[:100]}...")

# Try completely different: maybe the full URL is used
full_url = "https://api.qiandao.com/c2c-web/v1/currency/spu-list-v2"
for msg in [
    full_url + known_timestamp,
    full_url + body_str + known_timestamp,
    full_url + "?" + known_timestamp,
]:
    h = hmac.new(SKEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    if h == known_sign_hex:
        print(f"🎉 MATCH with full URL!")

print("\nDone. If no match, the message format needs more investigation.")
print(f"\nFor reference, actual sign hex = {known_sign_hex}")
# Let's also print what our best guess produces
msg = api_path + known_timestamp
h = hmac.new(SKEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
print(f"path+ts produces:                {h}")
msg = api_path + body_str + known_timestamp
h = hmac.new(SKEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
print(f"path+body+ts produces:           {h}")
