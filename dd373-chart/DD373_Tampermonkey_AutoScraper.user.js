// ==UserScript==
// @name         ⚡ DD373 Auto Sniper to Unified Server
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  Tự động đọc dữ liệu bảng giá DD373 và gia hạn Cookie về Unified Server
// @author       Antigravity
// @match        https://www.dd373.com/s-*
// @grant        GM_xmlhttpRequest
// @connect      192.168.2.114
// @connect      localhost
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';

    // CẤU HÌNH SERVER
    const BACKEND_URL = "http://192.168.2.114:8000/update_data";
    const ITEM_NAME = "DD373 POE2 Divine Orb";
    const RELOAD_INTERVAL_SEC = 30; // Tự động làm mới trang sau mỗi 30 giây để lấy giá mới nhất

    // Tạo bảng HUD hiển thị trạng thái góc dưới bên phải màn hình
    const hud = document.createElement('div');
    hud.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 999999;
        background: linear-gradient(135deg, #181c2e, #1e243b);
        color: #00e676;
        padding: 14px 18px;
        border-radius: 10px;
        font-family: Arial, sans-serif;
        font-size: 13px;
        font-weight: bold;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        border: 2px solid #00e676;
        display: flex;
        flex-direction: column;
        gap: 6px;
    `;
    hud.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 15px;">
            <span style="color: #ffcc00;">⚡ DD373 AUTO SNIPER (BROWSER)</span>
            <span id="dd-status" style="background: #00e67620; color: #00e676; padding: 2px 8px; border-radius: 4px; font-size: 11px;">LIVE</span>
        </div>
        <div style="font-size: 11px; color: #aaa;" id="dd-log">Đang chuẩn bị quét dữ liệu...</div>
    `;
    document.body.appendChild(hud);

    function log(msg, color = '#aaa') {
        const el = document.getElementById('dd-log');
        if (el) {
            el.style.color = color;
            el.innerText = msg;
        }
        console.log("[DD373 Sniper]", msg);
    }

    function parseNumber(text) {
        if (!text) return 0.0;
        const match = text.match(/(\d+\.?\d*)/);
        return match ? parseFloat(match[1]) : 0.0;
    }

    function scrapeAndSend() {
        log("🔎 Đang quét dữ liệu bảng giá...", "#ffcc00");

        // Tìm container bảng
        let container = document.querySelector(".platform-receive-content") ||
            document.querySelector(".b2c-goods-item") ||
            document.querySelector(".goods-list");

        let rows = [];
        if (container) {
            rows = Array.from(container.querySelectorAll("ul"));
            if (rows.length === 0) rows = Array.from(container.querySelectorAll("li"));
        }

        if (rows.length === 0) {
            // Universal fallback
            rows = Array.from(document.querySelectorAll("ul, li")).filter(el => {
                const txt = el.innerText || "";
                return (txt.includes("元/个") || txt.includes("1元=")) && el.querySelectorAll("li").length >= 3;
            });
        }

        if (rows.length === 0) {
            log("⚠️ Đang kiểm tra xác thực Aliyun WAF...", "#ff3b30");
            return;
        }

        const offers = [];

        rows.forEach(row => {
            try {
                const cols = row.querySelectorAll("li");
                if (cols.length < 3) return;

                // 1. Delivery time
                const delivEl = cols[0].querySelector("span.colorFF5") || cols[0];
                const delivery = delivEl.innerText.trim();

                // 2. Min Qty & Ratio
                const infoText = cols[1].innerText || "";
                const minQtyMatch = infoText.match(/(?:>=|≥|满)\s*(\d+)/) || infoText.match(/(\d+)\s*(?:件|个|m)/i);
                const minQty = minQtyMatch ? parseInt(minQtyMatch[1], 10) : 1;

                const ratioMatch = infoText.match(/1元[=≈](\d+\.?\d*)/);
                const ratio = ratioMatch ? `1元=${ratioMatch[1]}M` : "";

                // 3. Price
                const priceEl = cols[2].querySelector("span.colorF60") || cols[2];
                const unitPrice = parseNumber(priceEl.innerText);

                // 4. Stock
                let stock = 0;
                if (cols.length > 3) {
                    stock = Math.round(parseNumber(cols[3].innerText));
                }

                // 5. Seller
                let seller = "DD373_User";
                let online = "Online";
                if (cols.length > 4) {
                    const sellerText = cols[4].innerText.trim();
                    if (sellerText) seller = sellerText.split('\n')[0].trim();
                }

                if (unitPrice > 0) {
                    offers.push({
                        delivery: delivery,
                        min_qty: minQty,
                        ratio: ratio,
                        unit_price: unitPrice,
                        stock: stock,
                        seller: seller,
                        sold_total: 0,
                        online: online
                    });
                }
            } catch (err) {
                // Ignore row error
            }
        });

        if (offers.length === 0) {
            log("⚠️ Chưa có offer hợp lệ, thử lại sau...", "#ff9800");
            return;
        }

        if (document.cookie && document.cookie.length > 10) {
            GM_xmlhttpRequest({
                method: "POST",
                url: "http://192.168.2.114:8000/api/v1/dd373/cookie",
                headers: { "Content-Type": "application/json" },
                data: JSON.stringify({ cookie: document.cookie })
            });
        }

        const payload = {
            item_name: ITEM_NAME,
            platform: "dd373",
            data: offers
        };

        GM_xmlhttpRequest({
            method: "POST",
            url: BACKEND_URL,
            headers: {
                "Content-Type": "application/json"
            },
            data: JSON.stringify(payload),
            onload: function (response) {
                if (response.status >= 200 && response.status < 300) {
                    log(`✅ Đã cập nhật ${offers.length} offers & Cookie sống về Server!`, "#00e676");
                } else {
                    log(`❌ Lỗi gửi Server (${response.status})`, "#ff3b30");
                }
            },
            onerror: function () {
                log("❌ Không thể kết nối Server 192.168.2.114:8000", "#ff3b30");
            }
        });
    }

    // Chạy lần đầu sau khi trang tải 2 giây
    setTimeout(scrapeAndSend, 2000);

    // Tự động làm mới trang định kỳ để cập nhật giá mới nhất
    let count = RELOAD_INTERVAL_SEC;
    setInterval(() => {
        count--;
        const el = document.getElementById('dd-status');
        if (el) el.innerText = `RELOAD SAU ${count}s`;
        if (count <= 0) {
            window.location.reload();
        }
    }, 1000);

})();
