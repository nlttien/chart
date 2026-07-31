import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import random
import re
from datetime import datetime
from curl_cffi import requests 

# === 1. CẤU HÌNH BẢO MẬT (COOKIE & TOKEN) ===
# (Hãy đảm bảo Cookie này còn mới)
MY_COOKIE = 'eldoradogg_currencyPreference=USD; cr-homepage-usp=1; p-checkout-test=1; cr-currency-aa=0; cr-homepage-aa=0; cr-top-up-aa=1; p-primer-update=1; curr-homepage-trending-games=1; cr-smaller-other-sellers-list=1; or-non-instant-redesign=1; p-c-badges=1; cr-top-up-swipeable=1; cr-homepage-popular-products=0; curr-offer-head-check=1; cr-tally-roblox-survey=1; it-product-aa=1; cr-topup-discount=0; p-billing-descriptor=0; it-abc=0; ac-gs-aa=1; cr-global-sec-button=0; cr-top-up-seller-reviews=0; pseudoId=14ea29d1-5f9d-42dd-bb2c-4d6b8aeb135f; cr-offer-sorting-v2=0; ac-score-p-g=1; cr-dark-theme=1; ac-more-like-v3=0; it-offer-listing-aa=0; ac-offer-listing-aa=1; ac-offer-p-aa=1; ac-price-mb=1; __Host-XSRF-TOKEN=d02a33864d608bcbfa8b55f5e9add2dd308fce976898937ffe8c4f8be751b098; eldoradogg_locale=en-US; rtkclickid-store=69870d56e7319caefb38eaee'

# Tự động lấy XSRF Token
xsrf_match = re.search(r'__Host-XSRF-TOKEN=([a-zA-Z0-9]+)', MY_COOKIE)
XSRF_TOKEN = xsrf_match.group(1) if xsrf_match else ""

HEADERS = {
    "authority": "www.eldorado.gg",
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8",
    "referer": "https://www.eldorado.gg/",
    "origin": "https://www.eldorado.gg",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "cookie": MY_COOKIE,
    "x-xsrf-token": XSRF_TOKEN
}

# === CẤU HÌNH HỆ THỐNG ===
CONFIG_FILE = "eldorado_config.json"
SERVER_URL = "http://localhost:8001/update_data" 
API_BASE = "https://www.eldorado.gg/api/predefinedOffers/augmentedGame/offers"
PAGE_SIZE = 150 

class SniperEngine:
    def __init__(self, log_callback, update_stats_callback):
        self.is_running = False
        self.log = log_callback
        self.update_stats = update_stats_callback

    def scan_single_item(self, item_config):
        try:
            name = item_config['name']
            keyword = item_config['keyword'].strip()
            
            game_id = str(item_config['service_id']) # Chuyển về string để so sánh
            server_name = item_config['brand_id']
            category = item_config['filter_attr']

            self.log(f"🔎 Đang quét: {name} | Sv: {server_name}...")
            
            # --- LOGIC TỰ ĐỘNG CHUYỂN ĐỔI POE 1 / POE 2 ---
            params = {
                'gameId': game_id,
                'category': category,
                'pageSize': str(PAGE_SIZE), 
                'offerSortingCriterion': 'Price'
            }

            if game_id == '2': # === CẤU HÌNH RIÊNG CHO POE 1 ===
                # PoE 1 yêu cầu Device là PC ở value0, Server ở value1
                params['tradeEnvironmentValue0'] = 'PC' 
                params['tradeEnvironmentValue1'] = server_name
                
                # Nếu từ khóa là Divine Orb, dùng ID chuẩn 0-1 để lọc chính xác hơn
                if 'divine' in keyword.lower():
                    params['offerAttributeIdsCsv'] = '0-1'
                elif 'mirror' in keyword.lower():
                    params['offerAttributeIdsCsv'] = '0-3'
                else:
                    params['offerAttributeIdsCsv'] = '0-0'
            
            else: # === CẤU HÌNH MẶC ĐỊNH (POE 2 & CÁC GAME KHÁC) ===
                params['tradeEnvironmentValue0'] = server_name
                
                if 'mirror' in keyword.lower():
                    params['offerAttributeIdsCsv'] = '0-3'
                else:
                    params['offerAttributeIdsCsv'] = '0-0'

            # -----------------------------------------------

            all_raw_results = []
            
            with requests.Session(impersonate="chrome120") as s:
                for i in range(1, 5): 
                    if not self.is_running: return None
                    
                    p = params.copy()
                    p['pageIndex'] = str(i)
                    
                    try:
                        resp = s.get(API_BASE, params=p, headers=HEADERS, timeout=15)
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            if 'results' in data and isinstance(data['results'], list):
                                current_items = data['results']
                                count_current = len(current_items)
                                all_raw_results.extend(current_items)
                                
                                # Logic thoát sớm nếu hết dữ liệu
                                if count_current == 0:
                                    break 
                            else:
                                break 
                        else:
                            if resp.status_code == 400: # Hết trang
                                break 
                            
                            self.log(f"⚠️ Lỗi HTTP {resp.status_code} tại trang {i}")
                            if resp.status_code in [401, 403]:
                                self.log("⛔ Cookie hết hạn/lỗi! Dừng item này.")
                                return []
                                
                    except Exception as err:
                        self.log(f"⚠️ Lỗi kết nối: {str(err)}")
                    
                    time.sleep(random.uniform(1.0, 2.0))

            # === LOGIC LỌC (FILTER) ===
            filtered_items = []
            min_price = 999999.0
            
            for item in all_raw_results:
                offer = item.get('offer')
                if not offer: continue

                attr_list = offer.get('offerAttributeIdValues', [])
                is_match = False
                
                if not keyword:
                    is_match = True
                else:
                    for attr in attr_list:
                        val = str(attr.get('value', ''))
                        if keyword.lower() == val.lower():
                            is_match = True
                            break
                
                if not is_match: continue

                try:
                    price_obj = offer.get('pricePerUnit', {})
                    final_price = float(price_obj.get('amount', 0))
                except:
                    final_price = 0.0
                
                stock = int(offer.get('quantity', 0))
                user = item.get('user', {})
                username = user.get('username', 'Unknown')
                sold_total = int(user.get('completedOrders', 0))

                delivery_time = offer.get('guaranteedDeliveryTime', 'Unknown')
                status_display = delivery_time
                if delivery_time == "Minute20":
                    status_display = "20 Phút"
                elif delivery_time == "Hour1":
                    status_display = "1 Giờ"
                
                if final_price > 0 and final_price < min_price:
                    min_price = final_price

                filtered_items.append({
                    "seller": username,
                    "unit_price": final_price,
                    "stock": stock,
                    "online": status_display,
                    "sold_total": sold_total
                })

            count = len(filtered_items)
            if count > 0:
                self.log(f"✅ {name}: Tổng {count} người bán. Min: ${min_price:.6f}")
                return filtered_items
            else:
                self.log(f"⚠️ {name}: Không tìm thấy ai bán '{keyword}'!")
                return []

        except Exception as e:
            self.log(f"❌ Exception: {str(e)}")
            return []

    def send_to_server(self, item_name, data):
        try:
            payload = {"item_name": item_name, "data": data}
            import requests as normal_requests 
            response = normal_requests.post(SERVER_URL, json=payload, timeout=5)
            if response.status_code == 200:
                self.log(f"   -> 📤 Đã gửi {len(data)} dòng về App.")
            else:
                self.log(f"   -> ⚠️ App Server lỗi: {response.status_code}")
        except:
            pass

    def run_scheduler(self, items, delay):
        if not XSRF_TOKEN:
            self.log("❌ LỖI: Không tìm thấy XSRF Token trong Cookie!")
            return

        self.is_running = True
        self.log("🚀 Bắt đầu chu trình quét Eldorado (Smart PoE 1&2)...")
        
        while self.is_running:
            active_items = [i for i in items if i.get('enabled', True)]
            
            if not active_items:
                self.log("⚠️ Chưa chọn item nào để quét!")
                self.is_running = False
                break

            for item in active_items:
                if not self.is_running: break
                
                results = self.scan_single_item(item)
                
                if results:
                    self.send_to_server(item['name'], results)
                
                time.sleep(random.uniform(2.0, 4.0))

            if not self.is_running: break
            
            last_run_str = datetime.now().strftime("%H:%M:%S")
            self.update_stats(last_run_str, "Waiting...")

            wait_s = int(delay)
            self.log(f"💤 Nghỉ {wait_s}s...")
            for i in range(wait_s, 0, -1):
                if not self.is_running: break
                self.update_stats(last_run_str, f"{i}s")
                time.sleep(1)

        self.log("🛑 Đã dừng hệ thống.")
        self.update_stats("--:--:--", "Stopped")

# === UI SECTION GIỮ NGUYÊN ===
class G2GSniperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Eldorado Sniper (Multi-Game Fixed)")
        self.root.geometry("1100x750")
        
        style = ttk.Style()
        style.theme_use('clam')

        self.items = self.load_config()
        self.engine = SniperEngine(self.log_msg, self.update_stats)

        # UI Layout
        left_panel = tk.Frame(root, width=300, bg="#f0f2f5")
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(left_panel, text="DANH SÁCH MỤC TIÊU", font=("Segoe UI", 12, "bold"), bg="#fbc02d", fg="black", pady=10).pack(fill=tk.X)
        self.listbox = tk.Listbox(left_panel, font=("Segoe UI", 10), height=30, bd=0, selectbackground="#fff9c4", selectforeground="black")
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        right_panel = tk.Frame(root, bg="white")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cfg_frame = tk.LabelFrame(right_panel, text="Cấu Hình Item (Eldorado)", font=("Segoe UI", 10, "bold"), bg="white", padx=10, pady=10)
        cfg_frame.pack(fill=tk.X)

        tk.Label(cfg_frame, text="Tên Gợi Nhớ:", bg="white").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_name = ttk.Entry(cfg_frame, width=30)
        self.entry_name.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Từ Khóa (Item Name):", bg="white", fg="#d32f2f").grid(row=0, column=2, sticky="w", padx=(15, 0))
        self.entry_keyword = ttk.Entry(cfg_frame, width=30)
        self.entry_keyword.grid(row=0, column=3, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Game ID (VD: 220):", bg="white").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_service = ttk.Entry(cfg_frame, width=30)
        self.entry_service.grid(row=2, column=1, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Server (VD: Fate of the Vaal):", bg="white").grid(row=2, column=2, sticky="w", padx=(15, 0))
        self.entry_brand = ttk.Entry(cfg_frame, width=30)
        self.entry_brand.grid(row=2, column=3, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Category (VD: Currency):", bg="white").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_filter = ttk.Entry(cfg_frame, width=90)
        self.entry_filter.grid(row=3, column=1, columnspan=3, sticky="w", padx=5)

        btn_row = tk.Frame(cfg_frame, bg="white")
        btn_row.grid(row=4, column=0, columnspan=4, sticky="ew", pady=10)
        self.var_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(btn_row, text="Kích Hoạt", variable=self.var_enabled, bg="white").pack(side=tk.LEFT)
        tk.Button(btn_row, text="💾 LƯU", command=self.save_item, bg="#4caf50", fg="white").pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_row, text="❌ Xóa", command=self.del_item, bg="#ffcdd2").pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_row, text="🧹 Mới", command=self.clear_form, bg="#eeeeee").pack(side=tk.RIGHT, padx=5)

        dash_frame = tk.Frame(right_panel, bg="#fffde7", pady=10, bd=1, relief="solid")
        dash_frame.pack(fill=tk.X, pady=15)
        tk.Label(dash_frame, text="Delay (s):", bg="#fffde7").pack(side=tk.LEFT, padx=10)
        self.spin_delay = tk.Spinbox(dash_frame, from_=10, to=3600, width=5, justify="center")
        self.spin_delay.pack(side=tk.LEFT)
        self.spin_delay.insert(0, "30")
        self.btn_start = tk.Button(dash_frame, text="▶️ BẮT ĐẦU QUÉT", command=self.toggle_scan, bg="#fbc02d", fg="black", font=("Segoe UI", 11, "bold"), width=20)
        self.btn_start.pack(side=tk.RIGHT, padx=20)
        self.lbl_countdown = tk.Label(dash_frame, text="--", font=("Arial", 14, "bold"), bg="#fffde7", fg="#d32f2f")
        self.lbl_countdown.pack(side=tk.RIGHT, padx=20)
        self.lbl_last = tk.Label(dash_frame, text="--:--:--", font=("Arial", 10, "bold"), bg="#fffde7")
        self.lbl_last.pack(side=tk.RIGHT, padx=10)

        tk.Label(right_panel, text="Log:", bg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(right_panel, height=15, state='disabled', bg="#212121", fg="#ffeb3b", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.refresh_list()

    def log_msg(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
    def update_stats(self, t, c):
        self.lbl_last.config(text=t); self.lbl_countdown.config(text=c)
    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.items, f, indent=4)
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for item in self.items:
            self.listbox.insert(tk.END, f"{'🟢' if item.get('enabled') else '⚪'} {item['name']}")
    def on_select(self, event):
        idx = self.listbox.curselection()
        if not idx: return
        d = self.items[idx[0]]
        self.entry_name.delete(0, tk.END); self.entry_name.insert(0, d['name'])
        self.entry_keyword.delete(0, tk.END); self.entry_keyword.insert(0, d['keyword'])
        self.entry_service.delete(0, tk.END); self.entry_service.insert(0, d['service_id'])
        self.entry_brand.delete(0, tk.END); self.entry_brand.insert(0, d['brand_id'])
        self.entry_filter.delete(0, tk.END); self.entry_filter.insert(0, d['filter_attr'])
        self.var_enabled.set(d.get('enabled', True))
    def clear_form(self):
        self.listbox.selection_clear(0, tk.END)
        for e in [self.entry_name, self.entry_keyword, self.entry_service, self.entry_brand, self.entry_filter]: e.delete(0, tk.END)
    def save_item(self):
        d = {
            "name": self.entry_name.get().strip(),
            "keyword": self.entry_keyword.get().strip(),
            "service_id": self.entry_service.get().strip(),
            "brand_id": self.entry_brand.get().strip(),
            "filter_attr": self.entry_filter.get().strip(),
            "enabled": self.var_enabled.get()
        }
        if not d["name"]: return
        idx = self.listbox.curselection()
        if idx: self.items[idx[0]] = d
        else: self.items.append(d)
        self.save_config(); self.refresh_list(); self.clear_form()
    def del_item(self):
        idx = self.listbox.curselection()
        if idx and messagebox.askyesno("Xóa", "Xóa mục này?"):
            del self.items[idx[0]]; self.save_config(); self.refresh_list(); self.clear_form()
    def toggle_scan(self):
        if not self.engine.is_running:
            t = threading.Thread(target=self.engine.run_scheduler, args=(self.items, int(self.spin_delay.get())))
            t.daemon = True; t.start()
            self.btn_start.config(text="⛔ DỪNG LẠI", bg="#d32f2f")
        else:
            self.engine.is_running = False
            self.btn_start.config(text="▶️ BẮT ĐẦU QUÉT", bg="#fbc02d")

if __name__ == "__main__":
    import sys
    root = tk.Tk()
    app = G2GSniperApp(root)
    if "--auto-start" in sys.argv:
        root.after(1500, app.toggle_scan)
    root.mainloop()