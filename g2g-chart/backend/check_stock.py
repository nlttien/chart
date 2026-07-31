import sqlite3

def check_db():
    conn = sqlite3.connect('g2g_market.db', timeout=10)
    c = conn.cursor()
    c.execute('SELECT MAX(timestamp) FROM market_logs')
    ts = c.fetchone()[0]
    
    if not ts:
        print("Khong co du lieu trong DB")
        return
        
    c.execute('SELECT seller, price, stock FROM market_logs WHERE timestamp=? ORDER BY price ASC', (ts,))
    rows = c.fetchall()
    
    print(f'Thoi gian cap nhat gan nhat: {ts}')
    print('\n--- TOP 10 SELLER GIA RE NHAT ---')
    for i, r in enumerate(rows[:10]):
        print(f"{i+1}. Seller: {r[0]} | Gia: {r[1]} | Stock: {r[2]}")
        
    top_6 = rows[:6]
    max_stock_seller = max(top_6, key=lambda x: int(x[2]) if x[2] is not None else 0)
    
    print('\n=> TRONG TOP 6 GIA RE NHAT:')
    print(f"Seller co stock khung nhat la: {max_stock_seller[0]}")
    print(f"So luong stock: {max_stock_seller[2]}")
    print(f"Muc gia: {max_stock_seller[1]}")

check_db()
