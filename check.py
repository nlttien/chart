import re
with open('google_search.html', 'r', encoding='utf-8') as f:
    html = f.read()
# Find any number that resembles 3500-3900
matches = re.findall(r'>([^<]*3[5678]\d\d(?:\.\d+)?[^<]*)<', html)
print('Possible rates in Search HTML:', set(matches))
