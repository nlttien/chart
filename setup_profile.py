#!/usr/bin/env python3
"""
Setup Chrome Persistent Profile for Unified Chart (DD373)
Usage: python3 setup_profile.py
"""

import os
import sys
import time
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("setup_profile")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROFILE_DIR = os.path.join(DATA_DIR, "dd373_playwright_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
"""

def clean_stale_singleton_lock():
    lock_file = os.path.join(PROFILE_DIR, "SingletonLock")
    if os.path.exists(lock_file) or os.path.islink(lock_file):
        try:
            os.remove(lock_file)
            logger.info("Cleaned stale SingletonLock file.")
        except Exception as e:
            logger.warning(f"Could not remove SingletonLock: {e}")

def main():
    clean_stale_singleton_lock()
    print("================================================================")
    print("🚀 CHƯƠNG TRÌNH SETUP CHROME PROFILE THẬT CHO CHART (DD373)")
    print("================================================================")
    print(f"📁 Thư mục lưu Profile: {PROFILE_DIR}")
    print("🌐 Đang mở Chrome giao diện thật để bạn đăng nhập DD373 / Google...")

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
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
                    "--window-size=1280,900",
                    "--lang=zh-CN,zh"
                ],
                ignore_default_args=["--enable-automation"],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900},
                device_scale_factor=1,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                java_script_enabled=True,
                ignore_https_errors=True
            )

            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script(STEALTH_JS)

            try:
                page.goto("https://www.dd373.com/", wait_until="commit", timeout=20000)
            except Exception as e:
                logger.warning(f"Page load note: {e}")

            print("\n" + "="*60)
            print("✋ [HƯỚNG DẪN SETUP]:")
            print("1. Hãy tự do đăng nhập / giải Captcha / tạo lịch sử trình duyệt trên DD373.")
            print("2. Khi đăng nhập xong và sẵn sàng, quay lại terminal này.")
            print("3. Nhấn phím [ENTER] bên dưới để hoàn tất & lưu lại Profile...")
            print("="*60 + "\n")

            try:
                input(">>> Nhấn ENTER tại đây để LƯU PROFILE THẬT & ĐÓNG TRÌNH DUYỆT... <<< ")
            except (KeyboardInterrupt, EOFError):
                pass

            cookies = context.cookies()
            logger.info(f"✅ Đã lưu thành công Profile Người Dùng Thật ({len(cookies)} cookies) vào {PROFILE_DIR}!")
            context.close()

        except Exception as e:
            logger.error(f"Setup Profile Exception: {e}")

if __name__ == "__main__":
    main()
