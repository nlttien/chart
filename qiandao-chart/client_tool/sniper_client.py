import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import json
import random
import os
import hashlib
import hmac
import base64
import sys
from datetime import datetime
from curl_cffi import requests as cffi_requests
import requests as normal_requests

# === CẤU HÌNH HỆ THỐNG ===
CONFIG_FILE = "qiandao_config.json"
LOCAL_SERVER_URL = "http://localhost:8003/update_data"
ONLINE_SERVER_URL = "https://qiandao.gegechart.xyz/update_data"

# === QIANDAO API SIGNATURE (ĐÃ BẺ KHÓA!) ===
SKEY = "2TJhRTpCpUIgnWl3qwIaoMMt3KhL2nkC"

def generate_sign(api_path, timestamp_ms):
    """Tạo chữ ký HMAC_SHA256 cho Qiandao API"""
    msg = api_path + str(timestamp_ms)
    hex_hash = hmac.new(SKEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    return base64.b64encode(hex_hash.encode('utf-8')).decode('utf-8')


class SniperEngine:
    def __init__(self, log_callback, update_stats_callback):
        self.is_running = False
        self.log = log_callback
        self.update_stats = update_stats_callback

    def scan_single_item(self, item_config):
        try:
            name = item_config.get('name', 'Unknown')
            jwt_token = item_config.get('jwt_token', '').strip()
            spu_id = item_config.get('spu_id', '836104794648117776').strip()
            spec_id = item_config.get('spec_id', '269603').strip()
            is_sell = item_config.get('is_sell', False)
            
            if not jwt_token:
                self.log(f"⚠️ {name}: JWT Token trống, bỏ qua.")
                return []
            
            self.log(f"   Dang quet: {name}...")
            
            if is_sell:
                api_path = "/c2c-web/v1/currency/spu-list-v2"
            else:
                api_path = "/c2c-web/v1/currency/buy-direction/spu-list-v2"
            api_url = "https://api.qiandao.com" + api_path
            timestamp = str(int(time.time() * 1000))
            sign = generate_sign(api_path, timestamp)
            
            headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': f'Bearer {jwt_token}',
                'origin': 'https://qiandao.com',
                'referer': 'https://qiandao.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
                'x-echo-region': 'CN',
                'x-request-package-id': '1044',
                'x-request-package-sign-version': '0.0.1',
                'x-request-sign': sign,
                'x-request-sign-type': 'HMAC_SHA256',
                'x-request-sign-version': 'v1',
                'x-request-timestamp': timestamp,
            }
            
            body = {
                "spuId": spu_id,
                "offset": 0,
                "limit": 30,
                "filters": [{
                    "key": "904221228984762040",
                    "keyType": "ATTRIBUTE",
                    "filterOperType": "EQ",
                    "isNot": False,
                    "selectedQueryValue": {
                        "candidateType": "SINGLE_VALUE",
                        "candidateValues": [{"label": "\u666e\u901a", "value": spec_id}]
                    }
                }],
                "sortBy": "BEST_RATIO"
            }
            
            resp = cffi_requests.post(api_url, headers=headers, 
                                      data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                      impersonate="chrome120", timeout=10)
            
            if resp.status_code == 200:
                resp_data = resp.json()
                
                api_code = resp_data.get('code')
                if str(api_code) not in ('0', '200'):
                    err = resp_data.get('errCode', 'Unknown')
                    msg_detail = resp_data.get('msg', '')
                    self.log(f"   {name}: API code={resp_data.get('code')}, err={err}, msg={msg_detail}")
                    if 'TOKEN' in str(err).upper() or 'AUTH' in str(err).upper() or 'EXPIRE' in str(err).upper():
                        self.log(f"   {name}: JWT Token het han! Hay dang nhap lai va copy token moi.")
                    return []
                
                data_obj = resp_data.get('data', {})
                if isinstance(data_obj, dict):
                    items = data_obj.get('items', data_obj.get('list', []))
                elif isinstance(data_obj, list):
                    items = data_obj
                else:
                    items = []
                
                if not items:
                    self.log(f"   {name}: Danh sach trong. resp={str(resp_data)[:300]}")
                    return []
                
                parsed_items = []
                for it in items:
                    seller_info = it.get('buyerInfo') or it.get('sellerInfo', {})
                    ratio_price = float(it.get('ratioPrice', 0))
                    rmb_price = float(it.get('rmbPrice', 0))
                    stock = int(it.get('stock', 0))
                    min_buy = int(it.get('minBuyCount', 0))
                    seller_name = seller_info.get('nickname', 'Unknown')
                    is_online = seller_info.get('isOnline', False)
                    credit = seller_info.get('creditPoint', {})
                    credit_score = int(float(credit.get('point', 0) or 0))
                    
                    parsed_items.append({
                        'seller': seller_name,
                        'unit_price': rmb_price,
                        'stock': stock,
                        'sold_total': credit_score,
                        'online': "Online" if is_online else "Offline",
                        'ratio': ratio_price,
                        'min_buy': min_buy
                    })
                
                # Do not sort, use the order from the API
                best = parsed_items[0]['ratio'] if parsed_items else 0
                self.log(f"   OK {name}: {len(parsed_items)} requests. Best ratio: 1Y={best}")
                return parsed_items
            else:
                try:
                    err_body = resp.json()
                    self.log(f"   {name}: HTTP {resp.status_code}, response: {err_body}")
                except:
                    self.log(f"   {name}: HTTP {resp.status_code}, body: {resp.text[:200]}")
                return []
        except Exception as e:
            self.log(f"   LOI ({item_config.get('name', '?')}): {str(e)}")
            return []

    def send_to_server(self, item_name, data):
        payload = {"source": "qiandao", "item_name": item_name, "platform": "qiandao", "data": data}
        try:
            r = normal_requests.post(LOCAL_SERVER_URL, json=payload, timeout=2)
            if r.status_code == 200:
                self.log(f"   -> Da dong bo len Dashboard")
            else:
                self.log(f"   -> LOI Server HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            self.log(f"   -> LOI Server: {str(e)}")

    def run_scheduler(self, items, delay):
        self.is_running = True
        self.log("BAT DAU quet Qiandao (Tu dong 100% - Direct API)...")
        while self.is_running:
            active_items = [i for i in items if i.get('enabled', True)]
            if not active_items:
                self.log("Khong co cau hinh nao duoc bat.")
                self.is_running = False; break

            for item in active_items:
                if not self.is_running: break
                results = self.scan_single_item(item)
                if results:
                    self.send_to_server(item['name'], results)
                time.sleep(random.uniform(2.0, 4.0))

            if not self.is_running: break
            
            wait_s = int(delay)
            self.log(f"Dang cho {wait_s}s...")
            for i in range(wait_s, 0, -1):
                if not self.is_running: break
                self.update_stats(datetime.now().strftime("%H:%M:%S"), f"{i}s")
                time.sleep(1)
        self.log("Da dung quet.")


class QiandaoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Qiandao Sniper (Auto 100% - Direct API)")
        self.root.geometry("1000x750")
        
        self.items = self.load_config()
        self.engine = SniperEngine(self.log_msg, self.update_stats)

        left_panel = tk.Frame(root, width=250, bg="#f0f2f5")
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox = tk.Listbox(left_panel, height=30)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        right_panel = tk.Frame(root, bg="white")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cfg_frame = tk.LabelFrame(right_panel, text="Cau Hinh Item", padx=10, pady=10)
        cfg_frame.pack(fill=tk.X)

        tk.Label(cfg_frame, text="Ten Item:").grid(row=0, column=0, sticky="w")
        self.entry_name = ttk.Entry(cfg_frame, width=30)
        self.entry_name.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(cfg_frame, text="JWT Token (Bearer):").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_jwt = ttk.Entry(cfg_frame, width=70)
        self.entry_jwt.grid(row=1, column=1, columnspan=2, sticky="w", padx=5)

        tk.Label(cfg_frame, text="SPU ID (Mac dinh PoE2 Divine):").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_spu = ttk.Entry(cfg_frame, width=30)
        self.entry_spu.grid(row=2, column=1, sticky="w", padx=5)
        self.entry_spu.insert(0, "836104794648117776")

        tk.Label(cfg_frame, text="Spec ID (269603=Thuong):").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_spec = ttk.Entry(cfg_frame, width=30)
        self.entry_spec.grid(row=3, column=1, sticky="w", padx=5)
        self.entry_spec.insert(0, "269603")

        btn_row = tk.Frame(cfg_frame)
        btn_row.grid(row=4, column=0, columnspan=3, pady=10)
        tk.Button(btn_row, text="LUU", command=self.save_item, bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="Xoa", command=self.del_item, bg="red", fg="white").pack(side=tk.LEFT)
        tk.Button(btn_row, text="Moi", command=self.clear_form).pack(side=tk.LEFT)

        dash_frame = tk.Frame(right_panel, bg="#ffebee", pady=10)
        dash_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(dash_frame, text="Delay (s):").pack(side=tk.LEFT, padx=10)
        self.spin_delay = tk.Spinbox(dash_frame, from_=5, to=3600, width=5)
        self.spin_delay.pack(side=tk.LEFT); self.spin_delay.insert(0, "30")

        self.btn_start = tk.Button(dash_frame, text="START", command=self.toggle_scan, bg="blue", fg="white")
        self.btn_start.pack(side=tk.RIGHT, padx=20)
        self.lbl_countdown = tk.Label(dash_frame, text="--", font=("Arial", 14), bg="#ffebee")
        self.lbl_countdown.pack(side=tk.RIGHT)

        self.log_text = scrolledtext.ScrolledText(right_panel, height=20, bg="black", fg="#ff4081")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.refresh_list()
        
        self.log_msg("=== Qiandao Sniper - Da be khoa chu ky HMAC! ===")
        self.log_msg("Chi can dan JWT Token va bam START la chay tu dong vinh vien!")
        self.log_msg("JWT Token het han sau ~3 ngay, ban chi can dang nhap lai web Qiandao va copy token moi.")

    def log_msg(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n"); self.log_text.see(tk.END)
    def update_stats(self, t, c): self.lbl_countdown.config(text=c)
    
    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.items, f, indent=4)
        
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for item in self.items: self.listbox.insert(tk.END, item.get('name', 'Unknown'))
    def on_select(self, event):
        idx = self.listbox.curselection()
        if not idx: return
        d = self.items[idx[0]]
        self.entry_name.delete(0, tk.END); self.entry_name.insert(0, d.get('name', ''))
        self.entry_jwt.delete(0, tk.END); self.entry_jwt.insert(0, d.get('jwt_token', ''))
        self.entry_spu.delete(0, tk.END); self.entry_spu.insert(0, d.get('spu_id', '836104794648117776'))
        self.entry_spec.delete(0, tk.END); self.entry_spec.insert(0, d.get('spec_id', '269603'))
    def save_item(self):
        d = {
            "name": self.entry_name.get(), 
            "jwt_token": self.entry_jwt.get(),
            "spu_id": self.entry_spu.get() or "836104794648117776",
            "spec_id": self.entry_spec.get() or "269603",
            "enabled": True
        }
        idx = self.listbox.curselection()
        if idx: self.items[idx[0]] = d
        else: self.items.append(d)
        self.save_config(); self.refresh_list()
    def del_item(self):
        idx = self.listbox.curselection()
        if idx: del self.items[idx[0]]; self.save_config(); self.refresh_list()
    def clear_form(self):
        self.entry_name.delete(0, tk.END)
        self.entry_jwt.delete(0, tk.END)
        self.entry_spu.delete(0, tk.END); self.entry_spu.insert(0, "836104794648117776")
        self.entry_spec.delete(0, tk.END); self.entry_spec.insert(0, "269603")
    def toggle_scan(self):
        if not self.engine.is_running:
            t = threading.Thread(target=self.engine.run_scheduler, args=(self.items, int(self.spin_delay.get())))
            t.daemon = True; t.start()
            self.btn_start.config(text="STOP", bg="red")
        else:
            self.engine.is_running = False
            self.btn_start.config(text="START", bg="blue")

if __name__ == "__main__":
    root = tk.Tk()
    app = QiandaoApp(root)
    if "--auto-start" in sys.argv:
        root.after(1500, app.toggle_scan)
    root.mainloop()
