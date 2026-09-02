import os
import json
import logging
import asyncio
import time
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

ALLOWED_ORIGINS = [
    "http://192.168.2.113",
    "http://192.168.2.113:80",
    "http://192.168.2.113:8000",
    "http://192.168.2.113:5173",
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.middleware("http")
async def custom_cors_header_middleware(request, call_next):
    origin = request.headers.get("origin") or "*"
    
    if request.method == "OPTIONS":
        from fastapi.responses import Response
        response = Response(status_code=204)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true" if origin != "*" else "false"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true" if origin != "*" else "false"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

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
    
    SmartLogger.log_event(
        platform=platform,
        level="INFO",
        error_code="TAMPERMONKEY_DATA_RECEIVED",
        message=f"Received {len(records)} items from Tampermonkey browser for {payload.item_name}",
        details={"item_name": payload.item_name, "count": len(records)}
    )
    
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

cached_rates = {"USD": 25400.0, "CNY": 3850.0, "time": 0}

@app.get("/api/exchange_rate")
@app.get("/api/v1/exchange_rate")
async def exchange_rate():
    global cached_rates
    now = time.time()
    if now - cached_rates["time"] > 300:  # Cache 5 mins
        api_key = os.environ.get("EXCHANGERATE_API_KEY")
        if not api_key:
            logger.warning("EXCHANGERATE_API_KEY is not set, using fallback rates")
        else:
            try:
                import urllib.request
                import json
                url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("result") == "success" and "conversion_rates" in data:
                        usd_vnd = data["conversion_rates"].get("VND")
                        usd_cny = data["conversion_rates"].get("CNY")
                        if usd_vnd:
                            cached_rates["USD"] = float(usd_vnd)
                        if usd_vnd and usd_cny:
                            cached_rates["CNY"] = float(usd_vnd) / float(usd_cny)
                        cached_rates["time"] = now
            except Exception as e:
                logger.warning(f"Exchange rate fetch error: {e}")
    return {
        "status": "success",
        "rate_usd_vnd": cached_rates["USD"],
        "rate_cny_vnd": cached_rates["CNY"],
        "rate": cached_rates["USD"]
    }

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

class MarketRatesModel(BaseModel):
    usd_rate: Optional[float] = 26330.0
    rmb_rate: Optional[float] = 3850.0
    g2g_fee_rate: Optional[float] = 94.05
    eldo_fee_rate: Optional[float] = 91.2

@app.get("/api/v1/config/rates")
async def get_rates():
    """API lấy cấu hình tỉ giá USD, RMB và phí sàn G2G, Eldorado từ DB"""
    from server.database import get_market_rates_config
    rates = await asyncio.to_thread(get_market_rates_config)
    return {"status": "success", "rates": rates}

@app.post("/api/v1/config/rates")
async def update_rates(payload: MarketRatesModel = Body(...)):
    """API lưu tỉ giá & phí sàn vào SQLite DB central"""
    from server.database import save_market_rates_config
    rates = await asyncio.to_thread(
        save_market_rates_config,
        payload.usd_rate or 26330.0,
        payload.rmb_rate or 3850.0,
        payload.g2g_fee_rate or 94.05,
        payload.eldo_fee_rate or 91.2
    )
    msg = {
        "type": "rate_update",
        "rates": rates
    }
    await manager.broadcast(msg)
    return {"status": "success", "rates": rates}

@app.get("/api/v1/avatar/{seller_name}")
async def get_seller_avatar(seller_name: str, remote_url: Optional[str] = Query(None)):
    """API Phục vụ ảnh Avatar đã cào & lưu đệm cục bộ từ G2G / Eldorado"""
    from server.avatar_manager import get_avatar_file_path, download_and_cache_avatar, generate_fallback_svg_avatar
    
    file_path = get_avatar_file_path(seller_name)
    
    if not os.path.exists(file_path) and remote_url:
        await asyncio.to_thread(download_and_cache_avatar, seller_name, remote_url)
        
    if os.path.exists(file_path) and os.path.getsize(file_path) > 200:
        return FileResponse(file_path, media_type="image/png")
        
    svg_content = generate_fallback_svg_avatar(seller_name)
    return Response(content=svg_content, media_type="image/svg+xml")

@app.get("/api/v1/lowest")
async def api_global_lowest(item_name: Optional[str] = Query(None)):
    """API lấy giá thấp nhất (Lowest/Floor Price) toàn hệ thống hoặc theo item"""
    data = await asyncio.to_thread(get_lowest_prices, None, item_name)
    return {"status": "success", "lowest_prices": data}

@app.get("/api/v1/{platform}/lowest")
async def api_platform_lowest(platform: str, item_name: Optional[str] = Query(None)):
    """API lấy giá thấp nhất của một sàn cụ thể"""
    data = await asyncio.to_thread(get_lowest_prices, platform.lower(), item_name)
    return {"status": "success", "platform": platform, "lowest_prices": data}

@app.get("/api/v1/{platform}/snapshot")
async def api_platform_snapshot(platform: str, item_name: Optional[str] = Query(None)):
    plat = platform.lower()
    
    if plat == "dd373":
        from server.engines.dd373_engine import get_solving_state
        state = get_solving_state()
        if state.get("is_solving"):
            return {
                "status": "solving",
                "error_code": "CAPTCHA_SOLVING_IN_PROGRESS",
                "message": "Đang trong quá trình tự động giải mã Aliyun Captcha bằng Puppeteer Mouse Solver...",
                "platform": plat,
                "order_book": []
            }

    data = await asyncio.to_thread(get_latest_snapshot, plat, item_name, 86400 * 360)
    last_updated_at = data[0]["timestamp"] if data else None

    if not data:
        if plat == "dd373":
            from server.engines.dd373_engine import get_solving_state
            state = get_solving_state()
            if state.get("last_status") == "failed":
                return {
                    "status": "failed",
                    "error_code": state.get("error_code") or "CAPTCHA_SOLVE_FAILED",
                    "message": state.get("message") or "Không thể tự động giải mã Aliyun Captcha WAF trên trang DD373",
                    "details": state.get("details") or {},
                    "platform": plat,
                    "order_book": []
                }
        
        return {
            "status": "pending",
            "error_code": "DATA_NOT_YET_FETCHED",
            "message": "Chưa lấy được dữ liệu mới nhất (đang chờ đợt quét mới)",
            "platform": plat,
            "last_updated_at": None,
            "total_items": 0,
            "order_book": []
        }

    return {
        "status": "success",
        "platform": plat,
        "last_updated_at": last_updated_at,
        "total_items": len(data),
        "order_book": data
    }

@app.get("/api/v1/history")
async def api_global_history(
    platform: Optional[str] = Query(None),
    item_name: Optional[str] = Query(None),
    range: Optional[str] = Query('1d'),
    limit: int = Query(5000)
):
    logs = await asyncio.to_thread(get_history_logs, platform.lower() if platform else None, item_name, range, limit)
    return {"status": "success", "platform": platform, "item_name": item_name, "logs": logs, "data": logs}

@app.get("/api/v1/{platform}/history")
async def api_platform_history(
    platform: str,
    item_name: Optional[str] = Query(None),
    range: Optional[str] = Query('1d'),
    limit: int = Query(5000)
):
    logs = await asyncio.to_thread(get_history_logs, platform.lower(), item_name, range, limit)
    return {"status": "success", "platform": platform, "item_name": item_name, "logs": logs, "data": logs}

@app.get("/api/v1/{platform}/competitor_history")
async def api_platform_competitor_history(
    platform: str,
    item_name: str = Query(...),
    sellers: str = Query(...),
    hours: float = Query(24)
):
    seller_list = [s.strip() for s in sellers.split(',') if s.strip()]
    data = await asyncio.to_thread(get_competitor_history_logs, platform.lower(), item_name, seller_list, hours)
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

@app.post("/api/v1/{platform}/cookie")
async def api_update_platform_cookie(platform: str, payload: Dict[str, Any] = Body(...)):
    plat = platform.lower()
    cookie = payload.get("cookie", "").strip()
    if cookie:
        if plat == "dd373":
            from server.engines.dd373_engine import update_live_cookie
            update_live_cookie(cookie)
        SmartLogger.log_event(
            platform=plat,
            level="INFO",
            error_code="LIVE_COOKIE_UPDATED",
            message=f"Live verified cookie updated from browser for {plat}",
            details={"cookie_len": len(cookie)}
        )
        return {"status": "success", "platform": plat, "message": "Live cookie updated successfully"}
    raise HTTPException(status_code=400, detail="Empty cookie provided")

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
    stats = await asyncio.to_thread(SmartLogger.get_status, "dd373")
    return {"status": "success", "running": worker.is_running, "platform_stats": stats}

# --- SMART DIAGNOSTIC LOG & SCREENSHOT ENDPOINTS ---

@app.get("/api/v1/logs")
async def api_get_all_logs(limit: int = Query(50)):
    """Trả về danh sách log có cấu trúc (Structured JSON Logs) toàn hệ thống"""
    logs = await asyncio.to_thread(SmartLogger.get_logs, None, limit)
    return {"status": "success", "total_logs": len(logs), "logs": logs}

@app.get("/api/v1/{platform}/logs")
async def api_get_platform_logs(platform: str, limit: int = Query(50)):
    """Trả về log có cấu trúc cho một sàn cụ thể (VD: dd373)"""
    logs = await asyncio.to_thread(SmartLogger.get_logs, platform.lower(), limit)
    return {"status": "success", "platform": platform, "total_logs": len(logs), "logs": logs}

_DEBUG_MODE: Dict[str, bool] = {"dd373": True}

@app.get("/api/v1/{platform}/debug")
async def api_get_debug_mode(platform: str):
    plat = platform.lower()
    return {"status": "success", "platform": plat, "debug": _DEBUG_MODE.get(plat, False)}

@app.post("/api/v1/{platform}/debug")
async def api_toggle_debug_mode(platform: str, payload: Dict[str, Any] = Body(...)):
    plat = platform.lower()
    debug_enabled = bool(payload.get("debug", False))
    _DEBUG_MODE[plat] = debug_enabled
    await asyncio.to_thread(
        SmartLogger.log_event,
        platform=plat,
        level="INFO",
        error_code="DEBUG_MODE_TOGGLED",
        message=f"Debug mode set to {debug_enabled} for {plat}",
        details={"debug": debug_enabled}
    )
    return {"status": "success", "platform": plat, "debug": debug_enabled}

@app.get("/api/v1/{platform}/status")
async def api_get_platform_status(platform: str):
    """Trả về chi tiết trạng thái Scraper, tỷ lệ vượt Captcha, Cookie status"""
    status_info = await asyncio.to_thread(SmartLogger.get_status, platform.lower())
    status_info["debug"] = _DEBUG_MODE.get(platform.lower(), False)
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
