import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger("chart_config")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "platform_configs.json")

DEFAULT_CONFIG = {
    "scrape_interval_seconds": 15,
    "auto_scrape_enabled": True,
    "dd373": [
        {
            "name": "DD373 POE2 Divine Orb",
            "url": "https://www.dd373.com/s-3hcpqw-bwgvrk-fj6p5a-0-0-0-8rknmp-0-0-receive-0-0-1-0-0-0.html",
            "enabled": True
        },
        {
            "name": "DD373 POE1 Divine Orb",
            "url": "https://www.dd373.com/s-mnh4dv-n75hgf-mxgd6e-0-0-0-94vje2-0-0-receive-0-0-1-0-0-0.html",
            "enabled": True
        }
    ],
    "eldorado": [
        {
            "name": "Eldorado PoE 1 Divine Orb",
            "keyword": "Divine Orb",
            "service_id": "2",
            "brand_id": "Curse of The Allflames SC",
            "filter_attr": "Currency",
            "enabled": True
        },
        {
            "name": "Eldorado PoE 2 Divine Orb",
            "keyword": "Divine Orb",
            "service_id": "220",
            "brand_id": "Runes of Aldur Standard",
            "filter_attr": "Currency",
            "enabled": True
        },
        {
            "name": "Eldorado PoE 1 Chaos",
            "keyword": "Chaos Orb",
            "service_id": "2",
            "brand_id": "Curse of The Allflames SC",
            "filter_attr": "Currency",
            "enabled": True
        },
        {
            "name": "Eldorado PoE 1 Mirror",
            "keyword": "Mirror of Kalandra",
            "service_id": "2",
            "brand_id": "Curse of The Allflames SC",
            "filter_attr": "Currency",
            "enabled": True
        },
        {
            "name": "Eldorado PoE 2 Mirror",
            "keyword": "Mirror of Kalandra",
            "service_id": "220",
            "brand_id": "Runes of Aldur Standard",
            "filter_attr": "Currency",
            "enabled": True
        }
    ],
    "g2g": [
        {
            "name": "PoE 1 Divine Orb",
            "keyword": "divine orb",
            "service_id": "lgc_service_1",
            "brand_id": "lgc_game_19398",
            "filter_attr": "lgc_19398_server:lgc_19398_server_63274|lgc_19398_tier:lgc_19398_tier_42692",
            "enabled": True
        },
        {
            "name": "PoE 2 Divine Orb",
            "keyword": "divine orb",
            "service_id": "lgc_service_1",
            "brand_id": "lgc_game_27013",
            "filter_attr": "lgc_27013_platform:lgc_27013_platform_62230|lgc_27013_tier:lgc_27013_tier_54399",
            "enabled": True
        },
        {
            "name": "PoE 1 Chaos",
            "keyword": "chaos orb",
            "service_id": "lgc_service_1",
            "brand_id": "lgc_game_19398",
            "filter_attr": "lgc_19398_server:lgc_19398_server_63274|lgc_19398_tier:lgc_19398_tier_42689",
            "enabled": True
        },
        {
            "name": "PoE 1 Mirror",
            "keyword": "mirror",
            "service_id": "lgc_service_1",
            "brand_id": "lgc_game_19398",
            "filter_attr": "lgc_19398_server:lgc_19398_server_63274|lgc_19398_tier:lgc_19398_tier_42698",
            "enabled": True
        },
        {
            "name": "PoE 2 Mirror",
            "keyword": "mirror",
            "service_id": "lgc_service_1",
            "brand_id": "lgc_game_27013",
            "filter_attr": "lgc_27013_platform:lgc_27013_platform_62230|lgc_27013_tier:lgc_27013_tier_54403",
            "enabled": True
        }
    ],
    "qiandao": [
        {
            "name": "poe2 div",
            "jwt_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEwMDc0MzYxODIyMzUxNjQxNDAiLCJ0eXBlIjoiVVNFUiIsImV4cCI6MTc4NTA2MDE1NSwiaWF0IjoxNzg0ODAwOTU1fQ.oT6T-yj8-8byoqPhVUnwcd32We9WWBQdTmhU6ZnS_CXrqP4C4tyWLnoPszMx9O8e4z_Lch0iQCwFuCQF9IHetqmNmAjy2BiddHtrEsqKhkuFGUlFh3T2oHZvLP_0pj-Bqmhx6sNWrXgSKsGOHtgrJDCmTpHVx5uxtozo3dJsGsTUXjHFExaL7ev2_aw8-kXB0PcHRT5yGNXgJkScBIqeQwB-jcs3WJA78xTNyO7qRMndqoFLmGv10Wsb06cdwx8YMsF8NSII_HZxyS0K0b5LEHoOCJkFZnsU6D6SdSgWkN6afIXbRWXt31vtKPIpNStQ5B7N3mIMd0NB9x1GUOBIcQ",
            "spu_id": "836104794648117776",
            "spec_id": "269603",
            "enabled": True
        },
        {
            "name": "poe1 div",
            "jwt_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEwMDc0MzYxODIyMzUxNjQxNDAiLCJ0eXBlIjoiVVNFUiIsImV4cCI6MTc4NTA2MDE1NSwiaWF0IjoxNzg0ODAwOTU1fQ.oT6T-yj8-8byoqPhVUnwcd32We9WWBQdTmhU6ZnS_CXrqP4C4tyWLnoPszMx9O8e4z_Lch0iQCwFuCQF9IHetqmNmAjy2BiddHtrEsqKhkuFGUlFh3T2oHZvLP_0pj-Bqmhx6sNWrXgSKsGOHtgrJDCmTpHVx5uxtozo3dJsGsTUXjHFExaL7ev2_aw8-kXB0PcHRT5yGNXgJkScBIqeQwB-jcs3WJA78xTNyO7qRMndqoFLmGv10Wsb06cdwx8YMsF8NSII_HZxyS0K0b5LEHoOCJkFZnsU6D6SdSgWkN6afIXbRWXt31vtKPIpNStQ5B7N3mIMd0NB9x1GUOBIcQ",
            "spu_id": "836104794648117857",
            "spec_id": "269627",
            "enabled": True
        }
    ]
}

def load_config() -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving config file: {e}")
