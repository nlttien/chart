import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import random
from datetime import datetime
from curl_cffi import requests # Thư viện giả lập trình duyệt mạnh mẽ

# === CẤU HÌNH HỆ THỐNG ===
CONFIG_FILE = "sniper_config.json"
# [UPDATE] Đã đổi port từ 5000 -> 8002 để khớp với FastAPI
SERVER_URL = "http://localhost:8002/update_data" 
API_BASE = "https://sls.g2g.com/offer/search"

# Giữ nguyên Headers chuẩn [cite: 42]
HEADERS = {
    "authority": "sls.g2g.com",
    "accept": "application/json, text/plain, */*",
    "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://www.g2g.com",
    "referer": "https://www.g2g.com/",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# === CORE LOGIC (ENGINE) ===
class SniperEngine:
    def __init__(self, log_callback, update_stats_callback):
        self.is_running = False
        self.log = log_callback
        self.update_stats = update_stats_callback

    def scan_single_item(self, item_config):
        """Hàm quét 1 item cụ thể"""
        try:
            name = item_config['name']
            keyword = item_config['keyword'].strip().lower()
            
            self.log(f"🔎 Đang quét: {name} (Key: '{keyword}')...")
            
            params = {
                'service_id': item_config['service_id'],
                'brand_id': item_config['brand_id'],
                'filter_attr': item_config['filter_attr'],
                'sort': 'lowest_price',
                'page_size': '48',
                'group': '0',
                'currency': 'USD',
                'country': 'VN',
                'v': 'v2'
            }

            all_raw_results = []
            
            # Sử dụng curl_cffi để bypass anti-bot [cite: 46]
            with requests.Session(impersonate="chrome120") as s:
                for i in range(1, 4): # Quét 3 trang
                    if not self.is_running: return None
                    p = params.copy()
                    p['page'] = str(i)
                    try:
                        resp = s.get(API_BASE, params=p, headers=HEADERS, timeout=20)
                        if resp.status_code == 200:
                            data = resp.json()
                            if 'payload' in data and 'results' in data['payload']:
                                all_raw_results.extend(data['payload']['results'])
                            else:
                                break
                        else:
                            self.log(f"⚠️ HTTP {resp.status_code} tại trang {i}")
                    except Exception as err:
                        self.log(f"⚠️ Lỗi kết nối: {str(err)}")
                    time.sleep(random.uniform(1.0, 2.0))

            # Filter Logic
            filtered_items = []
            min_price = 999999.0
            
            for item in all_raw_results:
                title = (item.get('title') or "").lower()
                prod_name = (item.get('product_name') or "").lower()
                
                # Check keyword
                if keyword and (keyword not in title and keyword not in prod_name):
                    continue

                # Get Price
                final_price = item.get('converted_unit_price') or item.get('unit_price') or item.get('display_price')
                final_price = float(final_price) if final_price else 0.0

                # Get Sold
                sold = item.get('total_success_order', 0)
                if sold == 0: sold = item.get('total_completed_orders', 0)
                
                # Get Min Price (Online only)
                if item.get('is_online') and final_price > 0 and final_price < min_price:
                    min_price = final_price

                filtered_items.append({
                    "seller": item.get('username', 'Unknown'),
                    "unit_price": final_price,
                    "stock": int(item.get('available_qty', 0)),
                    "online": "Online" if item.get('is_online') else "Offline",
                    "sold_total": int(sold)
                })

            count = len(filtered_items)
            if count > 0:
                self.log(f"✅ {name}: Tìm thấy {count} sellers. Min: ${min_price:.4f}")
                return filtered_items
            else:
                self.log(f"⚠️ {name}: Không tìm thấy dữ liệu khớp '{keyword}'!")
                return []

        except Exception as e:
            self.log(f"❌ Exception ({item_config['name']}): {str(e)}")
            return []

    # --- HÀM GỬI DỮ LIỆU VỀ SERVER ---
    def send_to_server(self, item_name, data):
        try:
            payload = {"item_name": item_name, "data": data}
            # Dùng thư viện requests thường để gửi nội bộ (nhanh hơn curl_cffi cho localhost)
            import requests as normal_requests 
            
            response = normal_requests.post(SERVER_URL, json=payload, timeout=5)
            if response.status_code == 200:
                self.log(f"   -> 📤 Đã gửi thành công {len(data)} dòng về Server.")
            else:
                self.log(f"   -> ⚠️ Server trả về lỗi: {response.status_code}")
        except Exception as e:
            self.log(f"   -> ❌ Lỗi kết nối Server Python: {str(e)}")
            self.log("      (Hãy chắc chắn bạn đã chạy file main.py ở port 8002)")

    def run_scheduler(self, items, delay):
        self.is_running = True
        self.log("🚀 Bắt đầu chu trình quét...")
        
        while self.is_running:
            active_items = [i for i in items if i.get('enabled', True)]
            
            if not active_items:
                self.log("⚠️ Không có item nào được kích hoạt!")
                self.is_running = False
                break

            for item in active_items:
                if not self.is_running: break
                
                # 1. Quét lấy dữ liệu
                results = self.scan_single_item(item)
                
                # 2. GỬI VỀ SERVER
                if results:
                    self.send_to_server(item['name'], results)
                
                time.sleep(random.uniform(2.0, 4.0))

            if not self.is_running: break
            
            last_run_str = datetime.now().strftime("%H:%M:%S")
            self.update_stats(last_run_str, "Wait...")

            wait_s = int(delay)
            self.log(f"💤 Hoàn tất vòng quét. Nghỉ {wait_s}s...")
            for i in range(wait_s, 0, -1):
                if not self.is_running: break
                self.update_stats(last_run_str, f"{i}s")
                time.sleep(1)

        self.log("🛑 Đã dừng hệ thống.")
        self.update_stats("--:--:--", "Stopped")

# === UI SECTION ===
class G2GSniperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("G2G Multi-Currency Sniper (v7.0 WebSocket Ed.)")
        self.root.geometry("1100x750")
        
        style = ttk.Style()
        style.theme_use('clam')

        self.items = self.load_config()
        self.engine = SniperEngine(self.log_msg, self.update_stats)

        # UI LAYOUT
        left_panel = tk.Frame(root, width=300, bg="#f0f2f5")
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(left_panel, text="DANH SÁCH MỤC TIÊU", font=("Segoe UI", 12, "bold"), bg="#1a237e", fg="white", pady=10).pack(fill=tk.X)
        self.listbox = tk.Listbox(left_panel, font=("Segoe UI", 10), height=30, bd=0, selectbackground="#e8eaf6", selectforeground="black")
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        right_panel = tk.Frame(root, bg="white")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cfg_frame = tk.LabelFrame(right_panel, text="Cấu Hình Item", font=("Segoe UI", 10, "bold"), bg="white", padx=10, pady=10)
        cfg_frame.pack(fill=tk.X)

        tk.Label(cfg_frame, text="Tên Gợi Nhớ:", bg="white").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_name = ttk.Entry(cfg_frame, width=30)
        self.entry_name.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Từ Khóa:", bg="white", fg="#d32f2f").grid(row=0, column=2, sticky="w", padx=(15, 0))
        self.entry_keyword = ttk.Entry(cfg_frame, width=30)
        self.entry_keyword.grid(row=0, column=3, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Dán Link G2G:", bg="white", fg="#1976d2").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_url_import = ttk.Entry(cfg_frame, width=65)
        self.entry_url_import.grid(row=1, column=1, columnspan=2, sticky="w", padx=5)
        tk.Button(cfg_frame, text="⚡ Tự động điền ID", command=self.parse_g2g_url, bg="#1976d2", fg="white").grid(row=1, column=3, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Service ID:", bg="white").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_service = ttk.Entry(cfg_frame, width=30)
        self.entry_service.grid(row=2, column=1, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Brand ID:", bg="white").grid(row=2, column=2, sticky="w", padx=(15, 0))
        self.entry_brand = ttk.Entry(cfg_frame, width=30)
        self.entry_brand.grid(row=2, column=3, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Filter Attr:", bg="white").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_filter = ttk.Entry(cfg_frame, width=90)
        self.entry_filter.grid(row=3, column=1, columnspan=3, sticky="w", padx=5)

        btn_row = tk.Frame(cfg_frame, bg="white")
        btn_row.grid(row=4, column=0, columnspan=4, sticky="ew", pady=10)
        self.var_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(btn_row, text="Kích Hoạt", variable=self.var_enabled, bg="white").pack(side=tk.LEFT)
        tk.Button(btn_row, text="💾 LƯU", command=self.save_item, bg="#4caf50", fg="white").pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_row, text="❌ Xóa", command=self.del_item, bg="#ffcdd2").pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_row, text="🧹 Mới", command=self.clear_form, bg="#eeeeee").pack(side=tk.RIGHT, padx=5)

        dash_frame = tk.Frame(right_panel, bg="#e3f2fd", pady=10, bd=1, relief="solid")
        dash_frame.pack(fill=tk.X, pady=15)
        tk.Label(dash_frame, text="Delay (s):", bg="#e3f2fd").pack(side=tk.LEFT, padx=10)
        self.spin_delay = tk.Spinbox(dash_frame, from_=10, to=3600, width=5, justify="center")
        self.spin_delay.pack(side=tk.LEFT)
        self.spin_delay.insert(0, "30")
        self.btn_start = tk.Button(dash_frame, text="▶️ BẮT ĐẦU QUÉT", command=self.toggle_scan, bg="#2196f3", fg="white", font=("Segoe UI", 11, "bold"), width=20)
        self.btn_start.pack(side=tk.RIGHT, padx=20)
        self.lbl_countdown = tk.Label(dash_frame, text="--", font=("Arial", 14, "bold"), bg="#e3f2fd", fg="#d32f2f")
        self.lbl_countdown.pack(side=tk.RIGHT, padx=20)
        self.lbl_last = tk.Label(dash_frame, text="--:--:--", font=("Arial", 10, "bold"), bg="#e3f2fd")
        self.lbl_last.pack(side=tk.RIGHT, padx=10)

        tk.Label(right_panel, text="Log:", bg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(right_panel, height=15, state='disabled', bg="#263238", fg="#00e676", font=("Consolas", 9))
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
    def parse_g2g_url(self):
        url = self.entry_url_import.get().strip()
        if not url:
            messagebox.showwarning("Chú ý", "Vui lòng dán đường link G2G vào ô trước!")
            return
        import urllib.parse
        import re
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        fa = qs.get('fa', [''])[0]
        if not fa:
            messagebox.showerror("Lỗi", "Không tìm thấy tham số bộ lọc 'fa=' trong URL G2G này!")
            return
        m = re.search(r'lgc_(\d+)_', fa)
        brand_id = f"lgc_game_{m.group(1)}" if m else "lgc_game_19398"
        self.entry_service.delete(0, tk.END); self.entry_service.insert(0, "lgc_service_1")
        self.entry_brand.delete(0, tk.END); self.entry_brand.insert(0, brand_id)
        self.entry_filter.delete(0, tk.END); self.entry_filter.insert(0, fa)
        messagebox.showinfo("Thành công", f"Đã bóc tách tự động từ Link G2G:\n- Brand ID: {brand_id}\n- Filter Attr: {fa}")
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
            self.btn_start.config(text="▶️ BẮT ĐẦU QUÉT", bg="#2196f3")

if __name__ == "__main__":
    import sys
    root = tk.Tk()
    app = G2GSniperApp(root)
    if "--auto-start" in sys.argv:
        root.after(1500, app.toggle_scan)
    root.mainloop()