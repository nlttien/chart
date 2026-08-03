import logging
import time
import hashlib
import hmac
import base64
from typing import List, Dict, Any, Optional
from curl_cffi import requests

logger = logging.getLogger("qiandao_engine")

SKEY = "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"

def generate_sign(api_path: str, timestamp_ms: int) -> str:
    msg = api_path + str(timestamp_ms)
    hex_hash = hmac.new(SKEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    return base64.b64encode(hex_hash.encode('utf-8')).decode('utf-8')

def scan_qiandao_item(item_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    name = item_config.get('name', 'Unknown')
    jwt_token = item_config.get('jwt_token', '').strip()
    spu_id = item_config.get('spu_id', '836104794648117776').strip()
    spec_id = item_config.get('spec_id', '269603').strip()
    is_sell = item_config.get('is_sell', False)
    
    if not jwt_token:
        logger.warning(f"[Qiandao Engine] JWT Token is empty for {name}")
        return []
        
    logger.info(f"[Qiandao Engine] Scanning {name} (SPU: {spu_id})...")
    
    api_path = "/c2c-web/v1/currency/spu-list-v2" if is_sell else "/c2c-web/v1/currency/buy-direction/spu-list-v2"
    api_url = "https://api.qiandao.com" + api_path
    timestamp = str(int(time.time() * 1000))
    sign = generate_sign(api_path, timestamp)
    
    headers = {
        'accept': 'application/json',
        'accept-language': 'zh-CN,zh;q=0.9',
        'app-id': 'c2c-web',
        'content-type': 'application/json',
        'jwt-token': jwt_token,
        'origin': 'https://www.qiandao.com',
        'platform': 'web',
        'referer': 'https://www.qiandao.com/',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sign': sign,
        'timestamp': timestamp,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'version': '1.0.0'
    }

    payload = {
        'spuId': spu_id,
        'specIdList': [spec_id] if spec_id else [],
        'page': 1,
        'pageSize': 50,
        'sort': 1
    }

    try:
        with requests.Session(impersonate="chrome120") as s:
            resp = s.post(api_url, json=payload, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"[Qiandao Engine] Status {resp.status_code} for {name}")
                return []
                
            res_json = resp.json()
            if res_json.get('code') != 0 and res_json.get('code') != 200:
                logger.warning(f"[Qiandao Engine] API Error {res_json.get('msg')} for {name}")
                return []

            data = res_json.get('data', {})
            list_items = data.get('list', []) or data.get('records', []) or []
            
            clean_results = []
            for item in list_items:
                seller_name = item.get('merchantName', item.get('userName', 'Unknown'))
                unit_price = float(item.get('price', item.get('unitPrice', 0)))
                stock = int(item.get('stock', item.get('quantity', 0)))
                sold = int(item.get('salesVolume', 0))
                
                clean_results.append({
                    'seller': seller_name,
                    'unit_price': unit_price,
                    'stock': stock,
                    'sold_total': sold,
                    'online': 'Online',
                    'source': 'qiandao'
                })

            clean_results.sort(key=lambda x: x['unit_price'])
            logger.info(f"[Qiandao Engine] Found {len(clean_results)} items for {name}")
            return clean_results
            
    except Exception as e:
        logger.error(f"[Qiandao Engine] Scan error for {name}: {e}")
        return []
