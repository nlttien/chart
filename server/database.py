import sqlite3
import os
import logging
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
                       item.get("seller", "Unknown"),
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

def get_latest_snapshot(platform: Optional[str] = None, item_name: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    try:
        if platform and item_name:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE platform = ? AND item_name = ? 
                         ORDER BY id DESC LIMIT 100''', (platform, item_name))
        elif item_name:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE item_name = ? 
                         ORDER BY id DESC LIMIT 100''', (item_name,))
        elif platform:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         WHERE platform = ? 
                         ORDER BY id DESC LIMIT 500''', (platform,))
        else:
            c.execute('''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                         FROM market_logs 
                         ORDER BY id DESC LIMIT 500''')
            
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
