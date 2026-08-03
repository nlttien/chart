import sys
import json
import logging
from server.engines.dd373_engine import scan_dd373_item
from server.smart_logger import SmartLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def main():
    print("============================================================")
    print("TESTING DD373 PLAYWRIGHT STEALTH & SMART DIAGNOSTIC LOGGING")
    print("============================================================")

    test_item = {
        "name": "DD373 PoE 2 Divine Orb Test",
        "url": "https://www.dd373.com/s-49phxm-0-0-0-0-0-0-0-0-1-0-0-0.html?Keyword=%E6%B5%81%E4%BA%A1"
    }

    print(f"\n[1] Scanning DD373 item: {test_item['name']}...")
    results = scan_dd373_item(test_item)

    print(f"\n[2] Scan Results Count: {len(results)}")
    if len(results) > 0:
        print("Top 3 lowest price offers:")
        for r in results[:3]:
            print(f"  - Seller: {r['seller']} | Price: {r['unit_price']} ¥ | Stock: {r['stock']} | Delivery: {r['delivery']}")
    else:
        print("⚠️ No items returned. Checking Smart Logs...")

    print("\n[3] Retrieving Smart Logs for DD373:")
    logs = SmartLogger.get_logs("dd373", limit=10)
    for log in logs:
        print(f"  - [{log['timestamp']}] [{log['level']}] [{log['error_code']}] {log['message']}")
        if log.get("details"):
            print(f"    Details: {json.dumps(log['details'], ensure_ascii=False)}")

    print("\n[4] Checking Scraper Metrics Status:")
    status = SmartLogger.get_status("dd373")
    print(json.dumps(status, indent=2, ensure_ascii=False))

    screenshot_path = SmartLogger.get_last_error_screenshot()
    if screenshot_path:
        print(f"\n[5] Failure Screenshot Path: {screenshot_path}")

if __name__ == "__main__":
    main()
