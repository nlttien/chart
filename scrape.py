from curl_cffi import requests
import re
res = requests.get('https://www.google.com/finance/quote/CNY-VND', impersonate='chrome120')
html = res.text
match = re.search(r'data-last-price="([^"]+)"', html)
if match:
    print('Rate:', match.group(1))
else:
    match2 = re.search(r'class="YMlKec fxKbKc"[^>]*>([^<]+)<', html)
    if match2:
        print('Rate class:', match2.group(1))
    else:
        print('Not found')
