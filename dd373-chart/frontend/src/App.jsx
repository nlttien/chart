import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { createChart, LineSeries } from 'lightweight-charts';
import axios from 'axios';

// --- CẤU HÌNH API TỶ GIÁ MỚI (Ổn định & Miễn phí) ---
// Sử dụng Open Exchange Rate API (Không cần Key, Base là CNY)
const API_URL = "https://open.er-api.com/v6/latest/CNY";

// --- THEME CONFIG ---
const theme = {
  bg: '#0e1117',
  sidebar: '#262730',
  card: '#1e1e1e',
  text: '#fafafa',
  textSec: '#b0b0b0',
  cyan: '#00bcd4',
  border: '#414141',
  danger: '#ff4b4b',
  gold: '#ffc107',
  green: '#00e676'
};

// --- STYLES ---
const styles = {
  app: { display: 'flex', width: '100vw', height: '100vh', backgroundColor: theme.bg, color: theme.text, overflow: 'hidden' },
  
  sidebar: (isOpen) => ({
    width: isOpen ? '280px' : '0px',
    backgroundColor: theme.sidebar,
    padding: isOpen ? '20px' : '20px 0px',
    display: 'flex', flexDirection: 'column', 
    gap: '15px',
    borderRight: '1px solid ' + theme.border, 
    height: '100%', overflowY: 'auto', flexShrink: 0,
    transition: 'all 0.3s ease', opacity: isOpen ? 1 : 0,
    visibility: isOpen ? 'visible' : 'hidden'
  }),

  main: { 
    flex: 1, padding: '20px', height: '100%', overflowY: 'auto', 
    display: 'flex', flexDirection: 'column', gap: '20px',
    width: '100%', position: 'relative'
  },

  toggleBtn: {
    backgroundColor: theme.card, border: `1px solid ${theme.border}`,
    color: theme.text, width: '36px', height: '36px', borderRadius: '4px',
    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
    marginRight: '15px', flexShrink: 0
  },

  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' },
  
  kpiCard: { 
    backgroundColor: theme.card, padding: '15px', borderRadius: '8px', 
    borderLeft: `4px solid ${theme.cyan}`, boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    display: 'flex', flexDirection: 'column', justifyContent: 'center'
  },
  kpiLabel: { fontSize: '0.85rem', color: theme.textSec, textTransform: 'uppercase', marginBottom: '5px' },
  kpiValue: { fontSize: '1.6rem', fontWeight: 'bold', color: '#fff' },
  
  chartSection: { 
    flex: '0 0 300px', 
    backgroundColor: theme.card, borderRadius: '8px', border: '1px solid #333',
    position: 'relative', overflow: 'hidden', padding: '10px',
    minHeight: '300px',
    display: 'flex', flexDirection: 'column',
    width: '100%'
  },
  
  tableSection: {
    flex: 1, 
    backgroundColor: theme.card, borderRadius: '8px', border: '1px solid #333',
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
    minHeight: '400px'
  },
  tableWrapper: { flex: 1, overflowY: 'auto' }, 
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '13px' },
  th: { 
    textAlign: 'left', padding: '12px 15px', borderBottom: '1px solid #444', 
    color: theme.textSec, backgroundColor: '#2b2b2b', position: 'sticky', top: 0, zIndex: 10 
  },
  td: { padding: '12px 15px', borderBottom: '1px solid #333' },
  
  currencyBtn: {
    marginLeft: '10px', padding: '2px 8px', fontSize: '0.7rem', 
    backgroundColor: '#333', border: '1px solid #555', color: '#fff', 
    borderRadius: '4px', cursor: 'pointer'
  },
  
  input: { 
    width: '100%', padding: '8px 10px', boxSizing: 'border-box',
    borderRadius: '4px', border: '1px solid #555', backgroundColor: '#111', 
    color: 'white', marginTop: '5px', fontSize: '13px', outline: 'none'
  },
  
  legend: { position: 'absolute', top: '10px', left: '10px', zIndex: 20, fontSize: '12px', color: '#fff', backgroundColor: 'rgba(0,0,0,0.7)', padding: '5px', borderRadius: '4px', pointerEvents: 'none' }
};

const PercentageBadge = ({ value }) => {
    if (value === undefined || value === null) return null;
    const color = value === 0 ? '#888' : (value > 0 ? theme.green : theme.danger);
    return <span style={{ color, fontSize: '0.8rem', fontWeight: 'bold', marginLeft: '5px' }}>{value > 0 ? '▲' : (value < 0 ? '▼' : '')} {Math.abs(value).toFixed(2)}%</span>;
};

const App = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [availableItems, setAvailableItems] = useState(() => { try { return JSON.parse(localStorage.getItem('sniper_items')) || []; } catch { return []; } });
  const [selectedItem, setSelectedItem] = useState(() => localStorage.getItem('sniper_selected') || null);
  const selectedItemRef = useRef(selectedItem);
  
  const [marketData, setMarketData] = useState({ 
      raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0, 
      timestamp: '--:--', order_book: [], item_name: 'Loading...', platform: 'g2g'
  });
  
  const [timeWindow, setTimeWindow] = useState(24);
  const [connectionStatus, setStatus] = useState("Connecting...");
  const [highlightText, setHighlightText] = useState("");
  
  // --- LOGIC TỶ GIÁ ---
  const [showVND, setShowVND] = useState(false);
  const [exchangeRateVND, setExchangeRateVND] = useState(3650);

  // Cập nhật API lấy tỷ giá mới
  useEffect(() => {
    const fetchRate = async () => {
        try {
            console.log("Fetching Exchange Rate from Open API...");
            const res = await axios.get(API_URL);
            
            // API open.er-api.com trả về { result: "success", rates: { VND: 3600, ... } }
            if (res.data && res.data.result === "success") {
                const rate = res.data.rates.VND;
                if (rate) {
                    setExchangeRateVND(rate);
                    console.log(`Updated Rate: 1 CNY = ${rate.toFixed(2)} VND`);
                }
            }
        } catch (error) {
            console.error("Lỗi lấy tỷ giá:", error);
            // Fallback nếu lỗi
            setExchangeRateVND(3650);
        }
    };
    fetchRate();
  }, []);

  const formatPrice = (price, isVND) => {
      if (!price) return '0';
      if (isVND) {
          return (price * exchangeRateVND).toLocaleString('vi-VN', { maximumFractionDigits: 0 });
      }
      return price.toFixed(4);
  };

  const mainChartContainerRef = useRef(null);
  const mainChartInstance = useRef(null);
  const seriesRef = useRef({});
  const mainLegendRef = useRef(null);

  // --- CHART SETUP ---
  useEffect(() => {
    if (!mainChartContainerRef.current) return;
    
    // Cấu hình chart
    const chart = createChart(mainChartContainerRef.current, {
        layout: { background: { type: 'solid', color: theme.card }, textColor: theme.textSec },
        grid: { vertLines: { color: '#333' }, horzLines: { color: '#333' } },
        height: 280,
        width: mainChartContainerRef.current.clientWidth,
        
        localization: {
            timeFormatter: (timestamp) => {
                return new Date(timestamp * 1000).toLocaleString('vi-VN', {
                    hour: '2-digit', minute: '2-digit', second: '2-digit',
                    day: '2-digit', month: '2-digit', hour12: false
                });
            }
        },
        timeScale: { 
            timeVisible: true, 
            secondsVisible: true, 
            rightOffset: 5, 
            fixRightEdge: true,
            tickMarkFormatter: (time) => {
                return new Date(time * 1000).toLocaleTimeString('vi-VN', { 
                    hour: '2-digit', minute: '2-digit', hour12: false 
                });
            }
        },
    });

    const sRaw = chart.addSeries(LineSeries, { color: '#555', lineWidth: 1, lineStyle: 2, lastValueVisible: false });
    const sPrice = chart.addSeries(LineSeries, { color: theme.cyan, lineWidth: 2, lastValueVisible: true });

    mainChartInstance.current = chart;
    seriesRef.current = { raw: sRaw, price: sPrice };

    // Legend Logic
    chart.subscribeCrosshairMove(param => {
        if (!mainLegendRef.current) return;
        if (!param.time || param.point.x < 0) {
            mainLegendRef.current.innerHTML = `<span style="color:${theme.cyan}">Live Price</span>`; 
            return;
        }
        const price = param.seriesData.get(sPrice);
        const raw = param.seriesData.get(sRaw);
        const pVal = price ? price.value.toFixed(4) : '-';
        const rVal = raw ? raw.value.toFixed(4) : '-';
        
        const timeStr = new Date(param.time * 1000).toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'});

        mainLegendRef.current.innerHTML = `
            <div style="display:flex; gap:10px; align-items:center">
                <span style="color:#888; font-size: 11px">[${timeStr}]</span>
                <span>Trusted: <b style="color:${theme.cyan}">${pVal}</b></span>
                <span style="color:#666">|</span>
                <span>Raw: <span style="color:#888">${rVal}</span></span>
            </div>
        `;
    });

    // --- FIX: RESIZE OBSERVER (Biểu đồ tự chỉnh size) ---
    const resizeObserver = new ResizeObserver(() => {
        if (mainChartContainerRef.current) {
            const w = mainChartContainerRef.current.clientWidth;
            const h = mainChartContainerRef.current.clientHeight;
            window.requestAnimationFrame(() => {
                chart.applyOptions({ width: w, height: h });
            });
        }
    });

    resizeObserver.observe(mainChartContainerRef.current);

    return () => { 
        resizeObserver.disconnect();
        chart.remove(); 
    };
  }, []);

  // --- FIX: SIDEBAR RESIZE TRIGGER (Lấp đầy khoảng trống khi đóng sidebar) ---
  useEffect(() => {
    const handleResize = () => {
        if (mainChartInstance.current && mainChartContainerRef.current) {
            const w = mainChartContainerRef.current.clientWidth;
            const h = mainChartContainerRef.current.clientHeight;
            mainChartInstance.current.applyOptions({ width: w, height: h });
        }
    };
    
    handleResize();
    // Chờ animation sidebar 0.3s kết thúc rồi resize lại lần nữa cho chắc
    const timer = setTimeout(handleResize, 310);
    return () => clearTimeout(timer);
  }, [isSidebarOpen]);

  // --- DATA FETCHING ---
  const fetchData = useCallback(async () => {
    if (!selectedItem) return;
    try {
        const snapRes = await axios.get(`/api/snapshot?item_name=${selectedItem}&hours=${timeWindow}`);
        const data = snapRes.data;
        if (data && data.order_book) {
            setMarketData(prev => ({ ...prev, ...data, item_name: selectedItem }));
        }
        const histRes = await axios.get(`/api/history?item_name=${selectedItem}&hours=${timeWindow}`);
        const hist = histRes.data.history;
        if (hist && hist.length > 0 && seriesRef.current.price) {
            seriesRef.current.price.setData(hist.map(x => ({ time: x.time, value: x.trusted_floor })));
            seriesRef.current.raw.setData(hist.map(x => ({ time: x.time, value: x.raw_floor })));
            mainChartInstance.current.timeScale().fitContent();
        }
    } catch (e) { console.error(e); }
  }, [selectedItem, timeWindow]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // --- WEBSOCKET ---
  useEffect(() => {
    let ws = new WebSocket(window.location.protocol === 'https:' ? `wss://${window.location.host}/ws` : `ws://${window.location.host}/ws`);
    ws.onopen = () => setStatus("🟢 Live");
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'UPDATE') {
            const item = data.item_name;
            setAvailableItems(prev => prev.includes(item) ? prev : [...prev, item]);
            
            if (!selectedItemRef.current) {
                setSelectedItem(item); selectedItemRef.current = item;
            }
            if (selectedItemRef.current === item) {
                setMarketData(prev => ({ ...prev, ...data }));
                const ts = new Date(data.timestamp).getTime() / 1000;
                if (seriesRef.current.price) {
                    seriesRef.current.price.update({ time: ts, value: data.trusted_floor });
                    seriesRef.current.raw.update({ time: ts, value: data.raw_floor });
                }
            }
        }
    };
    return () => ws.close();
  }, []);

  const handleItemChange = (e) => {
      const newItem = e.target.value;
      setSelectedItem(newItem); selectedItemRef.current = newItem;
      localStorage.setItem('sniper_selected', newItem);
      setMarketData(prev => ({...prev, order_book: [], raw_floor: 0, trusted_floor: 0 }));
  };

  const sortedBook = useMemo(() => {
    const d = [...marketData.order_book];
    return d.sort((a, b) => b.unit_price - a.unit_price);
  }, [marketData.order_book]);

  const currencySymbol = showVND ? '₫' : (marketData.platform === 'dd373' ? '¥' : '$');
  const platformColor = marketData.platform === 'dd373' ? theme.gold : theme.cyan;
  const priceLabel = marketData.platform === 'dd373' ? 'Max Price' : 'Floor Price';

  return (
    <div style={styles.app}>
      <div style={styles.sidebar(isSidebarOpen)}>
        <div style={{padding: '0 15px'}}>
            <h2 style={{fontSize:'1.1rem', color: theme.cyan, marginBottom:'15px'}}>🦅 DD373 Config</h2>
            <label style={{fontSize:'12px', color:'#888'}}>Select Item</label>
            <select style={styles.input} value={selectedItem || ''} onChange={handleItemChange}>
                {availableItems.length === 0 && !selectedItem && <option>Waiting for data...</option>}
                {availableItems.map(i => <option key={i} value={i}>{i}</option>)}
            </select>

            <label style={{fontSize:'12px', color:'#888', marginTop:'15px', display:'block'}}>Time Window</label>
            <select style={styles.input} value={timeWindow} onChange={(e) => setTimeWindow(Number(e.target.value))}>
                <option value={0.25}>15 Minutes</option>
                <option value={1}>1 Hour</option>
                <option value={4}>4 Hours</option>
                <option value={24}>24 Hours</option>
            </select>

            <label style={{fontSize:'12px', color:'#888', marginTop:'15px', display:'block'}}>Highlight Seller (Optional)</label>
            <input style={styles.input} placeholder="Type name to highlight..." 
                   value={highlightText} onChange={(e) => setHighlightText(e.target.value)} />

            <div style={{marginTop:'20px', padding:'10px', backgroundColor:'#222', borderRadius:'5px', fontSize:'11px', color:'#aaa'}}>
                API Rate: 1 CNY ≈ {exchangeRateVND.toFixed(0)} VND
            </div>
        </div>
        
        <div style={{marginTop:'auto', padding:'10px 15px', borderTop:'1px solid #333', fontSize:'12px'}}>
            Status: <span style={{color: connectionStatus.includes("Live") ? theme.green : theme.danger}}>{connectionStatus}</span>
        </div>
      </div>

      <div style={styles.main}>
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
            <div style={{display:'flex', alignItems:'center'}}>
                <button style={styles.toggleBtn} onClick={() => setIsSidebarOpen(!isSidebarOpen)}>☰</button>
                <h1 style={{fontSize:'1.5rem', margin:0, display:'flex', alignItems:'center'}}>
                    {selectedItem || 'Market'} 
                    <span style={{fontSize:'0.8rem', backgroundColor: platformColor, color:'#000', padding:'2px 6px', borderRadius:'4px', marginLeft:'10px'}}>
                        {marketData.platform || 'G2G'}
                    </span>
                </h1>
                <button 
                    style={{
                        ...styles.currencyBtn, 
                        borderColor: theme.green,
                        color: '#fff',
                        backgroundColor: 'rgba(0, 230, 118, 0.15)',
                        padding: '4px 10px',
                        fontSize: '0.75rem',
                        fontWeight: 'bold',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        marginLeft: '15px'
                    }} 
                    onClick={() => {
                        mainChartInstance.current?.timeScale().scrollToRealTime();
                    }}
                >
                    <span style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: theme.green,
                        boxShadow: `0 0 8px ${theme.green}`,
                        display: 'inline-block'
                    }}></span>
                    Live / Real-time
                </button>
            </div>
            <div style={{fontSize:'0.9rem', color:'#888'}}>
                {marketData.timestamp !== '--:--' 
                    ? new Date(marketData.timestamp).toLocaleTimeString('vi-VN') 
                    : '--:--'}
            </div>
        </div>

        <div style={styles.kpiGrid}>
            <div style={{...styles.kpiCard, borderLeft: `4px solid ${platformColor}`}}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                    <div style={styles.kpiLabel}>{priceLabel} (Trusted)</div>
                    <button style={styles.currencyBtn} onClick={() => setShowVND(!showVND)}>
                        {showVND ? 'Switch to CNY' : 'Switch to VND'}
                    </button>
                </div>
                <div style={{...styles.kpiValue, color: platformColor}}>
                    {currencySymbol} {formatPrice(marketData.trusted_floor, showVND)}
                </div>
                <div><PercentageBadge value={marketData.trusted_change} /></div>
            </div>

            <div style={styles.kpiCard}>
                <div style={styles.kpiLabel}>{priceLabel} (Raw)</div>
                <div style={styles.kpiValue}>
                    {currencySymbol} {formatPrice(marketData.raw_floor, showVND)}
                </div>
                <div><PercentageBadge value={marketData.raw_change} /></div>
            </div>

            <div style={styles.kpiCard}>
                <div style={styles.kpiLabel}>Top Stock</div>
                <div style={styles.kpiValue}>
                    {sortedBook[0]?.stock || 0}
                </div>
                <div style={{fontSize:'0.8rem', color:'#888'}}>Available</div>
            </div>

            <div style={styles.kpiCard}>
                <div style={styles.kpiLabel}>Total Offers</div>
                <div style={styles.kpiValue}>{sortedBook.length}</div>
                <div style={{fontSize:'0.8rem', color:'#888'}}>Active Sellers</div>
            </div>
        </div>

        <div style={styles.chartSection}>
            <div ref={mainLegendRef} style={styles.legend}>Loading...</div>
            <div ref={mainChartContainerRef} style={{width:'100%', flex: 1}} />
        </div>

        <div style={styles.tableSection}>
            <div style={{padding:'10px 15px', borderBottom:'1px solid #333', fontWeight:'bold', display:'flex', justifyContent:'space-between'}}>
                <span>📖 Live Order Book</span>
                <span style={{fontSize:'0.8rem', color:'#888'}}>Showing top 100 offers</span>
            </div>
            
            <div style={styles.tableWrapper}>
                <table style={styles.table}>
                    <thead>
                        <tr>
                            <th style={{...styles.th, width:'50px'}}>#</th>
                            <th style={styles.th}>Seller</th>
                            <th style={styles.th}>Ratio (1¥)</th>
                            <th style={styles.th}>Min Qty</th>
                            <th style={{...styles.th, textAlign:'right'}}>Price ({currencySymbol})</th>
                            <th style={{...styles.th, textAlign:'right'}}>Stock</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedBook.length === 0 && (
                            <tr><td colSpan="6" style={{padding:'20px', textAlign:'center', color:'#666'}}>No data available</td></tr>
                        )}
                        {sortedBook.slice(0, 100).map((row, i) => {
                            const isHighlight = highlightText && row.seller.toLowerCase().includes(highlightText.toLowerCase());
                            const bg = isHighlight ? 'rgba(0, 230, 118, 0.2)' : (i % 2 === 0 ? 'transparent' : '#161616');
                            
                            return (
                                <tr key={i} style={{backgroundColor: bg, transition:'0.2s'}}>
                                    <td style={{...styles.td, color:'#666'}}>{i+1}</td>
                                    <td style={{...styles.td, fontWeight:'bold', color: isHighlight ? theme.green : '#fff'}}>
                                        {row.seller}
                                    </td>
                                    <td style={styles.td}>{row.ratio || '-'}</td>
                                    <td style={styles.td}>{row.min_qty || 1}</td>
                                    <td style={{...styles.td, textAlign:'right', color: platformColor, fontWeight:'bold', fontSize:'1.1rem'}}>
                                        {formatPrice(row.unit_price, showVND)}
                                    </td>
                                    <td style={{...styles.td, textAlign:'right'}}>
                                        {row.stock}
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
      </div>
    </div>
  );
};

export default App;