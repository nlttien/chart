import asyncio
import logging
import time
import gc
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from server.config import load_config
from server.database import save_market_batch
from server.engines.g2g_engine import scan_g2g_item
from server.engines.eldo_engine import scan_eldo_item
from server.engines.qiandao_engine import scan_qiandao_item
from server.engines.dd373_engine import scan_dd373_item

logger = logging.getLogger("background_worker")

# Giới hạn tối đa max_workers=1 & Semaphore(1) tối ưu bộ nhớ RAM cho môi trường máy ảo LXC Container
executor = ThreadPoolExecutor(max_workers=1)
_SEMAPHORE = asyncio.Semaphore(1)

class BackgroundWorker:
    def __init__(self, ws_manager=None):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.ws_manager = ws_manager
        self.last_run_time: Dict[str, float] = {}

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._run_loop())
            logger.info("Background Scraper Worker started.")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
            logger.info("Background Scraper Worker stopped.")

    async def _run_loop(self):
        while self.is_running:
            try:
                config = load_config()
                if not config.get("auto_scrape_enabled", True):
                    await asyncio.sleep(5)
                    continue

                interval = config.get("scrape_interval_seconds", 60)
                await self.scrape_all_platforms()
                gc.collect()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background worker loop: {e}")
                await asyncio.sleep(10)

    async def scrape_platform_item(self, platform: str, item: Dict[str, Any]):
        async with _SEMAPHORE:
            loop = asyncio.get_running_loop()
            name = item.get("name", "Unknown")
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

            results = []
            try:
                if platform == "g2g":
                    results = await loop.run_in_executor(executor, scan_g2g_item, item)
                elif platform == "eldorado":
                    results = await loop.run_in_executor(executor, scan_eldo_item, item)
                elif platform == "qiandao":
                    results = await loop.run_in_executor(executor, scan_qiandao_item, item)
                elif platform == "dd373":
                    results = await loop.run_in_executor(executor, scan_dd373_item, item)
            finally:
                gc.collect()

            if results:
                save_market_batch(platform, name, results, now_str)
                payload = {
                    "type": "market_update",
                    "platform": platform,
                    "item_name": name,
                    "timestamp": now_str,
                    "data": results
                }
                if self.ws_manager:
                    await self.ws_manager.broadcast(payload)

            await asyncio.sleep(1.0)
            return results

    async def scrape_all_platforms(self):
        config = load_config()
        # Chạy nối tiếp đơn luồng 1-by-1 để tiết kiệm RAM tối đa trên LXC Container
        for platform in ["dd373", "g2g", "eldorado", "qiandao"]:
            items = config.get(platform, [])
            for item in items:
                if item.get("enabled", True):
                    try:
                        await self.scrape_platform_item(platform, item)
                    except Exception as e:
                        logger.error(f"Error scraping {platform} item {item.get('name')}: {e}")
                    gc.collect()
