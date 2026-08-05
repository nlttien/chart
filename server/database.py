import sqlite3
import os
import re
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

    c.execute('''CREATE TABLE IF NOT EXISTS chart_history_summary
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  platform TEXT,
                  item_name TEXT,
                  min_price REAL,
                  avg_top5_price REAL,
                  avg_price REAL,
                  max_price REAL,
                  timestamp TEXT,
                  UNIQUE(platform, item_name, timestamp))''')

    c.execute('''CREATE INDEX IF NOT EXISTS idx_summary_platform_item_time 
                 ON chart_history_summary (platform, item_name, timestamp)''')

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

def cleanup_and_aggregate_old_logs(days: int = 3) -> Dict[str, Any]:
    """
    1. Trích xuất mốc giá min_price, avg_top5_price, avg_price theo từng giờ đối với log cũ hơn 'days' ngày.
    2. Lưu vào bảng chart_history_summary.
    3. Xóa các dòng gian hàng chi tiết cũ hơn 'days' ngày trong market_logs để tiết kiệm dung lượng đĩa.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%SZ")
        
        c.execute('''
            SELECT DISTINCT platform, item_name, strftime('%Y-%m-%d %H:00:00Z', timestamp) as hourly_ts
            FROM market_logs
            WHERE timestamp < ? AND price > 0
        ''', (cutoff_date,))
        
        old_groups = c.fetchall()
        summaries_inserted = 0
        
        for g in old_groups:
            plat, item, hourly_ts = g[0], g[1], g[2]
            
            c.execute('''
                SELECT price FROM market_logs
                WHERE platform = ? AND item_name = ? 
                  AND strftime('%Y-%m-%d %H:00:00Z', timestamp) = ?
                  AND price > 0
                ORDER BY price ASC
            ''', (plat, item, hourly_ts))
            
            prices = [r[0] for r in c.fetchall()]
            if not prices:
                continue
                
            min_p = prices[0]
            max_p = prices[-1]
            avg_p = sum(prices) / len(prices)
            
            top5_prices = prices[:5]
            avg_top5_p = sum(top5_prices) / len(top5_prices)
            
            c.execute('''
                INSERT OR REPLACE INTO chart_history_summary 
                (platform, item_name, min_price, avg_top5_price, avg_price, max_price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (plat, item, round(min_p, 4), round(avg_top5_p, 4), round(avg_p, 4), round(max_p, 4), hourly_ts))
            summaries_inserted += 1

        c.execute('DELETE FROM market_logs WHERE timestamp < ?', (cutoff_date,))
        deleted_rows = c.rowcount
        conn.commit()
        
        if deleted_rows > 0:
            logger.info(f"[DB Cleanup] Aggregated {summaries_inserted} hourly summaries and deleted {deleted_rows} detailed market log rows older than {days} days.")
        return {"deleted_rows": deleted_rows, "summaries_inserted": summaries_inserted}
    except Exception as e:
        logger.error(f"[DB Cleanup Error] {e}")
        return {"error": str(e)}
    finally:
        conn.close()

def get_lowest_prices(platform: Optional[str] = None, item_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy giá thấp nhất (Lowest/Floor Price) và giá trung bình Top 5 gian hàng thấp nhất từ đợt quét mới nhất"""
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
        
        # Thêm tính toán avg_top5_price
        result_rows = []
        for r in rows:
            plat = r['platform']
            iname = r['item_name']
            ts = r['timestamp']
            
            c.execute('''SELECT price FROM market_logs 
                         WHERE platform = ? AND item_name = ? AND timestamp = ? AND price > 0 
                         ORDER BY price ASC LIMIT 5''', (plat, iname, ts))
            top5_prices = [pr[0] for pr in c.fetchall()]
            avg_top5 = sum(top5_prices) / len(top5_prices) if top5_prices else r['lowest_price']
            
            row_dict = dict(r)
            row_dict['avg_top5_price'] = round(avg_top5, 4)
            result_rows.append(row_dict)
            
        return result_rows
    finally:
        conn.close()

def get_history_logs(platform: Optional[str] = None, item_name: Optional[str] = None, limit: int = 2000) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    try:
        results = []
        
        # 1. Lấy dữ liệu tổng hợp lịch sử (> 3 ngày) từ chart_history_summary
        summary_query = '''
            SELECT timestamp, platform, item_name, min_price as price, avg_top5_price, avg_price, 'Historical Summary' as seller
            FROM chart_history_summary
        '''
        sum_params = []
        if platform and item_name:
            summary_query += " WHERE platform = ? AND item_name = ?"
            sum_params.extend([platform.lower(), item_name])
        elif item_name:
            clean_kw = item_name.lower().replace("dd373", "").replace("qiandao", "").replace("eldorado", "").replace("g2g", "").replace("poe2", "poe 2").replace("poe1", "poe 1").strip()
            tokens = [t for t in re.split(r'[\s\_]+', clean_kw) if t]
            where_clauses = ["LOWER(item_name) LIKE ?"] * len(tokens)
            sum_params.extend([f"%{t}%" for t in tokens])
            summary_query += " WHERE " + " AND ".join(where_clauses)
            
        summary_query += " ORDER BY timestamp ASC LIMIT ?"
        sum_params.append(limit)
        
        c.execute(summary_query, sum_params)
        summary_rows = [dict(r) for r in c.fetchall()]
        results.extend(summary_rows)
        
        # 2. Lấy dữ liệu chi tiết trong 3 ngày gần đây từ market_logs
        raw_query = '''
            SELECT timestamp, platform, item_name, seller, price, stock, sold, online, min_qty, ratio, delivery
            FROM market_logs
        '''
        raw_params = []
        if platform and item_name:
            raw_query += " WHERE platform = ? AND item_name = ?"
            raw_params.extend([platform.lower(), item_name])
        elif item_name:
            clean_kw = item_name.lower().replace("dd373", "").replace("qiandao", "").replace("eldorado", "").replace("g2g", "").replace("poe2", "poe 2").replace("poe1", "poe 1").strip()
            tokens = [t for t in re.split(r'[\s\_]+', clean_kw) if t]
            where_clauses = ["LOWER(item_name) LIKE ?"] * len(tokens)
            raw_params.extend([f"%{t}%" for t in tokens])
            raw_query += " WHERE " + " AND ".join(where_clauses)
            
        raw_query += " ORDER BY timestamp ASC LIMIT ?"
        raw_params.append(limit)
        
        c.execute(raw_query, raw_params)
        raw_rows = [dict(r) for r in c.fetchall()]
        
        # Tính toán avg_top5_price theo từng đợt scan
        scans = {}
        for r in raw_rows:
            key = (r['platform'], r['item_name'], r['timestamp'])
            if key not in scans:
                scans[key] = []
            scans[key].append(r)
            
        for key, rows_list in scans.items():
            sorted_prices = sorted([x['price'] for x in rows_list if x['price'] > 0])
            top5 = sorted_prices[:5] if sorted_prices else [0.0]
            avg_top5 = sum(top5) / len(top5) if top5 else 0.0
            
            for item_dict in rows_list:
                item_dict['avg_top5_price'] = round(avg_top5, 4)
                results.append(item_dict)
                
        results.sort(key=lambda x: x.get('timestamp', ''))
        return results[:limit]
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
