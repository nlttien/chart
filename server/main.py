import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from server.database import (
    init_db, save_market_batch, get_latest_snapshot, 
    get_history_logs, get_distinct_items, get_lowest_prices,
    get_competitor_history_logs
)
from server.config import load_config, save_config
from server.background_worker import BackgroundWorker
from server.smart_logger import SmartLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chart_server")

app = FastAPI(
    title="Unified Chart Market API & Web Server",
    version="2.1.0",
    description="REST API Server & Scraper Engine for DD373, Eldorado, G2G, Qiandao"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
worker = BackgroundWorker(ws_manager=manager)

@app.on_event("startup")
async def startup_event():
    init_db()
    worker.start()
    logger.info("Chart Server started successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    worker.stop()
    logger.info("Chart Server shut down.")

# --- MODELS ---
class MarketItemModel(BaseModel):
    seller: str
    unit_price: float
    stock: int
    sold_total: Optional[int] = 0
    online: Optional[str] = "Unknown"
    min_qty: Optional[int] = 0
    delivery: Optional[str] = ""
    ratio: Optional[str] = ""
    source: Optional[str] = "g2g"

class UpdatePayloadModel(BaseModel):
    item_name: str
    platform: Optional[str] = "g2g"
    data: List[MarketItemModel]

# --- LEGACY / COMPATIBILITY ENDPOINTS ---

@app.post("/update_data")
async def update_data(payload: UpdatePayloadModel):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    platform = payload.platform.lower() if payload.platform else "g2g"
    records = [item.dict() for item in payload.data]
    save_market_batch(platform, payload.item_name, records, now_str)
    
    msg = {
        "type": "market_update",
        "platform": platform,
        "item_name": payload.item_name,
        "timestamp": now_str,
        "data": records
    }
    await manager.broadcast(msg)
    return {"status": "success", "platform": platform, "count": len(records)}

@app.get("/snapshot")
async def legacy_snapshot(
    platform: Optional[str] = Query("g2g"),
    item_name: Optional[str] = Query(None)
):
    data = get_latest_snapshot(platform.lower() if platform else None, item_name)
    return {"status": "success", "platform": platform, "order_book": data}

@app.get("/history")
async def legacy_history(
    platform: Optional[str] = Query("g2g"),
    item_name: str = Query(...)
):
    logs = get_history_logs(platform.lower() if platform else None, item_name)
    return {"status": "success", "platform": platform, "item_name": item_name, "logs": logs}

@app.get("/competitor_history")
async def legacy_competitor_history(
    item_name: str = Query(...),
    sellers: str = Query(...),
    hours: float = Query(24),
    platform: Optional[str] = Query(None)
):
    seller_list = [s.strip() for s in sellers.split(',') if s.strip()]
    data = get_competitor_history_logs(platform.lower() if platform else None, item_name, seller_list, hours)
    return {"status": "success", "data": data}

@app.get("/items")
async def legacy_items(platform: Optional[str] = Query("g2g")):
    items = get_distinct_items(platform.lower() if platform else None)
    return {"status": "success", "platform": platform, "items": items}

@app.get("/api/exchange_rate")
async def exchange_rate():
    return {"status": "success", "rate": 25400.0}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"pong: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- UNIFIED REST API V1 ENDPOINTS ---

@app.get("/api/v1/health")
async def api_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker_running": worker.is_running
    }

@app.get("/api/v1/platforms")
async def api_platforms():
    return {
        "platforms": [
            {"id": "dd373", "name": "DD373 (China)"},
            {"id": "eldorado", "name": "Eldorado (Global)"},
            {"id": "g2g", "name": "G2G (Global)"},
            {"id": "qiandao", "name": "Qiandao (China)"}
        ]
    }

@app.get("/api/v1/lowest")
async def api_global_lowest(item_name: Optional[str] = Query(None)):
    """API lấy giá thấp nhất (Lowest/Floor Price) toàn hệ thống hoặc theo item"""
    data = get_lowest_prices(platform=None, item_name=item_name)
    return {"status": "success", "lowest_prices": data}

@app.get("/api/v1/{platform}/lowest")
async def api_platform_lowest(platform: str, item_name: Optional[str] = Query(None)):
    """API lấy giá thấp nhất của một sàn cụ thể"""
    data = get_lowest_prices(platform=platform.lower(), item_name=item_name)
    return {"status": "success", "platform": platform, "lowest_prices": data}

@app.get("/api/v1/{platform}/snapshot")
async def api_platform_snapshot(platform: str, item_name: Optional[str] = Query(None)):
    plat = platform.lower()
    data = get_latest_snapshot(plat, item_name)
    
    # Auto-trigger scraper if DB is empty or has no snapshot data
    if not data:
        config = load_config()
        items = config.get(plat, [])
        for item in items:
            if not item_name or item.get("name") == item_name:
                await worker.scrape_platform_item(plat, item)
        data = get_latest_snapshot(plat, item_name)

    return {"status": "success", "platform": plat, "order_book": data}

@app.get("/api/v1/{platform}/history")
async def api_platform_history(platform: str, item_name: str = Query(...)):
    logs = get_history_logs(platform.lower(), item_name)
    return {"status": "success", "platform": platform, "item_name": item_name, "logs": logs}

@app.get("/api/v1/{platform}/competitor_history")
async def api_platform_competitor_history(
    platform: str,
    item_name: str = Query(...),
    sellers: str = Query(...),
    hours: float = Query(24)
):
    seller_list = [s.strip() for s in sellers.split(',') if s.strip()]
    data = get_competitor_history_logs(platform.lower(), item_name, seller_list, hours)
    return {"status": "success", "platform": platform, "data": data}

@app.get("/api/v1/{platform}/items")
async def api_platform_items(platform: str):
    config = load_config()
    items = config.get(platform.lower(), [])
    return {"status": "success", "platform": platform, "items": items}

@app.post("/api/v1/{platform}/items")
async def api_add_platform_item(platform: str, item: Dict[str, Any] = Body(...)):
    config = load_config()
    plat = platform.lower()
    if plat not in config:
        config[plat] = []
    config[plat].append(item)
    save_config(config)
    return {"status": "success", "platform": plat, "items": config[plat]}

@app.post("/api/v1/{platform}/scrape")
async def api_trigger_scrape(platform: str, item_name: Optional[str] = Query(None)):
    config = load_config()
    plat = platform.lower()
    items = config.get(plat, [])
    
    scraped_count = 0
    for item in items:
        if not item_name or item.get("name") == item_name:
            await worker.scrape_platform_item(plat, item)
            scraped_count += 1
            
    return {"status": "success", "platform": plat, "items_scraped": scraped_count}

@app.get("/api/v1/config")
async def api_get_config():
    return load_config()

@app.post("/api/v1/config")
async def api_update_config(new_config: Dict[str, Any] = Body(...)):
    save_config(new_config)
    return {"status": "success", "config": new_config}

@app.post("/api/v1/scraper/start")
async def api_start_scraper():
    worker.start()
    return {"status": "success", "running": worker.is_running}

@app.post("/api/v1/scraper/stop")
async def api_stop_scraper():
    worker.stop()
    return {"status": "success", "running": worker.is_running}

@app.get("/api/v1/scraper/status")
async def api_scraper_status():
    return {"status": "success", "running": worker.is_running, "platform_stats": SmartLogger.get_status("dd373")}

# --- SMART DIAGNOSTIC LOG & SCREENSHOT ENDPOINTS ---

@app.get("/api/v1/logs")
async def api_get_all_logs(limit: int = Query(50)):
    """Trả về danh sách log có cấu trúc (Structured JSON Logs) toàn hệ thống"""
    logs = SmartLogger.get_logs(platform=None, limit=limit)
    return {"status": "success", "total_logs": len(logs), "logs": logs}

@app.get("/api/v1/{platform}/logs")
async def api_get_platform_logs(platform: str, limit: int = Query(50)):
    """Trả về log có cấu trúc cho một sàn cụ thể (VD: dd373)"""
    logs = SmartLogger.get_logs(platform=platform.lower(), limit=limit)
    return {"status": "success", "platform": platform, "total_logs": len(logs), "logs": logs}

@app.get("/api/v1/{platform}/status")
async def api_get_platform_status(platform: str):
    """Trả về chi tiết trạng thái Scraper, tỷ lệ vượt Captcha, Cookie status"""
    status_info = SmartLogger.get_status(platform=platform.lower())
    return {"status": "success", "platform": platform, "details": status_info}

@app.get("/api/v1/{platform}/screenshot")
async def api_get_platform_screenshot(platform: str):
    """Trả về ảnh chụp màn hình debug lỗi gần nhất (nếu có)"""
    img_path = SmartLogger.get_last_error_screenshot()
    if img_path and os.path.exists(img_path):
        return FileResponse(img_path, media_type="image/png")
    raise HTTPException(status_code=404, detail=f"No error screenshot available for {platform}")

@app.get("/api/v1/{platform}/clip")
async def api_get_platform_clip(platform: str):
    """Trả về video clip ghi lại thao tác giải Captcha gần nhất"""
    plat = platform.lower()
    video_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "videos", plat)
    if os.path.exists(video_dir):
        files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith(".webm")]
        if files:
            latest_video = max(files, key=os.path.getmtime)
            return FileResponse(latest_video, media_type="video/webm")
    raise HTTPException(status_code=404, detail=f"No video clip available for {platform}")

# --- STATIC FILES FOR UNIFIED WEB UI ---
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "unified-chart", "dist")

if os.path.exists(WEB_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(WEB_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_web_ui(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(WEB_DIR, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(WEB_DIR, "index.html"))
