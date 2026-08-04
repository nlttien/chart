import sqlite3
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chart_db")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "unified_market.db")

def get_connection(db_file: str = DB_PATH):
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    conn = sqlite3.connect(db_file, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_file: str = DB_PATH):
    conn = get_connection(db_file)
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    
    c.execute('''CREATE TABLE IF NOT EXISTS market_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, 
                  platform TEXT DEFAULT 'g2g',
                  seller TEXT, 
                  price REAL, 
                  stock INTEGER, 
                  sold INTEGER DEFAULT 0, 
                  online TEXT DEFAULT '', 
                  item_name TEXT,
                  min_qty INTEGER DEFAULT 0,
                  ratio TEXT DEFAULT '',
                  delivery TEXT DEFAULT '')''')
                  
    c.execute('''CREATE INDEX IF NOT EXISTS idx_logs_platform_item_time 
                 ON market_logs (platform, item_name, timestamp)''')

    c.execute('''CREATE TABLE IF NOT EXISTS monitored_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  platform TEXT,
                  name TEXT,
                  keyword TEXT DEFAULT '',
                  service_id TEXT DEFAULT '',
                  brand_id TEXT DEFAULT '',
                  filter_attr TEXT DEFAULT '',
                  url TEXT DEFAULT '',
                  jwt_token TEXT DEFAULT '',
                  spu_id TEXT DEFAULT '',
                  spec_id TEXT DEFAULT '',
                  is_sell INTEGER DEFAULT 0,
                  enabled INTEGER DEFAULT 1)''')

    c.execute('''CREATE TABLE IF NOT EXISTS system_config
                 (key TEXT PRIMARY KEY,
                  value TEXT,
                  updated_at TEXT)''')

    # Dọn dẹp dữ liệu cũ bị gán Unknown seller nếu có
    try:
        c.execute("UPDATE market_logs SET seller = 'G2G Trader' WHERE platform = 'g2g' AND (seller IS NULL OR seller = 'Unknown')")
        c.execute("UPDATE market_logs SET seller = 'Eldorado Trader' WHERE platform = 'eldorado' AND (seller IS NULL OR seller = 'Unknown')")
        c.execute("UPDATE market_logs SET seller = 'Qiandao Merchant' WHERE platform = 'qiandao' AND (seller IS NULL OR seller = 'Unknown')")
        c.execute("UPDATE market_logs SET seller = 'DD373 Trader' WHERE platform = 'dd373' AND (seller IS NULL OR seller = 'Unknown')")
    except Exception as e:
        logger.warning(f"Cleanup legacy Unknown seller error: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {db_file}")

init_db()

def save_market_batch(platform: str, item_name: str, records: List[Dict[str, Any]], timestamp: str):
    conn = get_connection()
    c = conn.cursor()
    try:
        for item in records:
            c.execute('''INSERT INTO market_logs 
                         (timestamp, platform, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (timestamp,
                       platform,
                       item.get("seller", "Seller"),
                       float(item.get("unit_price", item.get("price", 0.0))),
                       int(item.get("stock", 0)),
                       int(item.get("sold_total", item.get("sold", 0))),
                       str(item.get("online", "")),
                       item_name,
                       int(item.get("min_qty", 0)),
                       str(item.get("ratio", "")),
                       str(item.get("delivery", ""))))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving market batch for {platform} - {item_name}: {e}")
    finally:
        conn.close()

def get_latest_snapshot(platform: Optional[str] = None, item_name: Optional[str] = None, max_age_seconds: int = 900) -> List[Dict[str, Any]]:
    """
    Lấy danh sách gian hàng từ duy nhất ĐỢT CÀO MỚI NHẤT (MAX timestamp).
    Bỏ qua nếu dữ liệu đã cũ quá max_age_seconds (mặc định 15 phút).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        if platform and item_name:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE platform = ? AND item_name = ? AND timestamp = (
                             SELECT MAX(timestamp) FROM market_logs WHERE platform = ? AND item_name = ?
                         )
                         ORDER BY price ASC''', (platform, item_name, platform, item_name))
        elif item_name:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE item_name = ? AND timestamp = (
                             SELECT MAX(timestamp) FROM market_logs WHERE item_name = ?
                         )
                         ORDER BY price ASC''', (item_name, item_name))
        elif platform:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE platform = ? AND (item_name, timestamp) IN (
                             SELECT item_name, MAX(timestamp) FROM market_logs WHERE platform = ? GROUP BY item_name
                         )
                         ORDER BY item_name ASC, price ASC''', (platform, platform))
        else:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE (platform, item_name, timestamp) IN (
                             SELECT platform, item_name, MAX(timestamp) FROM market_logs GROUP BY platform, item_name
                         )
                         ORDER BY platform ASC, item_name ASC, price ASC''')
            
        rows = [dict(row) for row in c.fetchall()]
        
        # Verify freshness: if latest timestamp is older than max_age_seconds, return empty list
        if rows:
            latest_ts_str = rows[0].get("timestamp", "")
            try:
                # Parse timestamp "YYYY-MM-DD HH:MM:SZ"
                dt = datetime.strptime(latest_ts_str.replace("Z", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - dt).total_seconds()
                if age > max_age_seconds:
                    return []
            except Exception:
                pass

        return rows
    finally:
        conn.close()

def get_lowest_prices(platform: Optional[str] = None, item_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy giá thấp nhất (Lowest/Floor Price) từ ĐỢT QUÉT MỚI NHẤT của mỗi item"""
    conn = get_connection()
    c = conn.cursor()
    try:
        query = '''
            WITH LatestScans AS (
                SELECT platform, item_name, MAX(timestamp) as latest_time
                FROM market_logs
                GROUP BY platform, item_name
            )
            SELECT m.platform, m.item_name, m.seller, MIN(m.price) as lowest_price, 
                   m.stock, m.sold, m.online, m.min_qty, m.delivery, m.timestamp
            FROM market_logs m
            INNER JOIN LatestScans ls 
               ON m.platform = ls.platform 
              AND m.item_name = ls.item_name 
              AND m.timestamp = ls.latest_time
            WHERE m.price > 0
        '''
        params = []
        if platform:
            query += " AND m.platform = ?"
            params.append(platform.lower())
        if item_name:
            query += " AND m.item_name = ?"
            params.append(item_name)
            
        query += " GROUP BY m.platform, m.item_name ORDER BY lowest_price ASC"
        
        c.execute(query, params)
        rows = [dict(row) for row in c.fetchall()]
        return rows
    finally:
        conn.close()

def get_history_logs(platform: Optional[str] = None, item_name: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    try:
        if platform and item_name:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE platform = ? AND item_name = ? 
                         ORDER BY timestamp ASC LIMIT ?''', (platform, item_name, limit))
        elif item_name:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE item_name = ? 
                         ORDER BY timestamp ASC LIMIT ?''', (item_name, limit))
        else:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         ORDER BY timestamp ASC LIMIT ?''', (limit,))
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()

def get_competitor_history_logs(platform: Optional[str], item_name: str, seller_list: List[str], hours: float = 24) -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    try:
        time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%SZ")
        placeholders = ','.join('?' for _ in seller_list)
        
        query = f'''
            SELECT timestamp, seller, price
            FROM market_logs 
            WHERE item_name = ? AND seller IN ({placeholders}) 
        '''
        params = [item_name] + seller_list
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        query += " AND timestamp >= ? ORDER BY timestamp ASC"
        params.append(time_threshold)
        
        c.execute(query, params)
        rows = c.fetchall()
        
        result = {}
        for r in rows:
            seller = r[1]
            if seller not in result:
                result[seller] = []
            result[seller].append({"timestamp": r[0], "price": r[2]})
        return result
    finally:
        conn.close()

def get_distinct_items(platform: Optional[str] = None) -> List[str]:
    conn = get_connection()
    c = conn.cursor()
    try:
        if platform:
            c.execute('SELECT DISTINCT item_name FROM market_logs WHERE platform = ?', (platform,))
        else:
            c.execute('SELECT DISTINCT item_name FROM market_logs')
        return [row[0] for row in c.fetchall() if row[0]]
    finally:
        conn.close()
