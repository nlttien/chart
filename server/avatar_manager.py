import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger("avatar_manager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVATAR_DIR = os.path.join(BASE_DIR, "data", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

HEADERS = {
    "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "referer": "https://www.g2g.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def clean_seller_name(seller: str) -> str:
    if not seller:
        return "unknown"
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', seller.strip().lower())
    return cleaned or "unknown"

def get_avatar_file_path(seller: str) -> str:
    slug = clean_seller_name(seller)
    return os.path.join(AVATAR_DIR, f"{slug}.png")

def download_and_cache_avatar(seller: str, remote_url: str) -> Optional[str]:
    """
    Tải avatar từ remote_url (G2G/Eldorado) bằng Referer header và lưu vào data/avatars/<seller>.png
    Trả về đường dẫn file cục bộ nếu thành công.
    """
    if not seller or not remote_url or not remote_url.startswith("http"):
        return None
        
    local_path = get_avatar_file_path(seller)
    
    # Nếu file đã tồn tại và kích thước > 0 -> dùng lại
    if os.path.exists(local_path) and os.path.getsize(local_path) > 500:
        return local_path

    try:
        logger.info(f"[Avatar Manager] Downloading avatar for '{seller}' from {remote_url}...")
        resp = requests.get(remote_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 200:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"[Avatar Manager] Saved avatar for '{seller}' -> {local_path} ({len(resp.content)} bytes)")
            return local_path
        else:
            logger.warning(f"[Avatar Manager] Failed download for '{seller}': status {resp.status_code}")
    except Exception as e:
        logger.error(f"[Avatar Manager] Error downloading avatar for '{seller}': {e}")
        
    return None

def get_avatar_url_for_seller(seller: str, remote_url: str = "") -> str:
    """
    Trả về API endpoint phục vụ avatar cục bộ /api/v1/avatar/{seller}
    Tự động kích hoạt nạp ảnh nếu remote_url chưa nạp.
    """
    slug = clean_seller_name(seller)
    local_path = get_avatar_file_path(seller)
    
    if not os.path.exists(local_path) and remote_url:
        download_and_cache_avatar(seller, remote_url)
        
    return f"/api/v1/avatar/{slug}"
