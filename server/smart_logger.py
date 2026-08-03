import os
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import deque

logger = logging.getLogger("smart_logger")

# Maximum log entries to keep in memory ring buffer
MAX_LOG_ENTRIES = 200

# Directory for logs and failure screenshots
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LAST_ERROR_SCREENSHOT = os.path.join(LOG_DIR, "dd373_last_error.png")

# Ring buffer for structured log entries
_LOG_BUFFER: deque = deque(maxlen=MAX_LOG_ENTRIES)

# Global status metrics
_PLATFORM_STATS: Dict[str, Dict[str, Any]] = {
    "dd373": {
        "status": "idle",
        "last_success_time": None,
        "last_error_time": None,
        "last_error_code": None,
        "captcha_attempts": 0,
        "captcha_solved": 0,
        "total_scrapes": 0,
        "failed_scrapes": 0,
        "cookie_status": "valid"
    }
}

class SmartLogger:
    @staticmethod
    def log_event(
        platform: str,
        level: str,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        screenshot_saved: bool = False
    ):
        """
        Record a structured log event with timestamp, platform, error_code, and detailed context.
        """
        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%SZ")

        log_entry = {
            "timestamp": timestamp_str,
            "platform": platform,
            "level": level.upper(),
            "error_code": error_code,
            "message": message,
            "details": details or {},
            "has_screenshot": screenshot_saved
        }

        _LOG_BUFFER.appendleft(log_entry)

        # Standard logging string
        log_line = f"[{timestamp_str}] [{platform.upper()}] [{level.upper()}] [{error_code}] {message}"
        if level.upper() == "ERROR":
            logger.error(f"{log_line} | details: {details}")
        elif level.upper() == "WARNING":
            logger.warning(f"{log_line} | details: {details}")
        else:
            logger.info(log_line)

        # Update stats
        if platform in _PLATFORM_STATS:
            stats = _PLATFORM_STATS[platform]
            stats["status"] = level.lower()
            if error_code == "PARSED_SUCCESS":
                stats["last_success_time"] = timestamp_str
                stats["total_scrapes"] += 1
            elif level.upper() == "ERROR":
                stats["last_error_time"] = timestamp_str
                stats["last_error_code"] = error_code
                stats["failed_scrapes"] += 1
            
            if error_code == "CAPTCHA_SOLVING_ATTEMPT":
                stats["captcha_attempts"] += 1
            elif error_code == "CAPTCHA_SOLVE_SUCCESS":
                stats["captcha_solved"] += 1

    @staticmethod
    def get_logs(platform: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent structured logs, optionally filtered by platform."""
        logs = list(_LOG_BUFFER)
        if platform:
            logs = [l for l in logs if l.get("platform") == platform.lower()]
        return logs[:limit]

    @staticmethod
    def get_status(platform: str = "dd373") -> Dict[str, Any]:
        """Get current platform scraper status and metrics."""
        return _PLATFORM_STATS.get(platform, {
            "status": "unknown",
            "message": f"No status tracked for {platform}"
        })

    @staticmethod
    def get_last_error_screenshot() -> Optional[str]:
        """Return path to last failure screenshot if it exists."""
        if os.path.exists(LAST_ERROR_SCREENSHOT):
            return LAST_ERROR_SCREENSHOT
        return None
