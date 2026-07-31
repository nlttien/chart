from curl_cffi import requests
import re

# === CẤU HÌNH COOKIE ===
# (Giữ nguyên Cookie cũ của bạn)
MY_COOKIE = 'eldoradogg_currencyPreference=USD; cr-homepage-usp=1; p-checkout-test=1; cr-currency-aa=0; cr-homepage-aa=0; cr-top-up-aa=1; p-primer-update=1; curr-homepage-trending-games=1; cr-smaller-other-sellers-list=1; or-non-instant-redesign=1; p-c-badges=1; cr-top-up-swipeable=1; cr-homepage-popular-products=0; curr-offer-head-check=1; cr-tally-roblox-survey=1; it-product-aa=1; cr-topup-discount=0; p-billing-descriptor=0; it-abc=0; ac-gs-aa=1; cr-global-sec-button=0; cr-top-up-seller-reviews=0; pseudoId=14ea29d1-5f9d-42dd-bb2c-4d6b8aeb135f; cr-offer-sorting-v2=0; ac-score-p-g=1; cr-dark-theme=1; ac-more-like-v3=0; it-offer-listing-aa=0; ac-offer-listing-aa=1; ac-offer-p-aa=1; ac-price-mb=1; __Host-XSRF-TOKEN=d02a33864d608bcbfa8b55f5e9add2dd308fce976898937ffe8c4f8be751b098; eldoradogg_locale=en-US; rtkclickid-store=69870d56e7319caefb38eaee'

# === TỰ ĐỘNG LẤY XSRF TOKEN TỪ COOKIE ===
# Tìm đoạn mã sau chữ __Host-XSRF-TOKEN=
xsrf_match = re.search(r'__Host-XSRF-TOKEN=([a-zA-Z0-9]+)', MY_COOKIE)
xsrf_token = xsrf_match.group(1) if xsrf_match else ""

if not xsrf_token:
    print("⚠️ CẢNH BÁO: Không tìm thấy XSRF TOKEN trong Cookie! Có thể sẽ lỗi 403.")
else:
    print(f"🔑 Đã trích xuất XSRF Token: {xsrf_token[:10]}...")

API_URL = "https://www.eldorado.gg/api/predefinedOffers/augmentedGame/offers"

HEADERS = {
    "authority": "www.eldorado.gg",
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8",
    "referer": "https://www.eldorado.gg/",
    "origin": "https://www.eldorado.gg",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "cookie": MY_COOKIE,
    "x-xsrf-token": xsrf_token  # <--- THÊM DÒNG NÀY ĐỂ FIX LỖI 403
}

params = {
    'gameId': '220',
    'category': 'Currency',
    'offerAttributeIdsCsv': '0-0',
    'tradeEnvironmentValue0': 'Fate of the Vaal',
    'pageSize': '10',
    'pageIndex': '1',
    'offerSortingCriterion': 'Price'
}

print("🔄 Đang kết nối lại với Token bảo mật...")

try:
    with requests.Session(impersonate="chrome120") as s:
        resp = s.get(API_URL, params=params, headers=HEADERS, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('results', [])
            print(f"✅ THÀNH CÔNG TUYỆT ĐỐI! Lấy được {len(items)} items.")
            if items:
                first = items[0]
                price = first.get('offer', {}).get('pricePerUnit', {}).get('amount')
                seller = first.get('user', {}).get('username')
                print(f"   -> Giá Top 1: ${price} | Seller: {seller}")
        else:
            print(f"❌ VẪN LỖI: HTTP {resp.status_code}")
            print("Nội dung lỗi:", resp.text[:300]) 

except Exception as e:
    print(f"❌ Lỗi ngoại lệ: {e}")