import hashlib, hmac, base64, json, time, sys, os
sys.stdout.reconfigure(encoding='utf-8')

SKEY = "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"
known_timestamp = "1784801029073"
known_sign_b64 = "NjQwZTU3NzY3ZGM4OTEwMWNlZWM4MjdlMzE1MmYyNWQwYTFiMGIwZmFjNzdiODkzZjMzODNlM2ExNzI2ZTljZg=="
known_sign_hex = base64.b64decode(known_sign_b64).decode('utf-8')
print(f"Target: {known_sign_hex}")

api_path = "/c2c-web/v1/currency/spu-list-v2"
body_str = '{"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":false,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"\u666e\u901a","value":"269603"}]}}],"sortBy":""}'

def sign(key, msg):
    return hmac.new(key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()

# From JS: _ = v.pathname + v.search + u(b) + w + h
# v = new URL(url) -> pathname, search
# For POST to https://api.qiandao.com/c2c-web/v1/currency/spu-list-v2:
#   v.pathname = "/c2c-web/v1/currency/spu-list-v2"
#   v.search = "" (no query params in URL)
# u(b) = stringify of merged+sorted query params = "" (no query)
# w = requestId = "" 
# h = timestamp

# So message should be: pathname + search + "" + "" + timestamp
# = "/c2c-web/v1/currency/spu-list-v2" + "" + "" + "" + "1784801029073"
# = "/c2c-web/v1/currency/spu-list-v21784801029073"

messages = {
    "path+ts": api_path + known_timestamp,
    "path+empty+ts": api_path + "" + known_timestamp,
    "path+body+ts": api_path + body_str + known_timestamp,
    "path+body+empty+ts": api_path + body_str + "" + known_timestamp,
    "path+empty+body+ts": api_path + "" + body_str + known_timestamp,
    "path+empty+empty+ts": api_path + "" + "" + known_timestamp,
    "path+empty+empty+empty+ts": api_path + "" + "" + "" + known_timestamp,
}

found = False
for name, msg in messages.items():
    h = sign(SKEY, msg)
    match = "<<< MATCH!" if h == known_sign_hex else ""
    if match:
        found = True
    print(f"{name}: {h} {match}")

if not found:
    # Maybe v.search includes "?" even when empty
    print("\n--- With ? separator ---")
    msgs2 = {
        "path+?+ts": api_path + "?" + known_timestamp,
        "path+?+empty+ts": api_path + "?" + "" + known_timestamp,
        "path+?+empty+empty+ts": api_path + "?" + "" + "" + known_timestamp,
        "path+?+body+ts": api_path + "?" + body_str + known_timestamp,
    }
    for name, msg in msgs2.items():
        h = sign(SKEY, msg)
        match = "<<< MATCH!" if h == known_sign_hex else ""
        if match: found = True
        print(f"{name}: {h} {match}")

if not found:
    # Maybe the body is POST data that gets query-stringified somehow?
    print("\n--- body as query string ---")
    body_dict = json.loads(body_str)
    # Try URL-encoding the body
    import urllib.parse
    body_qs = urllib.parse.urlencode(body_dict)
    msgs3 = {
        "path+body_qs+ts": api_path + body_qs + known_timestamp,
        "path+?+body_qs+ts": api_path + "?" + body_qs + known_timestamp,
    }
    for name, msg in msgs3.items():
        h = sign(SKEY, msg)
        match = "<<< MATCH!" if h == known_sign_hex else ""
        if match: found = True
        print(f"{name}: {h} {match}")

if not found:
    # Maybe Ug function is NOT standard HMAC but custom
    # Let me check: Ug takes (key, message) and returns something that Bg then base64-encodes
    # The output is hex string of 64 chars = 32 bytes = SHA256
    # But Ug is imported as a module. Let me look more carefully...
    # Actually from the JS, Ug is zg(function(){...}) which looks like an HMAC-SHA256 implementation
    # The key observation: Bg produces base64 of the hex string, not of the raw hash!
    # So the sign = base64(hex_string) not base64(raw_bytes)
    # This matches: base64("640e5776...") = "NjQwZTU3..."
    
    # Maybe the skey needs to be in a different env? Let's also try dev key
    DEV_SKEY = "67svK1GJqP0GMW31TfGI9YAOcyvLUX0q"
    print(f"\n--- Trying DEV key: {DEV_SKEY} ---")
    for name, msg in messages.items():
        h = sign(DEV_SKEY, msg)
        match = "<<< MATCH!" if h == known_sign_hex else ""
        if match: found = True
        print(f"{name}: {h} {match}")

if not found:
    # Maybe the path includes the host?
    print("\n--- With api host ---")
    for host_prefix in ["api.qiandao.com", "https://api.qiandao.com"]:
        for name_suffix, msg_suffix in [
            ("ts", known_timestamp),
            ("body+ts", body_str + known_timestamp),
        ]:
            msg = host_prefix + api_path + msg_suffix
            h = sign(SKEY, msg)
            match = "<<< MATCH!" if h == known_sign_hex else ""
            if match: found = True
            print(f"host+path+{name_suffix}: {h} {match}")
