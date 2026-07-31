import json
from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://www.dd373.com/s-mnh4dv-n75hgf-mxgd6e-0-0-0-94vje2-0-0-receive-0-0-1-0-0-0.html?u_atoken=6a67b279-da3f-3a63-9ac1-c996db4cfc7c&u_asig=6b9b3e1d17851807932606767e"
cookie = "clientId=a6676ef252c56a2a9f60c09998c13f82; dpushPC=true; Hm_lvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783669374; HMACCOUNT=2067EC5DCB8D2AE5; firstOpen_cc=true; imagestylewebp=1; headhistorySelectGame=%5B%7B%22Id%22%3A%2246e6971b94044ae3881dfaeb6993abb8%22%7D%5D; AutoSelectHistory=false; _c_WBKFRo=SdND9MOoObdOOBEaFuBUAF0wcGGE0fnmhEUbzpiZ; _nb_ioWEgULi=; Hm_lpvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783682808"

headers = {
    "Cookie": cookie,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Referer": "https://www.dd373.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,vi;q=0.8,en;q=0.7"
}

try:
    with requests.Session(impersonate="chrome120") as s:
        resp = s.get(url, headers=headers, timeout=15)
        print(f"Status Code: {resp.status_code}")
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        def is_valid_row(tag):
            if tag.name not in ['div', 'li', 'ul']: return False
            text = tag.get_text()
            if '元/个' not in text and '1元=' not in text: return False
            for child in tag.find_all(['div', 'li', 'ul']):
                child_text = child.get_text()
                if '元/个' in child_text or '1元=' in child_text:
                    return False
            return True
        
        inner_items = soup.find_all(is_valid_row)
        rows = []
        for item in inner_items:
            row = item
            while row.parent:
                count_in_parent = len([i for i in inner_items if i in row.parent.descendants or i == row.parent])
                count_in_row = len([i for i in inner_items if i in row.descendants or i == row])
                if count_in_parent > count_in_row:
                    break
                row = row.parent
            if row not in rows:
                rows.append(row)
        print(f"Found {len(rows)} data rows.")
        if rows:
            print("First row text:", rows[0].get_text(strip=True))
except Exception as e:
    print(f"Error: {e}")
