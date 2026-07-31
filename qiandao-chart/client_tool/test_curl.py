import json
import re
from curl_cffi import requests

curl_str = """curl 'https://api.qiandao.com/c2c-web/v1/currency/spu-list-v2' \
  -H 'accept: application/json' \
  -H 'accept-language: en-US' \
  -H 'authorization: Bearer undefined' \
  -H 'content-type: application/json' \
  -H 'origin: https://qiandao.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://qiandao.com/' \
  -H 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-site' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' \
  -H 'x-echo-region: CN' \
  -H 'x-request-package-id: 1044' \
  -H 'x-request-package-sign-version: 0.0.1' \
  -H 'x-request-sign: YmI0YTJhMjc4NjU4NDRkODEyOWNjZDY5N2I5M2I3MDAzMzNkOGM2ZTRmZWFhNzVmYzlmYjJlN2UwMWNlMzY2ZQ==' \
  -H 'x-request-sign-type: HMAC_SHA256' \
  -H 'x-request-sign-version: v1' \
  -H 'x-request-timestamp: 1784796785564' \
  --data-raw '{"spuId":"836104794648117776","offset":0,"limit":20,"filters":[{"key":"904221228984762040","keyType":"ATTRIBUTE","filterOperType":"EQ","isNot":false,"selectedQueryValue":{"candidateType":"SINGLE_VALUE","candidateValues":[{"label":"普通","value":"269603"}]}}],"sortBy":"BEST_RATIO"}'"""

def parse_curl(c_str):
    headers = {}
    url_match = re.search(r"curl\s+['\"]?(https?://[^\s'\"]+)['\"]?", c_str)
    url = url_match.group(1) if url_match else ""
    for h in re.findall(r"-H\s+['\"](.*?)['\"]", c_str):
        if ':' in h:
            k, v = h.split(':', 1)
            headers[k.strip()] = v.strip()
    data_match = re.search(r"--data-raw\s+'(.*?)'", c_str, re.DOTALL)
    data = data_match.group(1) if data_match else None
    return url, headers, data

url, headers, data = parse_curl(curl_str)
print("URL:", url)
print("Data length:", len(data) if data else 0)

try:
    resp = requests.post(url, headers=headers, data=data.encode('utf-8') if data else None, impersonate="chrome120")
    print("STATUS:", resp.status_code)
    try:
        print("RESPONSE:", resp.json())
    except:
        print("RESPONSE:", resp.content[:500])
except Exception as e:
    print("ERROR:", e)
