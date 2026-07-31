import sqlite3
import json

conn = sqlite3.connect('qiandao-chart/backend/qiandao_market.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM market_logs WHERE item_name = 'poe2 div (Sell)' ORDER BY timestamp DESC LIMIT 10;")
rows = cursor.fetchall()
print(json.dumps(rows, indent=2, ensure_ascii=True))
conn.close()
