import logging
import time
import json
import hashlib
import hmac
import base64
from typing import List, Dict, Any, Optional
from curl_cffi import requests as cffi_requests

logger = logging.getLogger("qiandao_engine")

SKEY = "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"

def generate_sign(api_path: str, timestamp_ms: int) -> str:
    """Tạo chữ ký HMAC_SHA256 chuẩn cho Qiandao API"""
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
    
    if is_sell:
        api_path = "/c2c-web/v1/currency/spu-list-v2"
    else:
        api_path = "/c2c-web/v1/currency/buy-direction/spu-list-v2"
        
    api_url = "https://api.qiandao.com" + api_path
    
    body = {
        "spuId": spu_id,
        "offset": 0,
        "limit": 30,
        "filters": [{
            "key": "904221228984762040",
            "keyType": "ATTRIBUTE",
            "filterOperType": "EQ",
            "isNot": False,
            "selectedQueryValue": {
                "candidateType": "SINGLE_VALUE",
                "candidateValues": [{"label": "普通", "value": spec_id}]
            }
        }],
        "sortBy": "BEST_RATIO"
    }

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        timestamp = str(int(time.time() * 1000))
        sign = generate_sign(api_path, timestamp)
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorization': f'Bearer {jwt_token}',
            'origin': 'https://qiandao.com',
            'referer': 'https://qiandao.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
            'x-echo-region': 'CN',
            'x-request-package-id': '1044',
            'x-request-package-sign-version': '0.0.1',
            'x-request-sign': sign,
            'x-request-sign-type': 'HMAC_SHA256',
            'x-request-sign-version': 'v1',
            'x-request-timestamp': timestamp,
        }

        try:
            resp = cffi_requests.post(
                api_url, 
                headers=headers, 
                data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                impersonate="chrome120", 
                timeout=25
            )
            
            if resp.status_code == 200:
                resp_data = resp.json()
                api_code = str(resp_data.get('code', ''))
                if api_code not in ('0', '200'):
                    err = resp_data.get('errCode', 'Unknown')
                    msg = resp_data.get('msg', '')
                    logger.warning(f"[Qiandao Engine] API Code {api_code}, Err: {err}, Msg: {msg}")
                    return []

                data_obj = resp_data.get('data', {})
                if isinstance(data_obj, dict):
                    items = data_obj.get('items', data_obj.get('list', []))
                elif isinstance(data_obj, list):
                    items = data_obj
                else:
                    items = []

                clean_results = []
                for it in items:
                    seller_info = it.get('buyerInfo') or it.get('sellerInfo') or {}
                    ratio_price = float(it.get('ratioPrice', 0))
                    rmb_price = float(it.get('rmbPrice', 0))
                    stock = int(it.get('stock', 0))
                    min_buy = int(it.get('minBuyCount', 0))
                    seller_name = seller_info.get('nickname') or seller_info.get('username') or 'Qiandao Merchant'
                    is_online = seller_info.get('isOnline', False)
                    credit = seller_info.get('creditPoint', {})
                    credit_score = int(float(credit.get('point', 0) or 0)) if isinstance(credit, dict) else 0

                    if rmb_price > 0 or ratio_price > 0:
                        clean_results.append({
                            'seller': str(seller_name),
                            'unit_price': rmb_price,
                            'stock': stock,
                            'sold_total': credit_score,
                            'online': "Online" if is_online else "Offline",
                            'min_qty': min_buy,
                            'ratio': str(ratio_price),
                            'source': 'qiandao'
                        })

                logger.info(f"[Qiandao Engine] Found {len(clean_results)} items for {name}")
                return clean_results
            else:
                logger.warning(f"[Qiandao Engine] HTTP {resp.status_code} for {name}")
                
        except Exception as e:
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                logger.warning(f"[Qiandao Engine] Attempt {attempt}/{max_retries} timed out connecting for {name}")
            else:
                logger.error(f"[Qiandao Engine] Attempt {attempt}/{max_retries} error for {name}: {e}")
            if attempt < max_retries:
                time.sleep(2)

    return []
