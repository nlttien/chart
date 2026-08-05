import os
import re
import time
import math
import random
import logging
import asyncio
import threading
from typing import List, Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, BrowserContext

from server.smart_logger import SmartLogger, LAST_ERROR_SCREENSHOT

logger = logging.getLogger("dd373_playwright_solver")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PROFILE_DIR = os.path.join(DATA_DIR, "dd373_playwright_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)

# Lock to prevent concurrent Chromium profile access (ProcessSingleton collision)
_BROWSER_LOCK = threading.Lock()

STEALTH_JS = """
// 1. Overwrite navigator.webdriver & Automation flags
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

// 2. Mock plugins array
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbheakVisualpdf', description: '' },
        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
    ]
});

// 3. Mock CDC / Aliyun WAF detection objects
delete window.cdc_adoQpoasndfTargetKCchStandard;
delete window.__driver_evaluate;
delete window.__webdriver_evaluate;
delete window.__selenium_evaluate;
delete window.__fxdriver_evaluate;
delete window.__driver_unwrapped;
delete window.__webdriver_unwrapped;
delete window.__selenium_unwrapped;
delete window.__fxdriver_unwrapped;

// 4. Mock WebGL Vendor & Renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Google Inc. (NVIDIA)';
    if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)';
    return getParameter.apply(this, [parameter]);
};

// 5. Override Permissions Query API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);
"""

def parse_number(text: str) -> float:
    if not text:
        return 0.0
    matches = re.findall(r"(\d+\.?\d*)", text)
    return float(matches[0]) if matches else 0.0

def clean_stale_singleton_lock():
    """Remove stale Chromium SingletonLock file to avoid launch errors."""
    lock_file = os.path.join(PROFILE_DIR, "SingletonLock")
    if os.path.exists(lock_file) or os.path.islink(lock_file):
        try:
            os.remove(lock_file)
            logger.info("[Playwright Solver] Cleaned stale Chromium SingletonLock file")
        except Exception as e:
            logger.warning(f"[Playwright Solver] Could not remove SingletonLock: {e}")

def generate_human_steps(distance: float) -> List[Tuple[float, float, float]]:
    """
    Quỹ đạo chuột kéo văng quá đà lề phải (+15px đến +25px) & rút nhẹ về đích từ chart-dd373-test:
    - Gia tốc Ease-In-Out tự nhiên.
    - Kéo văng quá đà lề phải (Overshoot) dứt khoát (~0.3s).
    - Rút nhẹ chuột về vị trí đích (Bounce Back).
    """
    steps = []
    current_x = 0.0
    current_y = 0.0

    overshoot = random.uniform(15.0, 25.0)
    target_overshoot_x = distance + overshoot

    # Giai đoạn 1: Kéo văng vượt qua lề phải (Dứt khoát: 14 - 20 bước)
    main_steps = random.randint(14, 20)
    for i in range(1, main_steps + 1):
        t = i / main_steps
        ease = 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2
        next_x = target_overshoot_x * ease
        dx = next_x - current_x
        dy = math.sin(t * math.pi) * random.uniform(0.2, 0.6) + random.uniform(-0.3, 0.3)

        current_x = next_x
        current_y += dy
        delay = random.uniform(0.005, 0.015)
        steps.append((dx, dy, delay))

    # Giai đoạn 2: Rút nhẹ chuột trở lại sát lề đích
    correction_steps = random.randint(4, 7)
    final_target_x = distance + 4.0
    start_corr_x = current_x

    for j in range(1, correction_steps + 1):
        t = j / correction_steps
        ease = math.sin(t * math.pi / 2)
        next_x = start_corr_x + (final_target_x - start_corr_x) * ease
        dx = next_x - current_x
        dy = random.uniform(-0.2, 0.2)
        current_x = next_x
        current_y += dy
        delay = random.uniform(0.005, 0.012)
        steps.append((dx, dy, delay))

    return steps

async def solve_aliyun_slider(page: Page) -> bool:
    """
    Detect and slide Aliyun Captcha slider using realistic human mouse trajectory from chart-dd373-test.
    """
    selectors = [
        '#aliyunCaptcha-sliding-slider',
        '#nc_1_n1z',
        '.nc_iconfont.btn_slide',
        'span[id*="sliding"]',
        '.btn_slide',
        'div[class*="sliding"] span'
    ]

    slider_btn = None
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                slider_btn = btn
                logger.info(f"[Playwright Solver] Captcha slider detected with selector: {sel}")
                break
        except Exception:
            pass

    if not slider_btn:
        for frame in page.frames:
            for sel in selectors:
                try:
                    btn = frame.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        slider_btn = btn
                        logger.info(f"[Playwright Solver] Captcha slider detected inside iframe with selector: {sel}")
                        break
                except Exception:
                    pass
            if slider_btn:
                break

    if not slider_btn:
        return False

    SmartLogger.log_event(
        platform="dd373",
        level="WARNING",
        error_code="WAF_CAPTCHA_DETECTED",
        message="Aliyun Captcha WAF Slider detected on DD373 page",
        details={"url": page.url}
    )

    box = await slider_btn.bounding_box()
    if not box:
        return False

    slide_distance = 345.0
    track_selectors = [
        '#aliyunCaptcha-sliding-body',
        '.sliding',
        '#aliyunCaptcha-sliding-wrapper',
        '.aliyunCaptcha-sliding-wrapper',
        'div[class*="sliding-wrapper"]',
        'div[class*="nc-container"]'
    ]

    for t_sel in track_selectors:
        try:
            track_el = page.locator(t_sel).first
            if await track_el.count() > 0:
                t_box = await track_el.bounding_box()
                if t_box and t_box["width"] > box["width"]:
                    measured = t_box["width"] - box["width"]
                    if 250 < measured < 400:
                        slide_distance = measured
                        break
        except Exception:
            pass

    start_x = box['x'] + box['width'] / 2
    start_y = box['y'] + box['height'] / 2

    SmartLogger.log_event(
        platform="dd373",
        level="INFO",
        error_code="CAPTCHA_SOLVING_ATTEMPT",
        message=f"Starting human-like drag on Aliyun Captcha (distance: {slide_distance:.1f}px)",
        details={"start_x": start_x, "start_y": start_y, "distance": slide_distance}
    )

    await page.mouse.move(start_x, start_y)
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.15, 0.3))

    curr_x, curr_y = start_x, start_y
    steps = generate_human_steps(slide_distance)
    for dx, dy, delay in steps:
        curr_x += dx
        curr_y += dy
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(delay)

    await asyncio.sleep(0.35)
    await page.mouse.up()
    await asyncio.sleep(3.0)

    page_content = await page.content()
    is_success = False
    
    if "aliyunCaptcha" not in page_content and "Please complete the operation" not in page_content:
        is_success = True
    else:
        succ_el = page.locator('.nc-lang-cnt, .aliyunCaptcha-sliding-text-box, span[class*="success"]').first
        if await succ_el.count() > 0:
            txt = await succ_el.text_content()
            if txt and ("验证" in txt or "成功" in txt or "verified" in txt.lower()):
                is_success = True

    if is_success:
        SmartLogger.log_event(
            platform="dd373",
            level="INFO",
            error_code="CAPTCHA_SOLVE_SUCCESS",
            message="Aliyun Captcha slider successfully bypassed!",
            details={"url": page.url}
        )
        return True
    else:
        SmartLogger.log_event(
            platform="dd373",
            level="ERROR",
            error_code="CAPTCHA_SOLVE_FAILED",
            message="Aliyun Captcha slider solve failed. Captcha prompt still present.",
            details={"url": page.url}
        )
        await page.screenshot(path=LAST_ERROR_SCREENSHOT, full_page=True)
        return False

def parse_dd373_html(html_content: str) -> List[Dict[str, Any]]:
    """Universal robust parser for DD373 price list DOM."""
    soup = BeautifulSoup(html_content, 'lxml')
    
    def is_valid_row(tag):
        if tag.name not in ['div', 'li', 'ul', 'tr']:
            return False
        text = tag.get_text()
        if '元/个' not in text and '1元=' not in text and '1元 =' not in text:
            return False
        for child in tag.find_all(['div', 'li', 'ul', 'tr']):
            child_text = child.get_text()
            if '元/个' in child_text or '1元=' in child_text or '1元 =' in child_text:
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

            if '元/个' in p or '1元=' in p or '1元 =' in p:
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
    return clean_results

async def fetch_dd373_with_playwright(url: str, max_retries: int = 3) -> Tuple[List[Dict[str, Any]], str]:
    """
    Fetch DD373 page using Playwright stealth persistent browser context (Thread-safe with Lock).
    Returns (clean_items_list, cookie_header_string).
    """
    start_time = time.time()
    
    with _BROWSER_LOCK:
        logger.info(f"[Playwright Solver] Lock acquired for {url}. Launching browser...")
        clean_stale_singleton_lock()

        async with async_playwright() as p:
            try:
                DEFAULT_COOKIES = [
                    {"name": "_c_WBKFRo", "value": "00f00qFLqkrt0CSYGjQrJElEkP7dyK7D3yf6GErK", "domain": ".dd373.com", "path": "/"},
                    {"name": "acw_tc", "value": "a3b58c9d17858312098557763ee4e3e096cb78d45c666914afc35543b8", "domain": ".dd373.com", "path": "/"},
                    {"name": "cdn_sec_tc", "value": "a3b58c9d17858312098557763ee4e3e096cb78d45c666914afc35543b8", "domain": ".dd373.com", "path": "/"}
                ]

                context = await p.chromium.launch_persistent_context(
                    user_data_dir=PROFILE_DIR,
                    headless=False,
                    args=[
                        "--js-flags=--max-old-space-size=256",
                        "--disable-software-rasterizer",
                        "--disable-extensions",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--window-size=960,1040",
                        "--window-position=0,0",
                        "--lang=zh-CN,zh"
                    ],
                    ignore_default_args=["--enable-automation"],
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    viewport={"width": 940, "height": 960},
                    device_scale_factor=1,
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    java_script_enabled=True,
                    ignore_https_errors=True
                )

                existing_cookies = await context.cookies()
                if not existing_cookies:
                    try:
                        await context.add_cookies(DEFAULT_COOKIES)
                        logger.info("[Playwright Solver] Injected fallback cookies into context.")
                    except Exception:
                        pass
                else:
                    logger.info(f"[Playwright Solver] Using {len(existing_cookies)} fresh persistent cookies from profile.")

                page = context.pages[0] if context.pages else await context.new_page()
                try:
                    from playwright_stealth import stealth_async
                    await stealth_async(page)
                except ImportError:
                    pass
                await page.add_init_script(STEALTH_JS)

                response = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                status_code = response.status if response else 0

                await asyncio.sleep(0.5)

                for attempt in range(1, max_retries + 1):
                    content = await page.content()
                    if "aliyunCaptcha" in content or "verify that you are a real person" in content or "sliding-slider" in content:
                        solved = await solve_aliyun_slider(page)
                        if solved:
                            await asyncio.sleep(1.5)
                            break
                        else:
                            logger.warning(f"[Playwright Solver] Captcha solve attempt {attempt}/{max_retries} failed. Refreshing page...")
                            await page.reload(wait_until="domcontentloaded")
                            await asyncio.sleep(1.0)
                    else:
                        break

                html_content = await page.content()
                cookies = await context.cookies()
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

                clean_results = parse_dd373_html(html_content)
                exec_time = int((time.time() - start_time) * 1000)

                if len(clean_results) > 0:
                    SmartLogger.log_event(
                        platform="dd373",
                        level="INFO",
                        error_code="PARSED_SUCCESS",
                        message=f"Playwright successfully scraped {len(clean_results)} items from DD373",
                        details={"url": url, "http_status": status_code, "execution_time_ms": exec_time, "items_count": len(clean_results)}
                    )
                else:
                    if "aliyunCaptcha" in html_content or "sliding-slider" in html_content:
                        err_code = "WAF_CAPTCHA_BLOCKED"
                        err_msg = "Playwright page still blocked by Aliyun Captcha WAF"
                    else:
                        err_code = "DOM_ELEMENT_NOT_FOUND"
                        err_msg = "Playwright fetched page but failed to parse price table (DOM structure changed or no offers)"

                    SmartLogger.log_event(
                        platform="dd373",
                        level="ERROR",
                        error_code=err_code,
                        message=err_msg,
                        details={"url": url, "http_status": status_code, "execution_time_ms": exec_time},
                        screenshot_saved=True
                    )
                    await page.screenshot(path=LAST_ERROR_SCREENSHOT, full_page=True)

                await context.close()
                return clean_results, cookie_str

            except Exception as e:
                exec_time = int((time.time() - start_time) * 1000)
                logger.error(f"[Playwright Solver] Error fetching {url}: {e}")
                SmartLogger.log_event(
                    platform="dd373",
                    level="ERROR",
                    error_code="BROWSER_LAUNCH_ERROR",
                    message=f"Playwright execution exception: {str(e)}",
                    details={"url": url, "execution_time_ms": exec_time, "exception": str(e)}
                )
                return [], ""
