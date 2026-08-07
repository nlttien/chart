import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger("avatar_manager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVATAR_DIR = os.path.join(BASE_DIR, "data", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

def get_headers(url: str) -> dict:
    if "eldorado" in url.lower():
        return {
            "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "referer": "https://www.eldorado.gg/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
    return {
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
    if not seller or not remote_url or not remote_url.startswith("http"):
        return None
        
    local_path = get_avatar_file_path(seller)
    if os.path.exists(local_path) and os.path.getsize(local_path) > 500:
        return local_path

    try:
        logger.info(f"[Avatar Manager] Downloading avatar for '{seller}' from {remote_url}...")
        headers = get_headers(remote_url)
        resp = requests.get(remote_url, headers=headers, timeout=10)
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

def generate_fallback_svg_avatar(seller: str) -> str:
    s = (seller or "Shop").strip()
    s_clean = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    
    # Preset color schemes & text matching G2G/Eldorado live shop icons
    if 'cnl' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#18181b" stroke="#3f3f46" stroke-width="4"/>
          <text x="50" y="42" font-family="Arial, sans-serif" font-weight="900" font-size="16" fill="#ffffff" text-anchor="middle">I'M A GAMER</text>
          <text x="50" y="62" font-family="Arial, sans-serif" font-weight="800" font-size="12" fill="#38bdf8" text-anchor="middle">FOR LIVING</text>
        </svg>'''
    elif 'thanku' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#facc15" stroke="#eab308" stroke-width="4"/>
          <text x="50" y="58" font-family="Verdana, sans-serif" font-weight="900" font-size="22" fill="#ef4444" text-anchor="middle">Thanku.</text>
        </svg>'''
    elif 'gege' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#f97316" stroke="#ea580c" stroke-width="4"/>
          <text x="50" y="46" font-size="28" text-anchor="middle">🦊</text>
          <text x="50" y="74" font-family="Arial, sans-serif" font-weight="900" font-size="16" fill="#ffffff" text-anchor="middle">GEGE</text>
        </svg>'''
    elif 'alotofgold' in s_clean or 'gold' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#eab308" stroke="#ca8a04" stroke-width="4"/>
          <text x="50" y="48" font-size="28" text-anchor="middle">💰</text>
          <text x="50" y="74" font-family="Arial, sans-serif" font-weight="900" font-size="14" fill="#ffffff" text-anchor="middle">GOLD</text>
        </svg>'''
    elif 'eternal' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#eab308" stroke="#a16207" stroke-width="4"/>
          <text x="50" y="46" font-size="26" text-anchor="middle">🎮</text>
          <text x="50" y="74" font-family="Arial, sans-serif" font-weight="900" font-size="13" fill="#000000" text-anchor="middle">ETERNAL</text>
        </svg>'''
    elif 'player' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#ffffff" stroke="#cbd5e1" stroke-width="4"/>
          <text x="50" y="58" font-family="Arial, sans-serif" font-weight="900" font-size="20" fill="#0f172a" text-anchor="middle">PLAYER</text>
        </svg>'''
    elif 'gaugau' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#15803d" stroke="#166534" stroke-width="4"/>
          <text x="50" y="48" font-size="28" text-anchor="middle">🔄</text>
          <text x="50" y="74" font-family="Arial, sans-serif" font-weight="900" font-size="13" fill="#ffffff" text-anchor="middle">GAUGAU</text>
        </svg>'''
    elif '1min' in s_clean or 'delivery' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#ffffff" stroke="#ef4444" stroke-width="4"/>
          <text x="50" y="46" font-size="26" text-anchor="middle">⚡</text>
          <text x="50" y="72" font-family="Arial, sans-serif" font-weight="900" font-size="12" fill="#ef4444" text-anchor="middle">1MIN</text>
        </svg>'''
    elif 'bushido' in s_clean or '269' in s_clean:
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#0f172a" stroke="#eab308" stroke-width="4"/>
          <text x="50" y="45" font-family="Arial, sans-serif" font-weight="900" font-size="16" fill="#eab308" text-anchor="middle">269</text>
          <text x="50" y="65" font-family="Arial, sans-serif" font-weight="800" font-size="12" fill="#ffffff" text-anchor="middle">STORE</text>
        </svg>'''
    else:
        # Default modern styled SVG
        initial = s[0].upper() if s else "?"
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="#1e293b" stroke="#475569" stroke-width="4"/>
          <text x="50" y="62" font-family="Arial, sans-serif" font-weight="900" font-size="34" fill="#38bdf8" text-anchor="middle">{initial}</text>
        </svg>'''
