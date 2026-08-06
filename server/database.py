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
        # Only keep top 10 lowest price listings per scan to keep DB lightweight
        sorted_records = sorted(
            records,
            key=lambda x: float(x.get("unit_price", x.get("price", 0.0))) if (x.get("unit_price") is not None or x.get("price") is not None) else 999999.0
        )
        top_10_records = sorted_records[:10]

        for item in top_10_records:
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

def get_latest_snapshot(platform: Optional[str] = None, item_name: Optional[str] = None, max_age_seconds: int = 86400 * 360) -> List[Dict[str, Any]]:
    """
    Lấy danh sách gian hàng từ duy nhất ĐỢT CÀO MỚI NHẤT (MAX timestamp).
    Lọc chính xác theo Tên Game và Loại Tiền (Divine / Chaos / Mirror).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        plat_lower = platform.lower() if platform else None

        where_clauses = []
        params = []

        if plat_lower:
            where_clauses.append("LOWER(platform) = ?")
            params.append(plat_lower)

        if item_name:
            sel_lower = item_name.lower()
            is_poe1 = "poe 1" in sel_lower or "poe1" in sel_lower
            is_poe2 = "poe 2" in sel_lower or "poe2" in sel_lower
            is_divine = "divine" in sel_lower or "div" in sel_lower
            is_chaos = "chaos" in sel_lower
            is_mirror = "mirror" in sel_lower

            if is_poe1:
                where_clauses.append("(LOWER(item_name) LIKE '%poe1%' OR LOWER(item_name) LIKE '%poe 1%')")
            elif is_poe2:
                where_clauses.append("(LOWER(item_name) LIKE '%poe2%' OR LOWER(item_name) LIKE '%poe 2%')")

            if is_divine:
                where_clauses.append("(LOWER(item_name) LIKE '%divine%' OR LOWER(item_name) LIKE '%div%')")
            elif is_chaos:
                where_clauses.append("LOWER(item_name) LIKE '%chaos%'")
            elif is_mirror:
                where_clauses.append("LOWER(item_name) LIKE '%mirror%'")

        where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        query = f'''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                     FROM market_logs 
                     {where_str} {"AND" if where_str else "WHERE"} timestamp = (
                         SELECT MAX(timestamp) FROM market_logs {where_str}
                     )
                     ORDER BY price ASC LIMIT 10'''
        
        c.execute(query, params + params)
        rows = [dict(row) for row in c.fetchall()]

        # Fallback if no exact MAX timestamp match
        if not rows:
            fallback_query = f'''SELECT timestamp, seller, price, stock, sold, online, item_name, min_qty, ratio, delivery 
                                FROM market_logs 
                                {where_str}
                                ORDER BY timestamp DESC, price ASC LIMIT 10'''
            c.execute(fallback_query, params)
            rows = [dict(row) for row in c.fetchall()]

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

def get_history_logs(platform: Optional[str] = None, item_name: Optional[str] = None, range_param: Optional[str] = '1d', limit: int = 5000) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    try:
        results = []
        
        # Calculate cutoff timestamp based on range_param
        cutoff_ts = None
        now_utc = datetime.now(timezone.utc)
        if range_param == '3h':
            cutoff_ts = (now_utc - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%SZ")
        elif range_param == '1d':
            cutoff_ts = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%SZ")
        elif range_param == '5d':
            cutoff_ts = (now_utc - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%SZ")
        elif range_param == '1m':
            cutoff_ts = (now_utc - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%SZ")
        elif range_param == '1y':
            cutoff_ts = (now_utc - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%SZ")

        # 1. Lấy dữ liệu tổng hợp lịch sử (> 3 ngày) từ chart_history_summary
        summary_query = '''
            SELECT timestamp, platform, item_name, min_price as price, avg_top5_price, avg_price, 'Historical Summary' as seller
            FROM chart_history_summary
        '''
        where_clauses = []
        sum_params = []
        if platform:
            where_clauses.append("platform = ?")
            sum_params.append(platform.lower())
        if item_name:
            sel_lower = item_name.lower()
            is_poe1 = "poe 1" in sel_lower or "poe1" in sel_lower
            is_poe2 = "poe 2" in sel_lower or "poe2" in sel_lower
            is_divine = "divine" in sel_lower or "div" in sel_lower
            is_chaos = "chaos" in sel_lower
            is_mirror = "mirror" in sel_lower

            if is_poe1:
                where_clauses.append("(LOWER(item_name) LIKE '%poe1%' OR LOWER(item_name) LIKE '%poe 1%')")
            elif is_poe2:
                where_clauses.append("(LOWER(item_name) LIKE '%poe2%' OR LOWER(item_name) LIKE '%poe 2%')")

            if is_divine:
                where_clauses.append("(LOWER(item_name) LIKE '%divine%' OR LOWER(item_name) LIKE '%div%')")
            elif is_chaos:
                where_clauses.append("LOWER(item_name) LIKE '%chaos%'")
            elif is_mirror:
                where_clauses.append("LOWER(item_name) LIKE '%mirror%'")

        if cutoff_ts:
            where_clauses.append("timestamp >= ?")
            sum_params.append(cutoff_ts)

        if where_clauses:
            summary_query += " WHERE " + " AND ".join(where_clauses)
            
        summary_query += " ORDER BY timestamp ASC LIMIT ?"
        sum_params.append(limit)
        
        c.execute(summary_query, sum_params)
        summary_rows = [dict(r) for r in c.fetchall()]
        results.extend(summary_rows)
        
        # 2. Lấy dữ liệu chi tiết trong market_logs
        raw_query = '''
            SELECT timestamp, platform, item_name, seller, price, stock, sold, online, min_qty, ratio, delivery
            FROM market_logs
        '''
        raw_where = []
        raw_params = []
        if platform:
            raw_where.append("platform = ?")
            raw_params.append(platform.lower())
        if item_name:
            sel_lower = item_name.lower()
            is_poe1 = "poe 1" in sel_lower or "poe1" in sel_lower
            is_poe2 = "poe 2" in sel_lower or "poe2" in sel_lower
            is_divine = "divine" in sel_lower or "div" in sel_lower
            is_chaos = "chaos" in sel_lower
            is_mirror = "mirror" in sel_lower

            if is_poe1:
                raw_where.append("(LOWER(item_name) LIKE '%poe1%' OR LOWER(item_name) LIKE '%poe 1%')")
            elif is_poe2:
                raw_where.append("(LOWER(item_name) LIKE '%poe2%' OR LOWER(item_name) LIKE '%poe 2%')")

            if is_divine:
                raw_where.append("(LOWER(item_name) LIKE '%divine%' OR LOWER(item_name) LIKE '%div%')")
            elif is_chaos:
                raw_where.append("LOWER(item_name) LIKE '%chaos%'")
            elif is_mirror:
                raw_where.append("LOWER(item_name) LIKE '%mirror%'")

        if cutoff_ts:
            raw_where.append("timestamp >= ?")
            raw_params.append(cutoff_ts)

        if raw_where:
            raw_query += " WHERE " + " AND ".join(raw_where)
            
        raw_query += " ORDER BY timestamp ASC LIMIT ?"
        raw_params.append(limit)
        
        c.execute(raw_query, raw_params)
        raw_rows = [dict(r) for r in c.fetchall()]
        
        # Aggregate each scan batch into ONE lightweight history point (min_price & avg_top5_price)
        scans = {}
        for r in raw_rows:
            key = (r['platform'], r['item_name'], r['timestamp'])
            if key not in scans:
                scans[key] = []
            scans[key].append(r['price'])
            
        for (plat, iname, ts), prices in scans.items():
            valid_prices = sorted([p for p in prices if p > 0])
            if not valid_prices:
                continue
            min_price = valid_prices[0]
            top5 = valid_prices[:5]
            avg_top5 = sum(top5) / len(top5)
            
            results.append({
                "timestamp": ts,
                "platform": plat,
                "item_name": iname,
                "price": round(min_price, 4),
                "lowest_price": round(min_price, 4),
                "avg_top5_price": round(avg_top5, 4)
            })
            
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
