import urllib.request
import re
req = urllib.request.Request('https://www.google.com/finance/quote/CNY-VND', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
matches = re.findall(r'"CNY / VND",\d+,null,\[([\d\.]+)', html)
print('matches:', matches)
