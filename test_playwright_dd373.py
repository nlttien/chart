#!/usr/bin/env python3
"""
Test Playwright Chrome DD373 (Half Screen 960x1040 & CDP Attach Mode)
Chế độ:
  1. Setup Profile (--setup): Mở Chrome để bạn tự do đăng nhập Google/DD373.
  2. Bot Tự Động Running (--run): Bot nạp Profile Thật, tự động kéo slider WAF & cào dữ liệu.
  3. Kết Nối Chrome Đang Chạy (--attach): Connect trực tiếp vào Chrome đang mở sẵn qua cổng 9222.
"""

import os
import sys
import time
import random
import re
import math
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
    HAS_PLAYWRIGHT_STEALTH = True
except ImportError:
    HAS_PLAYWRIGHT_STEALTH = False

TEST_URL = "https://www.dd373.com/s-49phxm-0-0-0-0-0-0-0-0-1-0-0-0.html?Keyword=%E6%B5%81%E4%BA%A1"

SELECTORS = [
    '#aliyunCaptcha-sliding-slider',
    '#nc_1_n1z',
    '.nc_iconfont.btn_slide',
    'span[id*="sliding"]',
    '.btn_slide',
    'div[class*="sliding"] span'
]

DEFAULT_COOKIES = [
    {
        "name": "_c_WBKFRo",
        "value": "00f00qFLqkrt0CSYGjQrJElEkP7dyK7D3yf6GErK",
        "domain": ".dd373.com",
        "path": "/"
    },
    {
        "name": "acw_tc",
        "value": "a3b58c9d17858312098557763ee4e3e096cb78d45c666914afc35543b8",
        "domain": ".dd373.com",
        "path": "/"
    },
    {
        "name": "cdn_sec_tc",
        "value": "a3b58c9d17858312098557763ee4e3e096cb78d45c666914afc35543b8",
        "domain": ".dd373.com",
        "path": "/"
    }
]

def inject_default_cookies(context):
    try:
        context.add_cookies(DEFAULT_COOKIES)
        print("🍪 Đã nạp thành công 3 Cookie Aliyun WAF hợp lệ vào Chrome (_c_WBKFRo, acw_tc, cdn_sec_tc)!")
    except Exception as e:
        print(f"⚠️ Thông báo nạp Cookie: {e}")

def parse_number(text: str) -> float:
    if not text: return 0.0
    matches = re.findall(r"(\d+\.?\d*)", text)
    return float(matches[0]) if matches else 0.0

def check_captcha_exists(page):
    for sel in SELECTORS:
        try:
            elem = page.query_selector(sel)
            if elem and elem.is_visible():
                return elem
        except Exception:
            pass

    for frame in page.frames:
        for sel in SELECTORS:
            try:
                elem = frame.query_selector(sel)
                if elem and elem.is_visible():
                    return elem
            except Exception:
                pass
    return None

def generate_human_mouse_steps(start_x, start_y, distance):
    """
    Tạo quỹ đạo chuột người thật với tốc độ nhanh & dứt khoát (~0.3s):
    - Gia tốc Ease-In-Out tự nhiên.
    - Kéo văng quá đà lề phải (+15px đến +25px) ra khỏi ô trượt luôn.
    - Rút nhẹ chuột về vị trí đích (Bounce Back).
    """
    steps = []
    current_x = start_x
    current_y = start_y

    overshoot = random.uniform(15.0, 25.0)
    target_overshoot_x = distance + overshoot

    main_steps = random.randint(14, 20)
    for i in range(1, main_steps + 1):
        t = i / main_steps
        ease = 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2
        next_x = start_x + (target_overshoot_x * ease)
        dx = next_x - current_x
        dy = math.sin(t * math.pi) * random.uniform(0.2, 0.6) + random.uniform(-0.3, 0.3)

        current_x = next_x
        current_y += dy
        delay = random.uniform(0.005, 0.015)
        steps.append((current_x, current_y, delay))

    steps.append((current_x, current_y, random.uniform(0.03, 0.06)))

    correction_steps = random.randint(4, 7)
    final_target_x = start_x + distance + 4.0
    for j in range(1, correction_steps + 1):
        t = j / correction_steps
        ease = math.sin(t * math.pi / 2)
        next_x = current_x + (final_target_x - current_x) * ease
        dy = random.uniform(-0.2, 0.2)
        current_x = next_x
        current_y += dy
        delay = random.uniform(0.005, 0.012)
        steps.append((current_x, current_y, delay))

    return steps

def solve_aliyun_slider(page):
    slider_elem = check_captcha_exists(page)
    if slider_elem:
        print("\n🤖 [BOT TỰ KÉO SLIDER] Phát hiện thanh trượt xác minh Aliyun Captcha!")
        print("🤖 Bot đang thực hiện kéo văng quá đà lề phải (+20px ra khỏi ô trượt) & rút nhẹ về đích...")
        
        box = slider_elem.bounding_box()
        if box:
            track_selectors = [
                '#aliyunCaptcha-sliding-body',
                '.sliding',
                '#aliyunCaptcha-sliding-wrapper',
                '.aliyunCaptcha-sliding-wrapper',
                'div[class*="sliding-wrapper"]',
                'div[class*="nc-container"]'
            ]

            slide_distance = 345.0
            for t_sel in track_selectors:
                try:
                    t_elem = page.query_selector(t_sel)
                    if t_elem:
                        t_box = t_elem.bounding_box()
                        if t_box and t_box['width'] > box['width']:
                            measured = t_box['width'] - box['width']
                            if 250 < measured < 400:
                                slide_distance = measured
                                break
                except Exception:
                    pass

            start_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] / 2

            page.mouse.move(start_x, start_y)
            page.mouse.down()
            time.sleep(random.uniform(0.15, 0.3))

            steps = generate_human_mouse_steps(start_x, start_y, slide_distance)
            for x, y, delay in steps:
                page.mouse.move(x, y)
                time.sleep(delay)

            time.sleep(0.35)
            page.mouse.up()
            print(f"✅ [BOT TỰ KÉO SLIDER] Đã hoàn tất kĩ thuật kéo văng quá đà & rút về đích ({slide_distance:.1f}px). Chờ xác thực (3s)...")
            time.sleep(3)
            return True
    return False

def extract_valid_offers(page):
    items = page.query_selector_all("div, li, tr")
    valid_offers = []
    for item in items:
        try:
            text = item.inner_text()
            if ('元/个' in text or '1元=' in text) and len(text) < 300:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                price = 0.0
                for l in lines:
                    if '元/个' in l or '1元=' in l:
                        price = parse_number(l)
                        break
                if price > 0:
                    valid_offers.append({"text_snippet": " | ".join(lines[:4]), "price": price})
        except Exception:
            pass
    return valid_offers

def run_attach_mode(cdp_url="http://127.0.0.1:9222"):
    """KẾT NỐI TRỰC TIẾP VÀO GOOGLE CHROME ĐANG CHẠY SẴN QUẢ CỔNG DEBUG 9222"""
    print("\n================================================================")
    print("🔌 [CHẾ ĐỘ ATTACH] KẾT NỐI VÀO CHROME ĐANG CHẠY SẴN QUẢ CỔNG 9222")
    print("================================================================")
    print(f"🔗 Đang kết nối tới Chrome qua {cdp_url}...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            print("✅ Kết nối tới Google Chrome đang mở thành công!")
        except Exception as e:
            print(f"❌ Không thể kết nối tới {cdp_url}: {e}")
            print("\n💡 HƯỚNG DẪN BẬT CHROME CÓ CỔNG DEBUG 9222:")
            print("  google-chrome --remote-debugging-port=9222 --user-data-dir=~/chrome_dev_profile &\n")
            return

        context = browser.contexts[0] if len(browser.contexts) > 0 else browser.new_context()
        page = context.pages[0] if len(context.pages) > 0 else context.new_page()

        if HAS_PLAYWRIGHT_STEALTH:
            stealth_sync(page)

        inject_default_cookies(context)

        print(f"🌐 Đang nạp trang test DD373 trên trình duyệt Chrome gốc...")
        try:
            page.goto(TEST_URL, wait_until="commit", timeout=15000)
        except Exception as e:
            print(f"⚠️ Thông báo khi nạp trang: {e}")
        time.sleep(2)

        c_elem = check_captcha_exists(page)
        if c_elem:
            solve_aliyun_slider(page)
        else:
            print("ℹ️ Không phát hiện Captcha WAF slider, trang nạp thành công!")

        time.sleep(2)
        offers = extract_valid_offers(page)

        print("\n================================================================")
        print("📊 BÁO CÁO KẾT QUẢ KẾT NỐI CHROME ĐANG CHẠY:")
        print("================================================================")
        if len(offers) > 0:
            print(f"🎉 SUCCESS: TÌM THẤY {len(offers)} GIAN HÀNG:")
            for idx, offer in enumerate(offers[:5], 1):
                print(f"  {idx}. Giá: {offer['price']} ¥ | Chi tiết: {offer['text_snippet']}")
        else:
            if "aliyunCaptcha" in page.content():
                print("❌ FAILED: Trang bị Aliyun WAF khóa.")
            else:
                print("⚠️ WARNING: Trang nạp thành công nhưng không có gian hàng.")

        print("✅ Đã xử lý xong (Trình duyệt Chrome vẫn tiếp tục mở để bạn sử dụng).")

def setup_real_user_profile(profile_dir):
    """BƯỚC 1: SETUP PROFILE NGƯỜI DÙNG THẬT"""
    print("\n================================================================")
    print("👤 [GIAI ĐOẠN 1] SETUP PROFILE NGƯỜI DÙNG THẬT")
    print("================================================================")
    print("👉 Mở trình duyệt Chrome ở 1 NỬA MÀN HÌNH.")
    print("👉 Bạn hãy tự do Đăng nhập Google / DD373 / Duyệt web như người thật.")
    print("📌 Toàn bộ Cookie & Session sẽ được lưu cố định vào Profile.\n")

    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": profile_dir,
            "headless": False,
            "args": [
                '--ignore-gpu-blocklist',
                '--enable-webgl',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--window-size=960,1040',
                '--window-position=0,0'
            ],
            "ignore_default_args": ["--enable-automation"],
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "viewport": {"width": 940, "height": 960}
        }

        try:
            context = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
        except Exception:
            context = p.chromium.launch_persistent_context(**launch_kwargs)

        page = context.pages[0] if len(context.pages) > 0 else context.new_page()

        if HAS_PLAYWRIGHT_STEALTH:
            stealth_sync(page)

        print("🌐 Đang mở trang Đăng nhập Google / DD373...")
        try:
            page.goto("https://accounts.google.com/", wait_until="commit", timeout=15000)
        except Exception:
            pass

        print("\n" + "="*60)
        print("✋ [HƯỚNG DẪN SETUP]:")
        print("1. Đăng nhập tài khoản Google / DD373 trên cửa sổ Chrome mở sẵn.")
        print("2. Duyệt web bình thường để tạo lịch sử & Cookie người dùng thật.")
        print("3. Khi đã sẵn sàng, nhấn phím ENTER bên dưới để lưu Profile...")
        print("="*60 + "\n")

        try:
            input(">>> Nhấn ENTER tại đây để HOÀN TẤT SETUP PROFILE & LƯU TÀI KHOẢN... <<< ")
        except (KeyboardInterrupt, EOFError):
            pass

        cookies = context.cookies()
        print(f"✅ Đã lưu thành công Profile Người Dùng Thật ({len(cookies)} cookies) vào thư mục!")
        context.close()

def run_bot_auto(profile_dir):
    """BƯỚC 2: BOT TỰ ĐỘNG RUNNING (Sử dụng Profile Thật đã setup để tự kéo WAF & cào dữ liệu)"""
    print("\n================================================================")
    print("🤖 [GIAI ĐOẠN 2] BOT TỰ ĐỘNG CHẠY VỚI PROFILE THẬT")
    print("================================================================")
    print(f"📁 Nạp Persistent Profile Người Dùng Thật tại: {profile_dir}")
    print("🌐 Đang mở trang sản phẩm DD373...")

    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": profile_dir,
            "headless": False,
            "args": [
                '--ignore-gpu-blocklist',
                '--enable-webgl',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--window-size=960,1040',
                '--window-position=0,0'
            ],
            "ignore_default_args": ["--enable-automation"],
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "viewport": {"width": 940, "height": 960}
        }

        try:
            context = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
        except Exception:
            context = p.chromium.launch_persistent_context(**launch_kwargs)

        page = context.pages[0] if len(context.pages) > 0 else context.new_page()

        if HAS_PLAYWRIGHT_STEALTH:
            stealth_sync(page)

        inject_default_cookies(context)

        try:
            page.goto(TEST_URL, wait_until="commit", timeout=15000)
        except Exception as e:
            print(f"⚠️ Thông báo khi nạp trang: {e}")
        time.sleep(3)

        c_elem = check_captcha_exists(page)
        if c_elem:
            solve_aliyun_slider(page)
        else:
            print("ℹ️ Không phát hiện WAF Captcha, trang đã nạp thẳng thành công!")

        time.sleep(3)
        offers = extract_valid_offers(page)

        print("\n================================================================")
        print("📊 BÁO CÁO KẾT QUẢ BOT TỰ ĐỘNG CHẠY VỚI PROFILE THẬT:")
        print("================================================================")
        if len(offers) > 0:
            print(f"🎉 SUCCESS: BOT GIẢI MÃ THÀNH CÔNG! Tìm thấy {len(offers)} gian hàng:")
            for idx, offer in enumerate(offers[:5], 1):
                print(f"  {idx}. Giá: {offer['price']} ¥ | Chi tiết: {offer['text_snippet']}")
        else:
            if "aliyunCaptcha" in page.content():
                print("❌ FAILED: Trang bị Aliyun WAF khóa.")
            else:
                print("⚠️ WARNING: Trang không vướng Captcha nhưng không thấy dữ liệu gian hàng.")

        print("\n🕒 Giữ cửa sổ Chrome 10 giây để bạn kiểm tra...")
        time.sleep(10)
        context.close()
        print("✅ Hoàn tất kiểm tra.")

def main():
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "browser_user_profile")
    os.makedirs(profile_dir, exist_ok=True)

    if "--attach" in sys.argv:
        run_attach_mode()
        return
    elif "--setup" in sys.argv:
        setup_real_user_profile(profile_dir)
        return
    elif "--run" in sys.argv:
        run_bot_auto(profile_dir)
        return

    print("================================================================")
    print("🚀 CHƯƠNG TRÌNH TEST PLAYWRIGHT CHROME")
    print("================================================================")
    print("Lựa chọn chế độ chạy:")
    print("  [1] Kết nối trực tiếp vào Google Chrome đang mở sẵn (Cổng 9222) - RẤT KHUYÊN DÙNG")
    print("  [2] Setup Profile Người Dùng Thật (Đăng nhập Google/DD373)")
    print("  [3] Chạy Bot Tự Động với Profile Thật")
    print("================================================================")

    choice = input("👉 Nhập lựa chọn (1, 2 hoặc 3) [Mặc định 1]: ").strip()

    if choice == "2":
        setup_real_user_profile(profile_dir)
    elif choice == "3":
        run_bot_auto(profile_dir)
    else:
        run_attach_mode()

if __name__ == "__main__":
    main()
