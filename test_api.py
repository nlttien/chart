#!/usr/bin/env python3
"""
Automated Test Script for Unified Chart Market REST API Server
Usage:
    python3 test_api.py [base_url]
Default base_url: http://localhost:8000
"""

import sys
import json
import urllib.request
import urllib.parse

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

def make_request(method, path, data=None):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    
    body = json.dumps(data).encode("utf-8") if data else None
    
    try:
        with urllib.request.urlopen(req, data=body, timeout=10) as response:
            status = response.getcode()
            res_body = response.read().decode("utf-8")
            return status, json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        return e.code, json.loads(res_body) if res_body else {}
    except Exception as e:
        return 500, {"error": str(e)}

def run_tests():
    print("============================================================")
    print(f"       TESTING UNIFIED CHART REST API AT: {BASE_URL}")
    print("============================================================\n")

    endpoints = [
        ("GET", "/api/v1/health", "Health Check"),
        ("GET", "/api/v1/platforms", "Get Platforms List"),
        ("GET", "/api/v1/g2g/items", "Get Monitored Items (G2G)"),
        ("GET", "/api/v1/g2g/snapshot", "Get Snapshot (G2G)"),
        ("GET", "/api/v1/eldorado/snapshot", "Get Snapshot (Eldorado)"),
        ("GET", "/api/v1/qiandao/snapshot", "Get Snapshot (Qiandao)"),
        ("GET", "/api/v1/dd373/snapshot", "Get Snapshot (DD373)"),
        ("GET", "/api/v1/config", "Get System Config"),
        ("GET", "/api/v1/scraper/status", "Get Scraper Status"),
        ("GET", "/snapshot?platform=g2g", "Legacy Snapshot"),
        ("GET", "/api/exchange_rate", "Legacy Exchange Rate"),
    ]

    passed = 0
    failed = 0

    for method, path, title in endpoints:
        status, resp = make_request(method, path)
        if status in [200, 201]:
            print(f"[SUCCESS] {title} ({method} {path}) - Status: {status}")
            passed += 1
        else:
            print(f"[FAIL] {title} ({method} {path}) - Status: {status} | Error: {resp}")
            failed += 1

    print("\n------------------------------------------------------------")
    print(f"RESULTS: {passed} PASSED, {failed} FAILED / {len(endpoints)} TOTAL")
    print("------------------------------------------------------------")

if __name__ == "__main__":
    run_tests()
