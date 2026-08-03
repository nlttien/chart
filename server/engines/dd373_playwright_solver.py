import os
import re
import time
import math
import random
import logging
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
// Overwrite navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
// Mock window.chrome
window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
// Overwrite navigator.languages
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
// Mock permissions
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

def generate_human_steps(distance: float) -> List[Tuple[float, float]]:
    """
    Generate realistic human mouse movement steps (X, Y jitter) with easing acceleration and slight overshoot.
    """
    steps = []
    current_x = 0.0
    current_y = 0.0
    
    # 90% distance with easing, slight overshoot
    main_distance = distance * (1.02 + random.uniform(0.01, 0.03))
    num_steps = random.randint(25, 40)
    
    for i in range(1, num_steps + 1):
        t = i / num_steps
        ease = 1 - math.pow(1 - t, 3)
        next_x = main_distance * ease
        dx = next_x - current_x
        dy = random.uniform(-1.5, 1.5)
        current_x = next_x
        current_y += dy
        steps.append((dx, dy))
        
    # Overshoot correction back to target
    correction_steps = random.randint(3, 6)
    target_overshoot_diff = current_x - distance
    for j in range(1, correction_steps + 1):
        back_dx = -(target_overshoot_diff / correction_steps) + random.uniform(-0.5, 0.5)
        back_dy = random.uniform(-1.0, 1.0)
        steps.append((back_dx, back_dy))
        
    return steps

async def solve_aliyun_slider(page: Page) -> bool:
    """
    Detect and slide Aliyun Captcha slider using realistic human mouse trajectory.
    """
    selectors = [
        '#aliyunCaptcha-sliding-slider',
        '.aliyunCaptcha-sliding-slider',
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

    # Measure container track width for precise slide distance
    slide_distance = 300.0
    track_selectors = [
        '#aliyunCaptcha-sliding-wrapper',
        '.aliyunCaptcha-sliding-wrapper',
        'div[class*="sliding-wrapper"]',
        '#nc_1_wrapper',
        '.nc-container'
    ]
    for t_sel in track_selectors:
        try:
            track_el = page.locator(t_sel).first
            if await track_el.count() > 0:
                t_box = await track_el.bounding_box()
                if t_box and t_box["width"] > box["width"]:
                    slide_distance = t_box["width"] - box["width"] - 2.0
                    logger.info(f"[Playwright Solver] Dynamic track width measured: {slide_distance:.1f}px")
                    break
        except Exception:
            pass

    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2

    SmartLogger.log_event(
        platform="dd373",
        level="INFO",
        error_code="CAPTCHA_SOLVING_ATTEMPT",
        message=f"Starting human-like drag on Aliyun Captcha (distance: {slide_distance:.1f}px)",
        details={"start_x": start_x, "start_y": start_y, "distance": slide_distance}
    )

    await page.mouse.move(start_x, start_y)
    await page.mouse.down()
    
    curr_x, curr_y = start_x, start_y
    trajectory = generate_human_steps(slide_distance)
    
    for dx, dy in trajectory:
        curr_x += dx
        curr_y += dy
        await page.mouse.move(curr_x, curr_y)
        time.sleep(random.uniform(0.008, 0.025))

    await page.mouse.up()
    time.sleep(2.5)

    page_content = await page.content()
    if "aliyunCaptcha" not in page_content and "Please complete the operation" not in page_content:
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

async def fetch_dd373_with_playwright(url: str, max_retries: int = 2) -> Tuple[List[Dict[str, Any]], str]:
    """
    Fetch DD373 page using Playwright stealth persistent browser context (Thread-safe with Lock).
    Returns (clean_items_list, cookie_header_string).
    """
    start_time = time.time()
    
    # Acquire lock to prevent ProcessSingleton collision
    with _BROWSER_LOCK:
        logger.info(f"[Playwright Solver] Lock acquired for {url}. Launching browser...")
        clean_stale_singleton_lock()

        async with async_playwright() as p:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=PROFILE_DIR,
                    headless=True,
                    channel="chromium",
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--window-size=1920,1080",
                        "--lang=zh-CN,zh"
                    ],
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )

                page = context.pages[0] if context.pages else await context.new_page()
                await page.add_init_script(STEALTH_JS)

                response = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                status_code = response.status if response else 0

                for attempt in range(1, max_retries + 1):
                    content = await page.content()
                    if "aliyunCaptcha" in content or "verify that you are a real person" in content or "sliding-slider" in content:
                        solved = await solve_aliyun_slider(page)
                        if solved:
                            await page.wait_for_load_state("networkidle", timeout=5000)
                            break
                        else:
                            logger.warning(f"[Playwright Solver] Captcha solve attempt {attempt}/{max_retries} failed. Reloading...")
                            await page.reload(wait_until="domcontentloaded")
                            time.sleep(2)
                    else:
                        break

                html_content = await page.content()
                cookies = await context.cookies()
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

                soup = BeautifulSoup(html_content, 'lxml')
                
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
                    SmartLogger.log_event(
                        platform="dd373",
                        level="ERROR",
                        error_code="DOM_ELEMENT_NOT_FOUND",
                        message="Playwright fetched page but failed to parse price table (DOM structure changed or blocked)",
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
