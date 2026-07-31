import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import random
import re
from datetime import datetime
from curl_cffi import requests  # Cần cài: pip install curl_cffi beautifulsoup4
from bs4 import BeautifulSoup

# === CẤU HÌNH HỆ THỐNG ===
CONFIG_FILE = "dd373_recycle_config.json"
LOCAL_SERVER_URL = "http://localhost:8000/update_data"
ONLINE_SERVER_URL = "https://dd373.gegechart.xyz/update_data"

# Headers giả lập trình duyệt để tránh bị chặn
DEFAULT_COOKIE = "clientId=a6676ef252c56a2a9f60c09998c13f82; dpushPC=true; Hm_lvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783669374; HMACCOUNT=2067EC5DCB8D2AE5; firstOpen_cc=true; imagestylewebp=1; headhistorySelectGame=%5B%7B%22Id%22%3A%2246e6971b94044ae3881dfaeb6993abb8%22%7D%5D; AutoSelectHistory=false; _c_WBKFRo=SdND9MOoObdOOBEaFuBUAF0wcGGE0fnmhEUbzpiZ; _nb_ioWEgULi=; acw_tc=6b9b3e2017836767239266076e72366b0fe422b914da8e36d261d7d316; cdn_sec_tc=6b9b3e2017836767239266076e72366b0fe422b914da8e36d261d7d316; acw_sc__v3=6a50bf378bc4cef54169f278582099aa5bca4c7c; Hm_lpvt_b1609ca2c0a77d0130ec3cf8396eb4d5=1783676689"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
    "Sec-Ch-Ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.dd373.com/s-3hcpqw-bwgvrk-fj6p5a-0-0-0-8rknmp-0-0-receive-0-0-1-0-0-0.html",
    "Cookie": DEFAULT_COOKIE
}

# === CORE LOGIC (ENGINE MÔ PHỎNG EXTENSION V2) ===
class SniperEngine:
    def __init__(self, log_callback, update_stats_callback):
        self.is_running = False
        self.log = log_callback
        self.update_stats = update_stats_callback

    def parse_number(self, text):
        """Lọc số từ chuỗi text rác"""
        if not text: return 0.0
        # Tìm số thực hoặc số nguyên (VD: 0.6757 hoặc 666)
        matches = re.findall(r"(\d+\.?\d*)", text)
        return float(matches[0]) if matches else 0.0

    def get_browser_page(self):
        """Khởi tạo trình duyệt tự động DrissionPage vượt Aliyun WAF"""
        if hasattr(self, '_dp_page') and self._dp_page:
            return self._dp_page
        try:
            from DrissionPage import ChromiumOptions, ChromiumPage
            co = ChromiumOptions()
            co.set_argument('--silent-debugger-extension-api') # Giấu thanh cảnh báo Debugger của Extension
            co.auto_port()
            
            # Tải trực tiếp Extension Auto Slider vào trình duyệt tự động
            import os
            ext_path = r"c:\Users\dung\Desktop\chart\aliyun-slider-ext"
            if os.path.exists(ext_path):
                co.add_extension(ext_path)
                
            self._dp_page = ChromiumPage(co)
            return self._dp_page
        except Exception as e:
            self.log(f"   ⚠️ Không thể mở ChromiumPage: {e}")
            return None

    def auto_solve_slider(self, page):
        """Tự động phát hiện và trượt nút xác minh Aliyun WAF bằng thao tác giả lập người thật (Human-like Random Drag)"""
        try:
            selectors = [
                '#aliyunCaptcha-sliding-slider',
                '#nc_1_n1z',
                '.nc_iconfont.btn_slide',
                'span[id*="sliding"]',
                '.btn_slide',
                'div[class*="sliding"] span'
            ]
            
            slider_btn = None
            for sel in selectors:
                try:
                    btn = page.ele(sel, timeout=1)
                    if btn:
                        slider_btn = btn; break
                except Exception: pass

            if not slider_btn:
                try:
                    frames = page.get_frames()
                    for frame in frames:
                        for sel in selectors:
                            try:
                                btn = frame.ele(sel, timeout=1)
                                if btn:
                                    slider_btn = btn; break
                            except Exception: pass
                        if slider_btn: break
                except Exception: pass

            if slider_btn:
                self.log("   🤖 Phát hiện nút trượt WAF! Đang giả lập kéo tay người thật (Human-like Random Speed)...")
                
                rect = slider_btn.rect
                start_x = rect.location[0] + random.randint(5, 12)
                start_y = rect.location[1] + random.randint(5, 12)
                
                # Tổng quãng đường kéo ngẫu nhiên (340px - 380px)
                target_distance = random.randint(345, 375)
                
                # Bắt đầu giữ nút
                actions = page.actions
                actions.move_to((start_x, start_y)).hold()
                time.sleep(random.uniform(0.1, 0.3))

                # Giả lập gia tốc kéo của tay người (Tăng tốc nhanh đầu -> Giảm tốc nhẹ cuối)
                curr_x = start_x
                curr_y = start_y
                steps = random.randint(15, 25)
                
                for i in range(steps):
                    # Tỷ lệ tiến trình
                    progress = (i + 1) / steps
                    # Hàm gia tốc phi tuyến tính (Easing Out)
                    step_ratio = 1 - (1 - progress) ** 3
                    
                    next_x = start_x + int(target_distance * step_ratio)
                    # Thêm độ rung nhẹ trục Y (tự nhiên như tay người rung nhẹ ±1px đến 2px)
                    next_y = start_y + random.choice([-1, 0, 1, 2, -1, 0])
                    
                    dx = next_x - curr_x
                    dy = next_y - curr_y
                    
                    actions.move(offset_x=dx, offset_y=dy, duration=random.uniform(0.015, 0.045))
                    curr_x, curr_y = next_x, next_y

                # Thao tác thả nút ngẫu nhiên nhẹ
                time.sleep(random.uniform(0.15, 0.35))
                actions.release()
                
                time.sleep(2.5)
                return True
        except Exception as e:
            self.log(f"   ⚠️ Lỗi tự động trượt nút: {e}")
        return False

    def scan_single_item(self, item_config):
        """Quét trang Recycle của DD373 (Tự động vượt WAF Aliyun bằng DrissionPage)"""
        try:
            name = item_config['name']
            url = item_config['url'].strip()
            
            self.log(f"🔎 Đang quét: {name}...")

            # Lấy cookie và user-agent tùy chỉnh từ item nếu có
            custom_cookie = item_config.get('cookie', '').strip() or DEFAULT_COOKIE
            custom_ua = item_config.get('user_agent', '').strip() or DEFAULT_USER_AGENT
            
            clean_headers = {
                "Cookie": custom_cookie,
                "User-Agent": custom_ua,
                "Referer": "https://www.dd373.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,vi;q=0.8,en;q=0.7"
            }

            resp_text = ""
            status_code = 0

            # Lần 1: Dùng curl_cffi giả lập Chrome 120
            try:
                with requests.Session(impersonate="chrome120") as s:
                    resp = s.get(url, headers=clean_headers, timeout=15)
                    status_code = resp.status_code
                    resp_text = resp.text
            except Exception:
                pass

            # Lần 2: Nếu bị WAF Aliyun chặn hoặc lỗi HTTP, dùng chuẩn HTTP/1.1 (urllib)
            if status_code != 200 or "aliyunCaptcha" in resp_text or "WAF_NC_H5_WRAPPER" in resp_text:
                try:
                    import urllib.request
                    req = urllib.request.Request(url, headers=clean_headers)
                    with urllib.request.urlopen(req, timeout=15) as r:
                        status_code = r.getcode()
                        resp_text = r.read().decode('utf-8', errors='ignore')
                except Exception:
                    pass

            # Update logic for DD373 SSR HTML Structure
            soup = BeautifulSoup(resp_text, 'lxml') if resp_text else None
            
            def is_valid_row(tag):
                if tag.name not in ['div', 'li', 'ul']: return False
                text = tag.get_text()
                if '元/个' not in text and '1元=' not in text: return False
                for child in tag.find_all(['div', 'li', 'ul']):
                    child_text = child.get_text()
                    if '元/个' in child_text or '1元=' in child_text:
                        return False
                return True

            inner_items = soup.find_all(is_valid_row) if soup else []
            rows = []
            for item in inner_items:
                row = item
                while row.parent:
                    count_in_parent = len([i for i in inner_items if i in row.parent.descendants or i == row.parent])
                    count_in_row = len([i for i in inner_items if i in row.descendants or i == row])
                    if count_in_parent > count_in_row:
                        break
                    row = row.parent
                if row not in rows:
                    rows.append(row)

            # Lần 3: TỰ ĐỘNG HÓA TRÌNH DUYỆT (DRISSIONPAGE) NẾU BỊ ALIYUN WAF CHẶN HOUC HẾT HẠN COOKIE
            if status_code != 200 or "aliyunCaptcha" in resp_text or not rows:
                self.log("   🛡️ Không thấy row -> Tự động kích hoạt trình duyệt thật (DrissionPage)...")
                try:
                    page = self.get_browser_page()
                    if page:
                        page.get(url)
                        time.sleep(2)
                        
                        # Tự động trượt CAPTCHA nếu xuất hiện
                        self.auto_solve_slider(page)

                        # Đợi tối đa 60s để giải Captcha (nếu có)
                        self.log("   ⏳ Đang chờ xác thực Captcha (Thử tự động giải hoặc bạn có thể kéo bằng tay)...")
                        for i in range(60):
                            time.sleep(1) # RẤT QUAN TRỌNG ĐỂ CHỜ TRANG TẢI
                            try:
                                resp_text = page.html
                                title = page.title
                            except Exception:
                                resp_text = ""
                                title = ""
                                
                            if title and "Verification" not in title and "验证" not in title and "aliyunCaptcha" not in resp_text:
                                break
                            
                            # Thử tự động kéo thanh trượt Aliyun (bản mới và cũ)
                            if i % 2 == 0:
                                try:
                                    # Nếu bị lỗi chữ đỏ, click tải lại Captcha
                                    refresh_btn = page.ele('.aliyunCaptcha-sliding-refresh', timeout=0.1) or page.ele('t:a@href:reset', timeout=0.1)
                                    if refresh_btn and refresh_btn.is_displayed:
                                        self.log("   🔄 Thanh trượt báo lỗi, đang tải lại Captcha...")
                                        refresh_btn.click()
                                        time.sleep(1)
                                        
                                    if self.auto_solve_slider(page):
                                        time.sleep(1.5)
                                    elif i % 4 == 0:
                                        # Kích hoạt Computer Vision nhận diện ảnh trên màn hình làm phương án dự phòng!
                                        self._auto_slide_visual()
                                except Exception as e:
                                    pass
                        
                        status_code = 200

                        # Tự động trích xuất cookie mới nhất sau khi vượt WAF
                        try:
                            cookies_list = page.cookies()
                            cookies_dict = {}
                            if isinstance(cookies_list, dict):
                                cookies_dict = cookies_list
                            elif isinstance(cookies_list, list):
                                cookies_dict = {c.get('name', ''): c.get('value', '') for c in cookies_list if isinstance(c, dict) and c.get('name')}
                        except TypeError:
                            cookies_dict = {}

                        if cookies_dict:
                            new_cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
                            self.log("   ✅ Đã tự động gia hạn & vượt WAF thành công!")
                            item_config['cookie'] = new_cookie_str

                        # Phân tích lại HTML mới từ trình duyệt thật
                        soup = BeautifulSoup(resp_text, 'lxml')
                        try:
                            with open('c:/Users/dung/Desktop/chart/dd373_success.html', 'w', encoding='utf-8') as f:
                                f.write(resp_text)
                        except: pass
                        
                        inner_items = soup.find_all(is_valid_row)
                        rows = []
                        for item in inner_items:
                            row = item
                            while row.parent:
                                count_in_parent = len([i for i in inner_items if i in row.parent.descendants or i == row.parent])
                                count_in_row = len([i for i in inner_items if i in row.descendants or i == row])
                                if count_in_parent > count_in_row:
                                    break
                                row = row.parent
                            if row not in rows:
                                rows.append(row)
                except Exception as edp:
                    self.log(f"   ⚠️ Lỗi DrissionPage: {edp}")
                    # Nếu trình duyệt bị lỗi hoặc bị đóng, reset lại để lần sau tạo mới
                    if hasattr(self, '_dp_page'):
                        try:
                            self._dp_page.quit()
                        except:
                            pass
                        self._dp_page = None

            if not rows:
                title_text = soup.title.string.strip() if soup and soup.title and soup.title.string else "Unknown"
                self.log(f"⚠️ Không tìm thấy bảng dữ liệu! (Title trang: '{title_text}')")
                return []

            self.log(f"   -> Tìm thấy {len(rows)} offers thô.")

            parsed_items = []
            
            for row in rows:
                try:
                    txt = row.get_text(separator=' ', strip=True)

                    # --- CỘT 1: Thời gian giao dịch (Delivery) ---
                    delivery = "Unknown"
                    if "极速收货" in txt: delivery = "极速收货"
                    elif "分钟" in txt: 
                        del_match = re.search(r"(\d+分钟)", txt)
                        if del_match: delivery = del_match.group(1)

                    # --- CỘT 2: Giá & Tỷ lệ ---
                    ratio_match = re.search(r"1\s*元\s*=\s*([\d\.]+)", txt)
                    ratio_num = float(ratio_match.group(1)) if ratio_match else 0.0
                    ratio = str(ratio_num) if ratio_num > 0 else "N/A"

                    price_match = re.search(r"([\d\.]+)\s*元\s*/个", txt)
                    price = float(price_match.group(1)) if price_match else 0.0
                    
                    if price == 0.0 and ratio_num > 0:
                        price = round(1.0 / ratio_num, 4)
                    elif ratio_num == 0.0 and price > 0:
                        ratio_num = round(1.0 / price, 4)
                        ratio = str(ratio_num)

                    # --- CỘT 3: Số lượng (Stock) & Min ---
                    # Regex vạn năng hỗ trợ cả trang Receive (không có chữ Số lượng) và trang Search (có chữ Số lượng)
                    stock_match = re.search(r"元\s*/个(?:.*?(?:数量|库存)[：:\s]*)?\s*([\d\,]+)\s*个", txt)
                    stock_text = stock_match.group(1) if stock_match else "0"
                    stock = int(self.parse_number(stock_text))

                    # Min qty usually explicit on receive page
                    min_match = re.search(r"起收≥\s*([\d\,]+)", txt)
                    min_qty = int(self.parse_number(min_match.group(1))) if min_match else 1

                    seller_name = f"Trader (1¥={ratio})"

                    if price > 0:
                        parsed_items.append({
                            "seller": seller_name,
                            "unit_price": price,
                            "stock": stock,
                            "min_qty": min_qty,
                            "delivery": delivery,
                            "ratio": ratio,
                            "source": "dd373_recycle"
                        })
                except Exception as e:
                    self.log(f"   ⚠️ Lỗi parse dòng DD373: {e}")
                    continue

            parsed_items.sort(key=lambda x: x['unit_price'], reverse=True)
            
            count = len(parsed_items)
            if count > 0:
                top_price = parsed_items[0]['unit_price']
                self.log(f"✅ {name}: Lấy được {count} offers. Giá cao nhất: {top_price} tệ")
                return parsed_items
            else:
                self.log(f"⚠️ {name}: Không bóc tách được dữ liệu!")
                return []

        except Exception as e:
            self.log(f"❌ Exception ({item_config['name']}): {str(e)}")
            return []

    def send_to_server(self, item_name, data):
        payload = {"item_name": item_name, "platform": "dd373", "data": data}
        import requests as normal_requests 
        # 1. Gửi lên Server Online (dd373.gegechart.xyz) để Web cập nhật ngay
        try:
            res_on = normal_requests.post(ONLINE_SERVER_URL, json=payload, timeout=5)
            if res_on.status_code == 200:
                self.log(f"   -> 🌐 Đã cập nhật Server Online (dd373.gegechart.xyz)")
        except Exception as e:
            self.log(f"   -> ⚠️ Lỗi gửi Server Online: {str(e)}")
            
        # 2. Gửi lên Server Local (nếu đang bật)
        try:
            res_loc = normal_requests.post(LOCAL_SERVER_URL, json=payload, timeout=2)
            if res_loc.status_code == 200:
                self.log(f"   -> 💻 Đã đồng bộ Server Local (localhost:8000)")
        except Exception:
            pass

    def run_scheduler(self, items, delay):
        self.is_running = True
        self.log("🚀 Bắt đầu quét DD373...")
        while self.is_running:
            active_items = [i for i in items if i.get('enabled', True)]
            if not active_items:
                self.log("⚠️ Không có item nào được bật.")
                self.is_running = False; break

            for item in active_items:
                if not self.is_running: break
                results = self.scan_single_item(item)
                if results:
                    self.send_to_server(item['name'], results)
                time.sleep(random.uniform(2.0, 4.0))

            if not self.is_running: break
            
            wait_s = int(delay)
            self.log(f"💤 Nghỉ {wait_s}s...")
            for i in range(wait_s, 0, -1):
                if not self.is_running: break
                self.update_stats(datetime.now().strftime("%H:%M:%S"), f"{i}s")
                time.sleep(1)
        self.log("🛑 Đã dừng.")

    def _auto_slide_visual(self):
        try:
            import pyautogui
            from PIL import ImageGrab
            import time
            img = ImageGrab.grab()
            width, height = img.size
            pixels = img.load()
            
            button_x, button_y = None, None
            found = False
            for y in range(0, height, 5):
                for x in range(0, width, 5):
                    r, g, b = pixels[x, y]
                    if r > 240 and 100 < g < 150 and b < 50:
                        if (x+15 < width and y+15 < height and 
                            pixels[x+15, y][0] > 240 and pixels[x, y+15][0] > 240):
                            button_x, button_y = x, y
                            found = True
                            break
                if found:
                    break
                    
            if button_x and button_y:
                self.log(f"   👁️ Phát hiện thanh trượt bằng Computer Vision! Đang kéo...")
                orig_x, orig_y = pyautogui.position()
                pyautogui.moveTo(button_x + 10, button_y + 10)
                time.sleep(0.1)
                pyautogui.mouseDown()
                time.sleep(0.05)
                # Kéo từ từ 380px sang phải
                steps = 30
                step_dist = 380 / steps
                for i in range(steps):
                    pyautogui.moveTo(button_x + 10 + int(i * step_dist), button_y + 10 + int((i%3)-1))
                    time.sleep(0.01)
                pyautogui.mouseUp()
                pyautogui.moveTo(orig_x, orig_y)
                return True
            return False
        except Exception as e:
            # Không log lỗi này liên tục
            return False

# === UI SECTION ===
class DD373App:
    def __init__(self, root):
        self.root = root
        self.root.title("DD373 Recycle Sniper (v2 Matches Extension)")
        self.root.geometry("1000x700")
        
        self.items = self.load_config()
        self.engine = SniperEngine(self.log_msg, self.update_stats)

        # Layout
        left_panel = tk.Frame(root, width=250, bg="#f0f2f5")
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox = tk.Listbox(left_panel, height=30)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        right_panel = tk.Frame(root, bg="white")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Form nhập liệu
        cfg_frame = tk.LabelFrame(right_panel, text="Cấu Hình Item", padx=10, pady=10)
        cfg_frame.pack(fill=tk.X)

        tk.Label(cfg_frame, text="Tên Item:").grid(row=0, column=0, sticky="w")
        self.entry_name = ttk.Entry(cfg_frame, width=30)
        self.entry_name.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(cfg_frame, text="URL (Trang Recycle):").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_url = ttk.Entry(cfg_frame, width=70)
        self.entry_url.grid(row=1, column=1, columnspan=2, sticky="w", padx=5)

        tk.Label(cfg_frame, text="Cookie (Sau khi trượt):").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_cookie = ttk.Entry(cfg_frame, width=70)
        self.entry_cookie.grid(row=2, column=1, columnspan=2, sticky="w", padx=5)
        self.entry_cookie.insert(0, DEFAULT_COOKIE)

        tk.Label(cfg_frame, text="User-Agent Trình duyệt:").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_ua = ttk.Entry(cfg_frame, width=70)
        self.entry_ua.grid(row=3, column=1, columnspan=2, sticky="w", padx=5)
        self.entry_ua.insert(0, DEFAULT_USER_AGENT)

        btn_row = tk.Frame(cfg_frame)
        btn_row.grid(row=4, column=0, columnspan=3, pady=10)
        tk.Button(btn_row, text="💾 LƯU", command=self.save_item, bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="❌ Xóa", command=self.del_item, bg="red", fg="white").pack(side=tk.LEFT)
        tk.Button(btn_row, text="🧹 Mới", command=self.clear_form).pack(side=tk.LEFT)

        # Dash
        dash_frame = tk.Frame(right_panel, bg="#e3f2fd", pady=10)
        dash_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(dash_frame, text="Delay (s):").pack(side=tk.LEFT, padx=10)
        self.spin_delay = tk.Spinbox(dash_frame, from_=5, to=3600, width=5)
        self.spin_delay.pack(side=tk.LEFT); self.spin_delay.insert(0, "30")

        self.btn_start = tk.Button(dash_frame, text="▶️ START", command=self.toggle_scan, bg="blue", fg="white")
        self.btn_start.pack(side=tk.RIGHT, padx=20)
        self.lbl_countdown = tk.Label(dash_frame, text="--", font=("Arial", 14), bg="#e3f2fd")
        self.lbl_countdown.pack(side=tk.RIGHT)

        self.log_text = scrolledtext.ScrolledText(right_panel, height=20, bg="black", fg="#00e676")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.refresh_list()

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
        for item in self.items: self.listbox.insert(tk.END, item['name'])
    def on_select(self, event):
        idx = self.listbox.curselection()
        if not idx: return
        d = self.items[idx[0]]
        self.entry_name.delete(0, tk.END); self.entry_name.insert(0, d['name'])
        self.entry_url.delete(0, tk.END); self.entry_url.insert(0, d['url'])
        self.entry_cookie.delete(0, tk.END); self.entry_cookie.insert(0, d.get('cookie', DEFAULT_COOKIE))
        self.entry_ua.delete(0, tk.END); self.entry_ua.insert(0, d.get('user_agent', DEFAULT_USER_AGENT))
    def save_item(self):
        d = {
            "name": self.entry_name.get(), 
            "url": self.entry_url.get(), 
            "cookie": self.entry_cookie.get(),
            "user_agent": self.entry_ua.get()
        }
        idx = self.listbox.curselection()
        if idx: self.items[idx[0]] = d
        else: self.items.append(d)
        self.save_config(); self.refresh_list()
    def del_item(self):
        idx = self.listbox.curselection()
        if idx: del self.items[idx[0]]; self.save_config(); self.refresh_list()
    def clear_form(self):
        self.entry_name.delete(0, tk.END); self.entry_url.delete(0, tk.END); self.entry_cookie.delete(0, tk.END); self.entry_ua.delete(0, tk.END)
        self.entry_cookie.insert(0, DEFAULT_COOKIE)
        self.entry_ua.insert(0, DEFAULT_USER_AGENT)
    def toggle_scan(self):
        if not self.engine.is_running:
            t = threading.Thread(target=self.engine.run_scheduler, args=(self.items, int(self.spin_delay.get())))
            t.daemon = True; t.start()
            self.btn_start.config(text="⛔ STOP", bg="red")
        else:
            self.engine.is_running = False
            if hasattr(self.engine, '_dp_page') and self.engine._dp_page:
                try:
                    self.engine._dp_page.quit()
                except Exception:
                    pass
                self.engine._dp_page = None
            self.btn_start.config(text="▶️ START", bg="blue")

if __name__ == "__main__":
    import sys
    root = tk.Tk()
    app = DD373App(root)
    if "--auto-start" in sys.argv:
        root.after(1500, app.toggle_scan)
    root.mainloop()