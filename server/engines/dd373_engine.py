import os
import re
import time
import json
import asyncio
import logging
import subprocess
import threading
from typing import List, Dict, Any, Tuple, Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from curl_cffi import requests
except ImportError:
    import requests

from server.smart_logger import SmartLogger

logger = logging.getLogger("dd373_engine")

DEFAULT_COOKIE = "clientId=a6676ef252c56a2a9f60c09998c13f82; dpushPC=true; Hm_lvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783669374; HMACCOUNT=2067EC5DCB8D2AE5; firstOpen_cc=true; imagestylewebp=1; headhistorySelectGame=%5B%7B%22Id%22%3A%2246e6971b94044ae3881dfaeb6993abb8%22%7D%5D; AutoSelectHistory=false; _c_WBKFRo=SdND9MOoObdOOBEaFuBUAF0wcGGE0fnmhEUbzpiZ; _nb_ioWEgULi=; acw_tc=6b9b3e2017836767239266076e72366b0fe422b914da8e36d261d7d316; cdn_sec_tc=6b9b3e2017836767239266076e72366b0fe422b914da8e36d261d7d316; acw_sc__v3=6a50bf378bc4cef54169f278582099aa5bca4c7c; Hm_lpvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783676689"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# In-memory cached dynamic cookie, solving status & thread serialization lock
_LIVE_COOKIE: str = DEFAULT_COOKIE
_ENGINE_SOLVER_LOCK = threading.Lock()
_SOLVING_STATE: Dict[str, Any] = {
    "is_solving": False,
    "last_status": "idle",  # "idle", "solving", "success", "failed"
    "error_code": None,
    "message": None,
    "last_updated_at": None
}

def parse_number(text: str) -> float:
    if not text:
        return 0.0
    matches = re.findall(r"(\d+\.?\d*)", text)
    return float(matches[0]) if matches else 0.0

def update_live_cookie(new_cookie: str):
    global _LIVE_COOKIE
    if new_cookie and len(new_cookie) > 10:
        _LIVE_COOKIE = new_cookie
        logger.info("[DD373 Engine] Live dynamic cookie updated!")

def get_solving_state() -> Dict[str, Any]:
    return _SOLVING_STATE

def scan_dd373_item(item_config: Dict[str, Any], custom_cookie: Optional[str] = None) -> List[Dict[str, Any]]:
    global _LIVE_COOKIE
    name = item_config.get('name', 'Unknown')
    url = item_config.get('url', '').strip()
    start_time = time.time()

    if not url:
        logger.warning(f"[DD373 Engine] URL is empty for {name}")
        SmartLogger.log_event(
            platform="dd373",
            level="WARNING",
            error_code="EMPTY_URL",
            message=f"Configuration error: URL is empty for item {name}"
        )
        return []
def make_dd373_request(url: str, headers: dict):
    try:
        from curl_cffi import requests as cffi_requests
        with cffi_requests.Session(impersonate="chrome120") as s:
            return s.get(url, headers=headers, timeout=15)
    except Exception:
        import requests
        with requests.Session() as s:
            return s.get(url, headers=headers, timeout=15)

def fetch_dd373_html_fast(url: str, name: str) -> Tuple[str, int, bool]:
    """Cào nhanh trang web DD373 dùng cURL cffi / requests với Cookie & User-Agent động"""
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Cookie': _LIVE_COOKIE,
        'Referer': 'https://www.dd373.com/',
        'User-Agent': DEFAULT_USER_AGENT,
        'Upgrade-Insecure-Requests': '1'
    }

    resp_text = ""
    status_code = 0
    try:
        resp = make_dd373_request(url, headers)
        status_code = resp.status_code
        if status_code == 200:
            resp_text = resp.text
        else:
            logger.warning(f"[DD373 Engine] Status {status_code} for {name}")
            SmartLogger.log_event(
                platform="dd373",
                level="WARNING",
                error_code="HTTP_BLOCKED",
                message=f"DD373 cURL request received HTTP status {status_code}",
                details={"url": url, "http_status": status_code}
            )

    except Exception as e:
        logger.error(f"[DD373 Engine] cURL request exception: {e}")
        SmartLogger.log_event(
            platform="dd373",
            level="WARNING",
            error_code="NETWORK_TIMEOUT",
            message=f"cURL request exception: {str(e)}",
            details={"url": url, "exception": str(e)}
        )

    # Check if Aliyun Captcha WAF page is returned
    is_waf_captcha = False
    if resp_text:
        if "aliyunCaptcha" in resp_text or "verify that you are a real person" in resp_text or "sliding-slider" in resp_text:
            is_waf_captcha = True

    # If cURL succeeds and no WAF Captcha, attempt parsing HTML
    clean_results = []
    if resp_text and not is_waf_captcha:
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

        for r in rows:
            text = r.get_text(separator=' | ', strip=True)
            parts = [p.strip() for p in text.split('|') if p.strip()]

            price = 0.0
            stock = 0
            min_qty = 0
            ratio = ""
            delivery = "Online"
            seller_found = ""

            for p in parts:
                if "极速收货" in p:
                    delivery = "极速收货"
                elif "分钟" in p:
                    delivery = p

                if '1元=' in p or '1元 =' in p:
                    ratio_match = re.search(r"1\s*元\s*=\s*([\d\.]+)", p)
                    if ratio_match:
                        ratio = ratio_match.group(1)

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

                if not seller_found and not any(c in p for c in ['元', '件', '个', '万', '收', '货', '分钟']):
                    if len(p) > 1 and len(p) < 30:
                        seller_found = p

            if price == 0.0 and ratio:
                try:
                    price = round(1.0 / float(ratio), 4)
                except Exception:
                    pass

            seller = seller_found if seller_found else (f"Trader (1¥={ratio})" if ratio else "DD373 Trader")

            if price > 0:
                clean_results.append({
                    'seller': seller,
                    'unit_price': price,
                    'stock': stock,
                    'sold_total': 0,
                    'online': delivery,
                    'min_qty': min_qty,
                    'ratio': ratio,
                    'delivery': delivery,
                    'source': 'dd373'
                })

        clean_results.sort(key=lambda x: x['unit_price'])

    # If cURL returned items > 0, return immediately with success log
    if len(clean_results) > 0:
        exec_time = int((time.time() - start_time) * 1000)
        logger.info(f"[DD373 Engine] cURL found {len(clean_results)} items for {name}")
        SmartLogger.log_event(
            platform="dd373",
            level="INFO",
            error_code="PARSED_SUCCESS",
            message=f"cURL Engine successfully parsed {len(clean_results)} items for {name}",
            details={"url": url, "http_status": status_code, "execution_time_ms": exec_time, "items_count": len(clean_results)}
        )
        return clean_results

    # If cURL returned 0 items and NO Captcha WAF, return [] directly to prevent launching heavy Chromium browser processes
    if not is_waf_captcha:
        return []

    # FALLBACK: Trigger Puppeteer/Playwright Mouse Solver ONLY when Aliyun Captcha WAF page is explicitly detected
    with _ENGINE_SOLVER_LOCK:
        logger.warning(f"[DD373 Engine] Lock acquired for {name}. Triggering Puppeteer Mouse Solver...")
        _SOLVING_STATE["is_solving"] = True
        _SOLVING_STATE["last_status"] = "solving"
        _SOLVING_STATE["error_code"] = "CAPTCHA_SOLVING_IN_PROGRESS"
        _SOLVING_STATE["message"] = "Đang trong quá trình tự động giải mã Aliyun Captcha bằng Puppeteer Mouse Solver..."

        SmartLogger.log_event(
            platform="dd373",
            level="WARNING",
            error_code="WAF_CAPTCHA_DETECTED" if is_waf_captcha else "CURL_PARSED_EMPTY",
            message=f"Triggering Puppeteer Mouse Solver for {name} (is_waf_captcha={is_waf_captcha})",
            details={"url": url, "http_status": status_code}
        )

        p_results, p_cookie = [], ""
        try:
            from server.engines.dd373_playwright_solver import fetch_dd373_with_playwright
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            p_results, p_cookie = new_loop.run_until_complete(fetch_dd373_with_playwright(url))
            new_loop.close()
        except Exception as p_ex:
            logger.warning(f"[DD373 Engine] Playwright solver exception: {p_ex}")
            p_results, p_cookie = [], ""

        if p_cookie:
            update_live_cookie(p_cookie)

        if len(p_results) > 0:
            _SOLVING_STATE["is_solving"] = False
            _SOLVING_STATE["last_status"] = "success"
            _SOLVING_STATE["error_code"] = None
            _SOLVING_STATE["message"] = "Giải mã Captcha WAF bằng Playwright Stealth Solver thành công"
            logger.info(f"[DD373 Engine] Playwright Stealth Solver successfully retrieved {len(p_results)} items for {name}")
            SmartLogger.log_event(
                platform="dd373",
                level="INFO",
                error_code="PLAYWRIGHT_SOLVE_SUCCESS",
                message=f"Playwright Stealth Solver successfully bypassed Captcha & retrieved {len(p_results)} items for {name}",
                details={"url": url, "items_count": len(p_results)}
            )
            return p_results

        _SOLVING_STATE["is_solving"] = False
        _SOLVING_STATE["last_status"] = "failed"
        _SOLVING_STATE["error_code"] = "CAPTCHA_SOLVE_FAILED"
        _SOLVING_STATE["message"] = "Không thể tự động giải mã Aliyun Captcha WAF trên trang DD373 bằng Playwright Stealth Solver"
        return []

def fetch_dd373_with_puppeteer(url: str) -> Tuple[List[Dict[str, Any]], str]:
    """Execute Puppeteer Node.js mouse solver script to bypass Captcha and scrape DD373."""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puppeteer_mouse_solver.js")
    if not os.path.exists(script_path):
        SmartLogger.log_event(
            platform="dd373",
            level="ERROR",
            error_code="PUPPETEER_SCRIPT_NOT_FOUND",
            message=f"Script file not found: {script_path}",
            details={"script_path": script_path}
        )
        return [], ""

    try:
        logger.info(f"[DD373 Engine] Launching Node.js Puppeteer solver for {url}...")
        res = subprocess.run(["node", script_path, url], capture_output=True, text=True, timeout=45)
        
        if res.returncode != 0 or not res.stdout:
            err_msg = res.stderr.strip() if res.stderr else f"Exit code {res.returncode}"
            logger.error(f"[DD373 Engine] Puppeteer process failed: {err_msg}")
            _SOLVING_STATE["is_solving"] = False
            _SOLVING_STATE["last_status"] = "failed"
            _SOLVING_STATE["error_code"] = "PUPPETEER_PROCESS_ERROR"
            _SOLVING_STATE["message"] = f"Node.js Puppeteer process returned error: {err_msg}"
            _SOLVING_STATE["details"] = {"returncode": res.returncode, "stderr": res.stderr}
            SmartLogger.log_event(
                platform="dd373",
                level="ERROR",
                error_code="PUPPETEER_PROCESS_ERROR",
                message=f"Node.js Puppeteer process returned error: {err_msg}",
                details={"returncode": res.returncode, "stderr": res.stderr, "stdout": res.stdout}
            )
            return [], ""

        data = json.loads(res.stdout)
        if not data.get("success"):
            err = data.get("error", "Unknown error in Puppeteer script")
            err_code = data.get("error_code", "PUPPETEER_SOLVE_FAILED")
            logger.error(f"[DD373 Engine] Puppeteer script reported error: {err}")
            _SOLVING_STATE["is_solving"] = False
            _SOLVING_STATE["last_status"] = "failed"
            _SOLVING_STATE["error_code"] = err_code
            _SOLVING_STATE["message"] = err
            _SOLVING_STATE["details"] = {"error": err}
            SmartLogger.log_event(
                platform="dd373",
                level="ERROR",
                error_code=err_code,
                message=f"Puppeteer script execution failed: {err}",
                details={"error": err}
            )
            return [], ""

        has_screenshot = data.get("has_screenshot", False)
        if data.get("html"):
            from server.engines.dd373_playwright_solver import parse_dd373_html
            results = parse_dd373_html(data["html"])
            
            if len(results) == 0:
                raw_err_code = data.get("error_code") or "PARSER_ZERO_ITEMS_FOUND"
                raw_err_msg = data.get("error_message") or "Bóc tách được 0 gian hàng từ trang DD373"
                _SOLVING_STATE["is_solving"] = False
                _SOLVING_STATE["last_status"] = "failed"
                _SOLVING_STATE["error_code"] = raw_err_code
                _SOLVING_STATE["message"] = raw_err_msg
                _SOLVING_STATE["details"] = {"items_count": 0, "solved": data.get("solved", False)}
            
            logger.info(f"[DD373 Engine] Puppeteer solver parsed {len(results)} items successfully!")
            SmartLogger.log_event(
                platform="dd373",
                level="INFO" if len(results) > 0 else "WARNING",
                error_code="PUPPETEER_SOLVE_SUCCESS" if len(results) > 0 else (data.get("error_code") or "PUPPETEER_PARSED_EMPTY"),
                message=f"Puppeteer Mouse Solver bypassed Captcha & parsed {len(results)} items!",
                details={"items_count": len(results), "solved": data.get("solved", False), "raw_error": data.get("error_message")},
                screenshot_saved=has_screenshot
            )
            return results, data.get("cookies", "")

    except Exception as e:
        logger.error(f"[DD373 Engine] Puppeteer solver execution error: {e}")
        SmartLogger.log_event(
            platform="dd373",
            level="ERROR",
            error_code="PUPPETEER_EXCEPTION",
            message=f"Puppeteer execution exception: {str(e)}",
            details={"exception": str(e)}
        )
    return [], ""
