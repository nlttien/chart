import logging
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests

logger = logging.getLogger("dd373_engine")

DEFAULT_COOKIE = "clientId=a6676ef252c56a2a9f60c09998c13f82; dpushPC=true; Hm_lvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783669374; HMACCOUNT=2067EC5DCB8D2AE5; firstOpen_cc=true; imagestylewebp=1; headhistorySelectGame=%5B%7B%22Id%22%3A%2246e6971b94044ae3881dfaeb6993abb8%22%7D%5D; AutoSelectHistory=false; _c_WBKFRo=SdND9MOoObdOOBEaFuBUAF0wcGGE0fnmhEUbzpiZ; _nb_ioWEgULi=; acw_tc=6b9b3e2017836767239266076e72366b0fe422b914da8e36d261d7d316; cdn_sec_tc=6b9b3e2017836767239266076e72366b0fe422b914da8e36d261d7d316; acw_sc__v3=6a50bf378bc4cef54169f278582099aa5bca4c7c; Hm_lpvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783676689"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def parse_number(text: str) -> float:
    if not text:
        return 0.0
    matches = re.findall(r"(\d+\.?\d*)", text)
    return float(matches[0]) if matches else 0.0

def scan_dd373_item(item_config: Dict[str, Any], custom_cookie: Optional[str] = None) -> List[Dict[str, Any]]:
    name = item_config.get('name', 'Unknown')
    url = item_config.get('url', '').strip()
    
    if not url:
        logger.warning(f"[DD373 Engine] URL is empty for {name}")
        return []
        
    logger.info(f"[DD373 Engine] Scanning {name} (URL: {url})...")
    
    cookie = custom_cookie or item_config.get('cookie', '').strip() or DEFAULT_COOKIE
    user_agent = item_config.get('user_agent', '').strip() or DEFAULT_USER_AGENT
    
    headers = {
        "User-Agent": user_agent,
        "Cookie": cookie,
        "Referer": "https://www.dd373.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,vi;q=0.8,en;q=0.7"
    }

    try:
        resp_text = ""
        with requests.Session(impersonate="chrome120") as s:
            resp = s.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                resp_text = resp.text
            else:
                logger.warning(f"[DD373 Engine] Status {resp.status_code} for {name}")
                return []

        if not resp_text:
            return []

        soup = BeautifulSoup(resp_text, 'lxml')
        
        def is_valid_row(tag):
            if tag.name not in ['div', 'li', 'ul', 'tr']:
                return False
            text = tag.get_text()
            if '元/个' not in text and '1元=' not in text:
                return False
            for child in tag.find_all(['div', 'li', 'ul', 'tr']):
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

        clean_results = []
        for r in rows:
            text = r.get_text(separator=' | ', strip=True)
            parts = [p.strip() for p in text.split('|') if p.strip()]
            
            seller = "Unknown"
            price = 0.0
            stock = 0
            min_qty = 0
            ratio = ""
            delivery = ""
            
            for p in parts:
                if '元/个' in p or '1元=' in p:
                    price = parse_number(p)
                elif '件' in p or '万' in p or '个' in p:
                    num = parse_number(p)
                    if '万' in p:
                        num *= 10000
                    if stock == 0:
                        stock = int(num)
                    else:
                        min_qty = int(num)
            
            if price > 0:
                clean_results.append({
                    'seller': seller,
                    'unit_price': price,
                    'stock': stock,
                    'sold_total': 0,
                    'online': 'Online',
                    'min_qty': min_qty,
                    'ratio': ratio,
                    'delivery': delivery,
                    'source': 'dd373'
                })

        clean_results.sort(key=lambda x: x['unit_price'])
        logger.info(f"[DD373 Engine] Found {len(clean_results)} items for {name}")
        return clean_results
        
    except Exception as e:
        logger.error(f"[DD373 Engine] Scan error for {name}: {e}")
        return []
