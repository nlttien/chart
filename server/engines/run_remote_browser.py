import os
import sys
import time
import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("remote_browser")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PROFILE_DIR = os.path.join(DATA_DIR, "dd373_playwright_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
"""

async def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.dd373.com/s-3hcpqw-bwgvrk-fj6p5a-0-0-0-8rknmp-0-0-receive-0-0-1-0-0-0.html"
    logger.info("=========================================================")
    logger.info("Starting Playwright Remote Debugging Browser on Port 9222...")
    logger.info("=========================================================")
    
    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=True,
                channel="chromium",
                args=[
                    "--remote-debugging-port=9222",
                    "--remote-debugging-address=0.0.0.0",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--lang=zh-CN,zh"
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )

            page = context.pages[0] if context.pages else await context.new_page()
            await page.add_init_script(STEALTH_JS)

            logger.info(f"Navigating to {target_url}...")
            await page.goto(target_url, wait_until="domcontentloaded")
            
            logger.info("---------------------------------------------------------")
            logger.info("SUCCESS: Browser is running on remote port 9222!")
            logger.info("On your Local Chrome browser, open a new tab and go to:")
            logger.info("   chrome://inspect")
            logger.info("Click 'Inspect' on the page to view and drag the Captcha manually!")
            logger.info("Press Ctrl+C in this terminal when finished.")
            logger.info("---------------------------------------------------------")

            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping Remote Browser...")
        except Exception as e:
            logger.error(f"Remote Browser Exception: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())
