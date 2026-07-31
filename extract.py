import re
with open('google_finance.html', 'r', encoding='utf-8') as f:
    html = f.read()
matches = re.findall(r'"CNY / VND",\d+,null,\[([\d\.]+)', html)
if matches:
    print('Rate found:', matches)
else:
    print('Not found')
