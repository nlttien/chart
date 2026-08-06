import sqlite3
import time
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
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
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

DB_NAME = "g2g_market.db"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    
    # [UPDATE] Thêm các cột mới cho DD373: min_qty, ratio, delivery, platform
    c.execute('''CREATE TABLE IF NOT EXISTS market_logs
                 (timestamp TEXT, 
                  seller TEXT, 
                  price REAL, 
                  stock INTEGER, 
                  sold INTEGER, 
                  online TEXT, 
                  item_name TEXT,
                  min_qty INTEGER DEFAULT 0,
                  ratio TEXT DEFAULT '',
                  delivery TEXT DEFAULT '',
                  platform TEXT DEFAULT 'g2g')''')
                  
    # Index để query nhanh
    c.execute('''CREATE INDEX IF NOT EXISTS idx_logs_item_time 
                 ON market_logs (item_name, timestamp)''')
    conn.commit()
    conn.close()

init_db()

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# --- MODELS (CẬP NHẬT CHO DD373) ---
class MarketItem(BaseModel):
    seller: str
    unit_price: float
    stock: int
    # Các trường của G2G (Optional)
    sold_total: Optional[int] = 0
    online: Optional[str] = "Unknown"
    # Các trường của DD373 (Optional)
    min_qty: Optional[int] = 0
    delivery: Optional[str] = ""
    ratio: Optional[str] = ""
    source: Optional[str] = "g2g"

class UpdatePayload(BaseModel):
    item_name: str
    platform: Optional[str] = "g2g" # Nhận biết nguồn dữ liệu
    data: List[MarketItem]

# --- HELPERS ---
def parse_db_time(time_str):
    try:
        if time_str.endswith('Z'):
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%SZ")
            return dt.replace(tzinfo=timezone.utc).timestamp()
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.timestamp()
    except:
        return 0

def calculate_change(current, old):
    if old == 0: return 0.0
    return ((current - old) / old) * 100

def get_floor_prices(rows, platform="g2g"):
    if not rows: return 0, 0

    def safe_int(val):
        try:
            if val is None: return 0
            if isinstance(val, str):
                val = val.replace('.', '').replace(',', '')
            return int(float(val))
        except:
            return 0

    def get_price(r):
        return r.get('unit_price', 0) if isinstance(r, dict) else r[1]
    
    def get_stock(r):
        return r.get('stock', 0) if isinstance(r, dict) else r[2]

    if platform == "dd373":
        # DD373 Recycle: Ưu tiên giá CAO NHẤT (Giá giảm dần, Stock giảm dần)
        sorted_rows = sorted(rows, key=lambda x: (
            get_price(x) if get_price(x) is not None else -float('inf'),
            safe_int(get_stock(x))
        ), reverse=True)
    else:
        # G2G Mua: Ưu tiên giá THẤP NHẤT (Giá tăng dần, Stock giảm dần)
        sorted_rows = sorted(rows, key=lambda x: (
            get_price(x) if get_price(x) is not None else float('inf'), 
            -safe_int(get_stock(x))
        ))
    
    raw = get_price(sorted_rows[0])
    
    # Lấy top 5
    top_5 = sorted_rows[:5]
    
    # Tìm seller có stock lớn nhất trong top 5
    highest_stock_seller = max(top_5, key=lambda x: safe_int(get_stock(x)))
    trusted = get_price(highest_stock_seller)
    
    return raw, trusted

# --- API ENDPOINTS ---

@app.post("/update_data")
async def receive_data(payload: UpdatePayload):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # [UPDATE] Insert đủ 11 cột
    data_to_insert = [
        (
            timestamp, 
            item.seller, 
            item.unit_price, 
            item.stock, 
            item.sold_total, 
            item.online, 
            payload.item_name,
            item.min_qty,  # New
            item.ratio,    # New
            item.delivery, # New
            payload.platform # New
        )
        for item in payload.data
    ]
    
    cursor.executemany("""
        INSERT INTO market_logs 
        (timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_to_insert)
    conn.commit()
    
    # Tính toán nhanh để broadcast
    # Convert item objects to dicts for helper function
    temp_rows = [item.dict() for item in payload.data]
    raw_floor, trusted_floor = get_floor_prices(temp_rows, platform=payload.platform)
    
    conn.close()

    socket_msg = {
        "type": "UPDATE",
        "timestamp": timestamp,
        "item_name": payload.item_name,
        "platform": payload.platform,
        "raw_floor": raw_floor,     # DD373: Max Price, G2G: Min Price
        "trusted_floor": trusted_floor,
        "order_book": [item.dict() for item in payload.data]
    }
    await manager.broadcast(socket_msg)
    return {"status": "success"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

cached_cny_vnd = {"value": 3851.0, "time": 0}

@app.get("/api/exchange_rate")
async def get_exchange_rate():
    global cached_cny_vnd
    now = time.time()
    if now - cached_cny_vnd["time"] > 300: # Cache 5 mins
        try:
            import urllib.request
            import re
            req = urllib.request.Request('https://www.google.com/finance/quote/CNY-VND', headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req).read().decode('utf-8')
            matches = re.findall(r'"CNY / VND",\d+,null,\[([\d\.]+)', html)
            if matches:
                rate = float(matches[0])
                cached_cny_vnd = {"value": rate, "time": now}
        except Exception as e:
            print("Exchange rate fetch error:", e)
    return {"cny_vnd": cached_cny_vnd["value"]}

@app.get("/snapshot")
def get_snapshot(item_name: str, hours: float = 24):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    norm_name = item_name.replace(' ', '').lower()
    # Lấy dữ liệu mới nhất
    cursor.execute("SELECT MAX(timestamp), platform FROM market_logs WHERE LOWER(REPLACE(item_name, ' ', '')) = ?", (norm_name,))
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close(); return {}
    
    latest_ts = row[0]
    platform = row[1] if len(row) > 1 and row[1] else "g2g"

    # Lấy Order Book chi tiết (Thêm các cột mới)
    query_book = """
        SELECT seller, price, stock, sold, online, min_qty, ratio, delivery
        FROM market_logs 
        WHERE LOWER(REPLACE(item_name, ' ', '')) = ? AND timestamp = ?
    """
    # Sort: DD373 giá cao lên đầu, G2G giá thấp lên đầu
    if platform == "dd373":
        query_book += " ORDER BY price DESC"
    else:
        query_book += " ORDER BY price ASC"

    cursor.execute(query_book, (norm_name, latest_ts))
    current_rows_db = cursor.fetchall()

    # Format Order Book trả về
    order_book = []
    # Convert DB rows to list of dicts/tuples giả lập cho hàm get_floor
    calc_rows = [] 

    for r in current_rows_db:
        item_dict = {
            "seller": r[0], "unit_price": r[1], "stock": r[2], 
            "sold_total": r[3], "online": r[4],
            "min_qty": r[5], "ratio": r[6], "delivery": r[7]
        }
        order_book.append(item_dict)
        # Tạo tuple giả lập cấu trúc cũ cho hàm get_floor_prices (nếu dùng tuple logic)
        # (seller, price, stock, sold, online)
        calc_rows.append((r[0], r[1], r[2], r[3], r[4]))

    cur_raw, cur_trusted = get_floor_prices(calc_rows, platform=platform)

    # Lấy dữ liệu QUÁ KHỨ để tính % Change
    time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%SZ")
    
    cursor.execute("SELECT MIN(timestamp) FROM market_logs WHERE LOWER(REPLACE(item_name, ' ', '')) = ? AND timestamp >= ?", (norm_name, time_threshold))
    old_ts_row = cursor.fetchone()
    
    old_raw = cur_raw 
    old_trusted = cur_trusted

    if old_ts_row and old_ts_row[0]:
        old_ts = old_ts_row[0]
        cursor.execute("SELECT seller, price, stock, sold, online FROM market_logs WHERE LOWER(REPLACE(item_name, ' ', '')) = ? AND timestamp = ?", (norm_name, old_ts))
        old_rows_db = cursor.fetchall()
        old_raw, old_trusted = get_floor_prices(old_rows_db, platform=platform)

    pct_raw = calculate_change(cur_raw, old_raw)
    pct_trusted = calculate_change(cur_trusted, old_trusted)

    conn.close()

    return {
        "type": "SNAPSHOT",
        "timestamp": latest_ts,
        "item_name": item_name,
        "platform": platform,
        "raw_floor": cur_raw,
        "trusted_floor": cur_trusted,
        "raw_change": pct_raw,
        "trusted_change": pct_trusted,
        "order_book": order_book,
        "recent_sales": [] # Tạm tắt tính năng này cho DD373 vì logic khác
    }

@app.get("/history")
def get_history(item_name: str, hours: float = 24):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    norm_name = item_name.replace(' ', '').lower()
    # Xác định platform trước
    cursor.execute("SELECT platform FROM market_logs WHERE LOWER(REPLACE(item_name, ' ', '')) = ? ORDER BY timestamp DESC LIMIT 1", (norm_name,))
    p_row = cursor.fetchone()
    platform = p_row[0] if p_row else "g2g"

    time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%SZ")
    
    # Query gom nhóm theo timestamp
    query = f"""
        SELECT timestamp, 
               { 'MAX(price)' if platform == 'dd373' else 'MIN(price)' } as raw_floor,
               price -- dummy column
        FROM market_logs 
        WHERE LOWER(REPLACE(item_name, ' ', '')) = ? AND timestamp >= ?
        GROUP BY timestamp 
        ORDER BY timestamp ASC
    """
    cursor.execute(query, (norm_name, time_threshold))
    rows = cursor.fetchall()
    conn.close()
    
    chart_data = []
    for r in rows:
        ts_val = parse_db_time(r[0])
        if ts_val > 0:
            chart_data.append({
                "time": ts_val,
                "raw_floor": r[1],
                "trusted_floor": r[1] # DD373 không có trusted, dùng luôn raw
            })
    return {"history": chart_data}

@app.get("/items")
def get_items():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT item_name FROM market_logs WHERE item_name IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    return {"items": [r[0] for r in rows if r[0]]}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Server Backend v9.0 (G2G + DD373 Compatible)")
    uvicorn.run(app, host="0.0.0.0", port=8000)