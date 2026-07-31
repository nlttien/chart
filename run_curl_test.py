import subprocess

curl_cmd = r"""curl.exe 'https://api.qiandao.com/c2c-web/v1/common/currency-spu-price-list' \
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
  -H 'x-request-sign: YWU1ZmVjOWRkZTNhODVjNzQwOTQxZjExYjY1ZTdkMWFlYTRjNDI2NmIxZDlhNGU5OGYwMjFhOGNlMTJhZmJiZg==' \
  -H 'x-request-sign-type: HMAC_SHA256' \
  -H 'x-request-sign-version: v1' \
  -H 'x-request-timestamp: 1784789745022' \
  --data-raw '{"tagId":"1707645","offset":0,"limit":20,"specIds":["269615"]}'"""

# Clean up newlines for subprocess if needed, or use a batch file
with open("test_curl.bat", "w") as f:
    f.write(curl_cmd.replace('\\\n', '^'))

# run it
result = subprocess.run(["cmd.exe", "/c", "test_curl.bat"], capture_output=True, text=True)
print("OUT:", result.stdout)
print("ERR:", result.stderr)
