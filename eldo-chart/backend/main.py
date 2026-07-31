import sqlite3
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [ELDORADO] Đổi tên DB để tách biệt dữ liệu
DB_NAME = "eldorado_market.db"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    # Cấu trúc bảng giữ nguyên, cột 'online' sẽ lưu 'Delivery Time'
    c.execute('''CREATE TABLE IF NOT EXISTS market_logs
                 (timestamp TEXT, seller TEXT, price REAL, stock INTEGER, sold INTEGER, online TEXT, item_name TEXT)''')
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

# --- MODELS ---
class MarketItem(BaseModel):
    seller: str
    unit_price: float
    stock: int
    sold_total: int
    online: str # Trường này bên Client gửi lên là "20 Phút", "1 Giờ", v.v.

class UpdatePayload(BaseModel):
    item_name: str
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

def get_floor_prices(rows):
    """
    Logic mới:
    - raw_floor: Giá của seller có giá thấp nhất
    - trusted_floor: Giá của seller có stock cao nhất trong top 5 seller giá thấp nhất
    """
    if not rows:
        return 0, 0

    def safe_int(val):
        try:
            if val is None: return 0
            if isinstance(val, str):
                val = val.replace('.', '').replace(',', '')
            return int(float(val))
        except:
            return 0

    # Sắp xếp theo giá tăng dần -> Trùng giá thì ưu tiên stock cao lên trước
    sorted_rows = sorted(rows, key=lambda x: (
        x[1] if x[1] is not None else float('inf'), 
        -safe_int(x[2])
    ))
    
    raw = sorted_rows[0][1]
    
    # Lấy top 5 seller giá thấp nhất
    top_5 = sorted_rows[:5]
    
    # Tìm seller có stock cao nhất trong top 5
    highest_stock_seller = max(top_5, key=lambda x: safe_int(x[2]))
    
    trusted = highest_stock_seller[1]
    
    return raw, trusted

# --- API ENDPOINTS ---

@app.post("/update_data")
async def receive_data(payload: UpdatePayload):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    data_to_insert = [
        (timestamp, item.seller, item.unit_price, item.stock, item.sold_total, item.online, payload.item_name)
        for item in payload.data
    ]
    cursor.executemany("INSERT INTO market_logs VALUES (?, ?, ?, ?, ?, ?, ?)", data_to_insert)
    conn.commit()
    
    temp_rows = [(item.seller, item.unit_price, item.stock, item.sold_total, item.online) for item in payload.data]
    raw_floor, trusted_floor = get_floor_prices(temp_rows)
    
    conn.close()

    socket_msg = {
        "type": "UPDATE",
        "timestamp": timestamp,
        "item_name": payload.item_name,
        "raw_floor": raw_floor,
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

@app.get("/snapshot")
def get_snapshot(item_name: str, hours: float = 24):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Lấy dữ liệu mới nhất
    cursor.execute("SELECT MAX(timestamp) FROM market_logs WHERE item_name = ?", (item_name,))
    latest_ts_row = cursor.fetchone()
    
    if not latest_ts_row or not latest_ts_row[0]:
        conn.close()
        return {} 

    latest_ts = latest_ts_row[0]

    query_book = """
        SELECT seller, price, stock, sold, online 
        FROM market_logs 
        WHERE item_name = ? AND timestamp = ?
        ORDER BY price ASC
    """
    cursor.execute(query_book, (item_name, latest_ts))
    current_rows = cursor.fetchall()
    
    cur_raw, cur_trusted = get_floor_prices(current_rows)

    order_book = []
    for r in current_rows:
        order_book.append({
            "seller": r[0], "unit_price": r[1], "stock": r[2], 
            "sold_total": r[3], "online": r[4] # Delivery Time
        })

    # Lấy dữ liệu quá khứ
    time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%SZ")
    if not latest_ts.endswith('Z'):
        time_threshold = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT MIN(timestamp) FROM market_logs WHERE item_name = ? AND timestamp >= ?", (item_name, time_threshold))
    old_ts_row = cursor.fetchone()
    
    old_raw = cur_raw 
    old_trusted = cur_trusted

    if old_ts_row and old_ts_row[0]:
        old_ts = old_ts_row[0]
        cursor.execute(query_book, (item_name, old_ts))
        old_rows = cursor.fetchall()
        old_raw, old_trusted = get_floor_prices(old_rows)

    pct_raw = calculate_change(cur_raw, old_raw)
    pct_trusted = calculate_change(cur_trusted, old_trusted)

    # Tính Growth (Volume sold tăng thêm)
    query_growth = """
        SELECT seller, (MAX(sold) - MIN(sold)) as growth
        FROM market_logs
        WHERE item_name = ? AND timestamp >= ?
        GROUP BY seller
        HAVING growth > 0
        ORDER BY growth DESC
        LIMIT 50
    """
    cursor.execute(query_growth, (item_name, time_threshold))
    growth_rows = cursor.fetchall()
    conn.close()

    recent_sales = []
    for r in growth_rows:
        recent_sales.append({"seller": r[0], "amount": r[1], "time": "Recent"})

    return {
        "type": "SNAPSHOT",
        "timestamp": latest_ts,
        "item_name": item_name,
        "raw_floor": cur_raw,
        "trusted_floor": cur_trusted,
        "raw_change": pct_raw,
        "trusted_change": pct_trusted,
        "order_book": order_book,
        "recent_sales": recent_sales 
    }

@app.get("/history")
def get_history(item_name: str, hours: float = 24):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%SZ")
    fallback_threshold = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Lấy tất cả các bản ghi để nhóm và tìm giá của seller thứ 2 trong Python
    query = """
        SELECT timestamp, seller, price, stock, sold, online
        FROM market_logs 
        WHERE item_name = ? AND (timestamp >= ? OR timestamp >= ?)
        ORDER BY timestamp ASC, price ASC
    """
    cursor.execute(query, (item_name, time_threshold, fallback_threshold))
    rows = cursor.fetchall()
    conn.close()
    
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in rows:
        # r[0] là timestamp, r[1] là seller, r[2] là price, r[3] là stock, r[4] là sold, r[5] là online
        grouped[r[0]].append((r[1], r[2], r[3], r[4], r[5]))
        
    chart_data = []
    for ts in sorted(grouped.keys()):
        ts_val = parse_db_time(ts)
        if ts_val > 0:
            raw, trusted = get_floor_prices(grouped[ts])
            chart_data.append({
                "time": ts_val,
                "raw_floor": raw,
                "trusted_floor": trusted
            })
    return {"history": chart_data}

@app.get("/competitor_history")
def get_competitor_history(item_name: str, sellers: str, hours: float = 24):
    seller_list = sellers.split(',')
    if not seller_list: return {"data": {}}
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%SZ")
    fallback_threshold = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    placeholders = ','.join('?' for _ in seller_list)
    query = f"""
        SELECT timestamp, seller, price
        FROM market_logs 
        WHERE item_name = ? AND seller IN ({placeholders}) 
        AND (timestamp >= ? OR timestamp >= ?)
        ORDER BY timestamp ASC
    """
    args = [item_name] + seller_list + [time_threshold, fallback_threshold]
    cursor.execute(query, args)
    rows = cursor.fetchall()
    conn.close()
    
    result = {}
    for r in rows:
        seller = r[1]
        if seller not in result: result[seller] = []
        ts_val = parse_db_time(r[0])
        if ts_val > 0:
            result[seller].append({"time": ts_val, "value": r[2]})
        
    return {"data": result}

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
    print("🚀 Eldorado Backend v1.0 (Port 8001)")
    uvicorn.run(app, host="0.0.0.0", port=8001)