import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { createChart, LineSeries } from 'lightweight-charts';
import axios from 'axios';

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
};

// --- STYLES ---
const styles = {
  app: { display: 'flex', width: '100vw', height: '100vh', backgroundColor: theme.bg, color: theme.text, overflow: 'hidden' },
  sidebar: (isOpen) => ({
    width: isOpen ? '300px' : '0px',
    backgroundColor: theme.sidebar,
    padding: isOpen ? '20px' : '20px 0px',
    display: 'flex', flexDirection: 'column', 
    gap: '12px',
    borderRight: '1px solid ' + theme.border, 
    height: '100%', overflowY: 'auto', overflowX: 'hidden', 
    flexShrink: 0, boxSizing: 'border-box',
    transition: 'all 0.3s ease', 
    opacity: isOpen ? 1 : 0, visibility: isOpen ? 'visible' : 'hidden'
  }),
  main: { 
    flex: 1, padding: '2rem 3rem', height: '100%', overflowY: 'auto', position: 'relative',
    transition: 'all 0.3s ease'
  },
  toggleBtn: {
    position: 'sticky', top: '0', left: '0', zIndex: 100, 
    backgroundColor: theme.card, border: `1px solid ${theme.border}`,
    color: theme.text, width: '40px', height: '40px', borderRadius: '8px',
    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '1.2rem', boxShadow: '0 2px 5px rgba(0,0,0,0.2)', marginBottom: '10px'
  },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '30px', marginTop: '10px' },
  kpiCard: { backgroundColor: theme.card, padding: '15px', borderRadius: '8px', borderLeft: `4px solid ${theme.cyan}`, boxShadow: '0 2px 5px rgba(0,0,0,0.2)' },
  kpiLabel: { fontSize: '0.8rem', color: theme.textSec, textTransform: 'uppercase' },
  kpiValue: { fontSize: '1.8rem', fontWeight: 'bold', margin: '5px 0' },
  kpiSub: { fontSize: '0.8rem', color: '#00e676' },
  chartContainer: { backgroundColor: theme.card, padding: '0', borderRadius: '8px', marginBottom: '30px', border: '1px solid #333', position: 'relative', overflow: 'hidden' },
  tableWrapper: { backgroundColor: theme.card, borderRadius: '8px', overflow: 'hidden', border: '1px solid #333' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '14px' },
  th: { textAlign: 'left', padding: '12px 15px', borderBottom: '1px solid #444', color: theme.textSec, backgroundColor: '#2b2b2b' },
  td: { padding: '10px 15px', borderBottom: '1px solid #333' },
  inputGroup: { marginBottom: '5px' },
  inputLabel: { color: theme.textSec, fontSize: '12px', marginBottom: '4px', display: 'block' },
  input: { width: '100%', padding: '8px', borderRadius: '5px', border: '1px solid #555', backgroundColor: '#0e1117', color: 'white', outline: 'none', boxSizing: 'border-box', fontSize: '13px' },
  searchContainer: { position: 'relative', width: '100%' },
  searchResults: { position: 'absolute', top: '100%', left: 0, right: 0, backgroundColor: '#262730', border: '1px solid #555', borderRadius: '0 0 5px 5px', zIndex: 100, maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' },
  searchItem: { padding: '8px 10px', cursor: 'pointer', borderBottom: '1px solid #333', fontSize: '13px', transition: 'background 0.2s' },
  tagContainer: { display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' },
  tagItem: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#1e1e1e', padding: '6px 10px', borderRadius: '6px', border: '1px solid #444' },
  tagLeft: { display: 'flex', alignItems: 'center', gap: '10px' },
  colorPickerWrapper: { width: '14px', height: '14px', borderRadius: '50%', overflow: 'hidden', border: '1px solid #fff', cursor: 'pointer', position: 'relative' },
  colorInput: { position: 'absolute', top: '-50%', left: '-50%', width: '200%', height: '200%', opacity: 0, cursor: 'pointer' },
  removeBtn: { cursor: 'pointer', color: '#ff4b4b', fontWeight: 'bold', fontSize: '16px', padding: '0 5px', lineHeight: '1' },
  legend: {
    position: 'absolute', top: '10px', left: '10px', zIndex: 20,
    fontFamily: 'monospace', fontSize: '12px', color: '#fff',
    backgroundColor: 'rgba(30, 30, 30, 0.8)', 
    padding: '8px', borderRadius: '4px', pointerEvents: 'none'
  }
};

const COLORS = ['#e91e63', '#9c27b0', '#673ab7', '#2196f3', '#00bcd4', '#4caf50', '#ffeb3b', '#ff9800', '#ff5722', '#795548'];

const PercentageBadge = ({ value }) => {
    if (value === undefined || value === null) return null;
    const isPositive = value > 0;
    const isZero = value === 0;
    const color = isZero ? '#888' : (isPositive ? '#00e676' : '#ff4b4b');
    const arrow = isZero ? '' : (isPositive ? '▲' : '▼');
    return (
        <span style={{ 
            color: color, fontSize: '0.85rem', fontWeight: 'bold',
            backgroundColor: isZero ? 'rgba(136,136,136,0.1)' : (isPositive ? 'rgba(0, 230, 118, 0.1)' : 'rgba(255, 75, 75, 0.1)'),
            padding: '2px 6px', borderRadius: '4px', display: 'inline-block'
        }}>
            {arrow} {Math.abs(value).toFixed(2)}%
        </span>
    );
};

const formatLocalTime = (ts) => {
    if (!ts || ts === '--:--') return '--:--';
    try {
        const date = new Date(ts.endsWith('Z') ? ts : ts + 'Z'); 
        if (isNaN(date.getTime())) return ts.split(' ')[1] || ts; 
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }); 
    } catch(e) { return ts; }
};

const App = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [availableItems, setAvailableItems] = useState(() => {
      try {
          const saved = JSON.parse(localStorage.getItem('sniper_items')) || [];
          return Array.from(new Set(['PoE 1 Divine Orb', 'PoE 2 Divine Orb', ...saved]));
      } catch { return ['PoE 1 Divine Orb', 'PoE 2 Divine Orb']; }
  });
  const [selectedItem, setSelectedItem] = useState(() => localStorage.getItem('sniper_selected') || 'PoE 1 Divine Orb');
  const selectedItemRef = useRef(selectedItem); 
  const [marketData, setMarketData] = useState({ raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0, timestamp: '--:--', order_book: [], item_name: 'Loading...' });
  const [prevOrderBook, setPrevOrderBook] = useState({});
  const [marketVelocity, setMarketVelocity] = useState(0);
  const [salesLog, setSalesLog] = useState([]);
  const [connectionStatus, setStatus] = useState("Connecting...");
  const [timeWindow, setTimeWindow] = useState(24);
  
  const [selectedCompetitors, setSelectedCompetitors] = useState(() => {
    try { return JSON.parse(localStorage.getItem('sniper_competitors')) || []; } catch { return []; }
  });
  
  const [competitorColors, setCompetitorColors] = useState(() => {
    try { return JSON.parse(localStorage.getItem('sniper_comp_colors')) || {}; } catch { return {}; }
  });

  const [searchTerm, setSearchTerm] = useState("");
  const [showResults, setShowResults] = useState(false);

  const mainSectionRef = useRef(null);
  const mainChartContainerRef = useRef(null);
  const compChartContainerRef = useRef(null);
  const mainChartInstance = useRef(null);
  const compChartInstance = useRef(null);
  const seriesRef = useRef({}); 
  const competitorColorsRef = useRef(competitorColors);
  const mainLegendRef = useRef(null);
  const compLegendRef = useRef(null);

  useEffect(() => { competitorColorsRef.current = competitorColors; }, [competitorColors]);

  useEffect(() => {
      localStorage.setItem('sniper_competitors', JSON.stringify(selectedCompetitors));
  }, [selectedCompetitors]);

  useEffect(() => {
      localStorage.setItem('sniper_comp_colors', JSON.stringify(competitorColors));
  }, [competitorColors]);

  const fetchChartHistory = useCallback(async (item, hours) => {
      if (!item) return;
      try {
          const res = await axios.get(`/api/history?item_name=${encodeURIComponent(item)}&hours=${hours}`);
          const h = res.data.history;
          if (h && h.length > 0 && mainChartInstance.current && seriesRef.current.price) {
              seriesRef.current.price.setData(h.map(x => ({ time: x.time, value: x.trusted_floor })));
              seriesRef.current.raw.setData(h.map(x => ({ time: x.time, value: x.raw_floor })));
              mainChartInstance.current.timeScale().fitContent();
          }
      } catch (e) { console.error("History Error", e); }
  }, []);

  const fetchSnapshot = useCallback(async (item, hours) => {
      if (!item) return;
      try {
          const res = await axios.get(`/api/snapshot?item_name=${encodeURIComponent(item)}&hours=${hours}`);
          const data = res.data; 
          if (data && data.order_book) {
              setMarketData({ 
                  ...data, item_name: item, timestamp: data.timestamp,
                  raw_change: data.raw_change || 0, trusted_change: data.trusted_change || 0
              });
              if (data.recent_sales) {
                  setSalesLog(data.recent_sales);
                  const totalPastVol = data.recent_sales.reduce((acc, curr) => acc + curr.amount, 0);
                  setMarketVelocity(totalPastVol);
              } else {
                  setSalesLog([]); setMarketVelocity(0);
              }
              const map = {};
              data.order_book.forEach(i => map[i.seller] = i.sold_total);
              setPrevOrderBook(map);
          }
      } catch (e) { console.error("Snapshot Error", e); }
  }, []);

  const fetchCompetitorHistory = useCallback(async (item, competitors, hours) => {
      if (!item || competitors.length === 0 || !compChartInstance.current) return;
      try {
          const res = await axios.get(`/api/competitor_history?item_name=${item}&sellers=${competitors.join(',')}&hours=${hours}`);
          const data = res.data.data;
            
          if (seriesRef.current.competitors) {
              Object.values(seriesRef.current.competitors).forEach(s => compChartInstance.current.removeSeries(s));
          }
          seriesRef.current.competitors = {};

          competitors.forEach((seller, idx) => {
              if (data[seller]) {
                  const savedColor = competitorColorsRef.current[seller];
                  const color = savedColor || COLORS[idx % COLORS.length];
                  if (!savedColor) setCompetitorColors(prev => ({...prev, [seller]: color}));

                  const s = compChartInstance.current.addSeries(LineSeries, { 
                      color, lineWidth: 2, 
                      priceFormat: { type: 'price', precision: 6, minMove: 0.000001 },
                      lastValueVisible: false, 
                      priceLineVisible: true
                  });
                  s.setData(data[seller].map(p => ({ time: p.time, value: p.value })));
                  seriesRef.current.competitors[seller] = s;
              }
          });
          compChartInstance.current.timeScale().fitContent();
      } catch (e) { console.error("Comp Error", e); }
  }, []); 

  // --- CHARTS CONFIG ---
  const chartOptions = {
    layout: { background: { type: 'solid', color: theme.card }, textColor: theme.textSec },
    grid: { vertLines: { color: '#333' }, horzLines: { color: '#333' } },
    crosshair: {
        vertLine: { labelVisible: true }, 
        horzLine: { labelVisible: true }, 
    },
    timeScale: { 
        timeVisible: true, secondsVisible: true,
        rightOffset: 0, fixRightEdge: true, lockVisibleTimeRangeOnResize: true,
        tickMarkFormatter: (time) => new Date(time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
    },
    localization: {
        timeFormatter: (timestamp) => new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
    }
  };

  const initMainChart = () => {
    if (!mainChartContainerRef.current) return;
    const chart = createChart(mainChartContainerRef.current, { ...chartOptions, width: mainChartContainerRef.current.clientWidth, height: 350 });
    
    const sRaw = chart.addSeries(LineSeries, { 
        color: '#555', lineWidth: 1, lineStyle: 2, 
        priceFormat: { type: 'price', precision: 6, minMove: 0.000001 },
        lastValueVisible: false, 
        priceLineVisible: true 
    });
    
    const sPrice = chart.addSeries(LineSeries, { 
        color: theme.cyan, lineWidth: 3, 
        priceFormat: { type: 'price', precision: 6, minMove: 0.000001 },
        lastValueVisible: false, 
        priceLineVisible: true
    });
    
    mainChartInstance.current = chart;
    seriesRef.current.raw = sRaw;
    seriesRef.current.price = sPrice;

    const updateMainLegend = (param) => {
        const validCrosshairPoint = !(param === undefined || param.time === undefined || param.point.x < 0 || param.point.y < 0);
        let legendHtml = '';
        const getVal = (series) => {
            if (!series) return 'N/A';
            const price = validCrosshairPoint ? param.seriesData.get(series) : series.data().slice(-1)[0];
            return price ? `$${price.value.toFixed(6)}` : 'N/A';
        };
        legendHtml += `<div style="color: ${theme.cyan}; margin-bottom: 4px">Trusted Floor: <b>${getVal(sPrice)}</b></div>`;
        legendHtml += `<div style="color: #888;">Raw Floor: <b>${getVal(sRaw)}</b></div>`;
        if (mainLegendRef.current) mainLegendRef.current.innerHTML = legendHtml;
    };
    chart.subscribeCrosshairMove(updateMainLegend);
    updateMainLegend(undefined);
    return chart;
  };

  const initCompChart = () => {
    if (!compChartContainerRef.current) return;
    const chart = createChart(compChartContainerRef.current, { ...chartOptions, width: compChartContainerRef.current.clientWidth, height: 350 });
    compChartInstance.current = chart;
    seriesRef.current.competitors = {}; 

    const updateCompLegend = (param) => {
        const validCrosshairPoint = !(param === undefined || param.time === undefined || param.point.x < 0 || param.point.y < 0);
        let legendHtml = '';
        if (seriesRef.current.competitors) {
            Object.entries(seriesRef.current.competitors).forEach(([name, series]) => {
                const color = competitorColorsRef.current[name] || '#fff';
                let priceVal = 'N/A';
                if (validCrosshairPoint) {
                    const d = param.seriesData.get(series);
                    if (d) priceVal = `$${d.value.toFixed(6)}`;
                } else {
                    const data = series.data();
                    if (data.length > 0) priceVal = `$${data[data.length - 1].value.toFixed(6)}`;
                }
                if (priceVal !== 'N/A') {
                    legendHtml += `<div style="display: flex; align-items: center; margin-bottom: 4px;">
                        <span style="width: 8px; height: 8px; background-color: ${color}; border-radius: 50%; margin-right: 6px;"></span>
                        <span style="color: #ddd; margin-right: 6px;">${name}:</span>
                        <b style="color: #fff;">${priceVal}</b>
                    </div>`;
                }
            });
        }
        if (compLegendRef.current) compLegendRef.current.innerHTML = legendHtml;
    };
    chart.subscribeCrosshairMove(updateCompLegend);
    return chart;
  };

  useEffect(() => {
    const mChart = initMainChart();
    const cChart = initCompChart();

    if (selectedItem) {
        fetchChartHistory(selectedItem, timeWindow);
        fetchSnapshot(selectedItem, timeWindow);
    }
    
    const handleResize = () => {
        requestAnimationFrame(() => {
            if(mainChartInstance.current && mainChartContainerRef.current) {
                mainChartInstance.current.applyOptions({ width: mainChartContainerRef.current.clientWidth });
            }
            if(compChartInstance.current && compChartContainerRef.current) {
                compChartInstance.current.applyOptions({ width: compChartContainerRef.current.clientWidth });
            }
        });
    };

    const resizeObserver = new ResizeObserver(handleResize);
    if (mainSectionRef.current) resizeObserver.observe(mainSectionRef.current);

    return () => { 
        resizeObserver.disconnect();
        if(mChart) mChart.remove(); 
        if(cChart) cChart.remove(); 
    };
  }, []);

  useEffect(() => {
      if (selectedItem) {
          fetchChartHistory(selectedItem, timeWindow);
          fetchSnapshot(selectedItem, timeWindow);
          if (selectedCompetitors.length > 0) fetchCompetitorHistory(selectedItem, selectedCompetitors, timeWindow);
      }
  }, [selectedItem, timeWindow, selectedCompetitors]);

  useEffect(() => {
      axios.get('/api/items').then(res => {
          if (res.data && res.data.items) {
              setAvailableItems(prev => Array.from(new Set(['PoE 1 Divine Orb', 'PoE 2 Divine Orb', ...prev, ...res.data.items])));
          }
      }).catch(() => {});
  }, []);

  // --- [PHẦN QUAN TRỌNG] CẬP NHẬT LOGIC WEBSOCKET Ở ĐÂY ---
  useEffect(() => {
    let ws = null;
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host; 
        ws = new WebSocket(`${protocol}//${host}/ws`);
        ws.onopen = () => setStatus("🟢 Live");
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'UPDATE') {
                const incomingItem = data.item_name;
                setAvailableItems(prev => prev.includes(incomingItem) ? prev : [...prev, incomingItem]);
                
                if (!selectedItemRef.current) {
                    setSelectedItem(incomingItem);
                    selectedItemRef.current = incomingItem;
                    fetchChartHistory(incomingItem, timeWindow);
                    fetchSnapshot(incomingItem, timeWindow);
                }
                if (selectedItemRef.current !== incomingItem) return;

                const ts = new Date(data.timestamp).getTime() / 1000; 
                let sessionVol = 0;
                let newSales = [];
                
                // Cập nhật OrderBook và tính Velocity
                data.order_book.forEach(item => {
                    const prev = prevOrderBook[item.seller] || item.sold_total;
                    const diff = item.sold_total - prev;
                    if (diff > 0) {
                        sessionVol += diff;
                        newSales.push({ seller: item.seller, amount: diff, time: data.timestamp });
                    }
                });
                if (sessionVol > 0) {
                    setMarketVelocity(prev => prev + sessionVol);
                    setSalesLog(prev => [...newSales, ...prev].slice(0, 50));
                }
                const map = {};
                data.order_book.forEach(i => map[i.seller] = i.sold_total);
                setPrevOrderBook(map);
                
                // Cập nhật State OrderBook (Đồng bộ OrderBook Table)
                setMarketData(prev => ({...prev, ...data, item_name: data.item_name})); 

                // 1. Cập nhật Biểu đồ CHÍNH
                if (mainChartInstance.current && seriesRef.current.price) {
                    seriesRef.current.price.update({ time: ts, value: data.trusted_floor });
                    seriesRef.current.raw.update({ time: ts, value: data.raw_floor });
                }

                // 2. [MỚI] Cập nhật Biểu đồ ĐỐI THỦ (Competitor Chart)
                if (compChartInstance.current && seriesRef.current.competitors) {
                    data.order_book.forEach(offer => {
                        // Kiểm tra xem đối thủ này có đang được hiển thị trên biểu đồ không
                        const competitorSeries = seriesRef.current.competitors[offer.seller];
                        if (competitorSeries) {
                            // Cập nhật giá mới nhất vào chuỗi (series) của đối thủ đó
                            competitorSeries.update({
                                time: ts,
                                value: offer.unit_price
                            });
                        }
                    });
                }
            }
        };
    } catch(e) {}
    return () => { if(ws) ws.close(); };
  }, [prevOrderBook, timeWindow]);

  const handleItemChange = (e) => {
      const newItem = e.target.value;
      setSelectedItem(newItem);
      selectedItemRef.current = newItem;
      localStorage.setItem('sniper_selected', newItem);
      setMarketData({ raw_floor: 0, trusted_floor: 0, timestamp: 'Loading...', order_book: [], item_name: newItem });
      setPrevOrderBook({});
      fetchChartHistory(newItem, timeWindow);
      fetchSnapshot(newItem, timeWindow);
  };

  const handleAddCompetitor = (seller) => {
      if (!selectedCompetitors.includes(seller)) {
          setSelectedCompetitors(prev => [...prev, seller]);
          if (!competitorColors[seller]) {
              const nextColor = COLORS[selectedCompetitors.length % COLORS.length];
              const newColors = {...competitorColors, [seller]: nextColor};
              setCompetitorColors(newColors);
              competitorColorsRef.current = newColors;
          }
      }
      setSearchTerm("");
      setShowResults(false);
  };

  const handleRemoveCompetitor = (seller) => {
      setSelectedCompetitors(prev => prev.filter(s => s !== seller));
      if (seriesRef.current.competitors && seriesRef.current.competitors[seller] && compChartInstance.current) {
          compChartInstance.current.removeSeries(seriesRef.current.competitors[seller]);
          delete seriesRef.current.competitors[seller];
      }
  };

  const handleColorChange = (seller, newColor) => {
      const newColors = {...competitorColors, [seller]: newColor};
      setCompetitorColors(newColors);
      competitorColorsRef.current = newColors;
      if (seriesRef.current.competitors && seriesRef.current.competitors[seller]) {
          seriesRef.current.competitors[seller].applyOptions({ color: newColor });
      }
  };

  const sortedBook = useMemo(() => {
      return [...marketData.order_book].sort((a,b) => a.unit_price - b.unit_price);
  }, [marketData.order_book]);

  const leaderboard = useMemo(() => {
    const board = {}; salesLog.forEach(log => { if (!board[log.seller]) board[log.seller] = 0; board[log.seller] += log.amount; });
    return Object.entries(board).sort((a,b) => b[1] - a[1]).map(([s, a], i) => ({ rank: i+1, seller: s, amount: a }));
  }, [salesLog]);

  const uniqueSellers = useMemo(() => {
      return [...new Set(marketData.order_book.map(i => i.seller))].sort();
  }, [marketData.order_book]);

  const filteredSellers = uniqueSellers.filter(s => s.toLowerCase().includes(searchTerm.toLowerCase()));
  const getTimeLabel = (val) => val < 1 ? `${val * 60} Min` : `${val} Hr`;

  return (
    <div style={styles.app}>
      <div style={styles.sidebar(isSidebarOpen)}>
        <h2 style={{fontSize:'1.2rem', fontWeight:'bold', marginBottom:'10px', opacity: isSidebarOpen ? 1 : 0}}>🦅 G2G Config</h2>
        
        <div style={styles.inputGroup}>
            <label style={styles.inputLabel}>Item Selection</label>
            <select style={styles.input} value={selectedItem || ''} onChange={handleItemChange}>
                {availableItems.length === 0 && !selectedItem && <option value="">Waiting...</option>}
                {selectedItem && !availableItems.includes(selectedItem) && <option value={selectedItem}>{selectedItem}</option>}
                {availableItems.map(item => (<option key={item} value={item}>{item}</option>))}
            </select>
        </div>
        
        <div style={styles.inputGroup}>
            <label style={styles.inputLabel}>Time Window</label>
            <select style={styles.input} value={timeWindow} onChange={(e) => setTimeWindow(Number(e.target.value))}>
                <option value={0.25}>15 Minutes</option>
                <option value={0.5}>30 Minutes</option>
                <option value={1}>1 Hour</option>
                <option value={4}>4 Hours</option>
                <option value={12}>12 Hours</option>
                <option value={24}>24 Hours</option>
            </select>
        </div>

        <div style={{flex: 1, display: 'flex', flexDirection: 'column'}}>
            <label style={styles.inputLabel}>Competitors</label>
            <div style={styles.searchContainer}>
                <input style={styles.input} placeholder="Search..." value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); setShowResults(true); }}
                    onFocus={() => setShowResults(true)}
                    onBlur={() => setTimeout(() => setShowResults(false), 200)} />
                {showResults && searchTerm && (
                    <div style={styles.searchResults}>
                        {filteredSellers.length > 0 ? filteredSellers.map(seller => (
                            <div key={seller} style={styles.searchItem} onMouseDown={() => handleAddCompetitor(seller)}> {seller} </div>
                        )) : <div style={{padding:'10px', color:'#777', fontSize:'13px'}}>No matches</div>}
                    </div>
                )}
            </div>
            <div style={styles.tagContainer}>
                {selectedCompetitors.map((seller) => (
                    <div key={seller} style={styles.tagItem}>
                        <div style={styles.tagLeft}>
                            <div style={{...styles.colorPickerWrapper, backgroundColor: competitorColors[seller] || '#fff'}}>
                                <input type="color" style={styles.colorInput} value={competitorColors[seller] || '#ffffff'} onChange={(e) => handleColorChange(seller, e.target.value)} />
                            </div>
                            <span style={{fontSize:'13px'}}>{seller}</span>
                        </div>
                        <span style={styles.removeBtn} onClick={() => handleRemoveCompetitor(seller)}>×</span>
                    </div>
                ))}
            </div>
        </div>
        <div style={{marginTop:'auto', padding:'10px', backgroundColor:'#1e1e1e', borderRadius:'5px', fontSize:'12px', opacity: isSidebarOpen ? 1 : 0}}>
            Status: <span style={{color: connectionStatus.includes("Live") ? '#00e676' : '#ff4b4b'}}>{connectionStatus}</span>
        </div>
      </div>

      <div ref={mainSectionRef} style={styles.main}>
        <button style={styles.toggleBtn} onClick={() => setIsSidebarOpen(!isSidebarOpen)} title="Toggle Sidebar">
            {isSidebarOpen ? '❮' : '☰'}
        </button>

        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'10px'}}>
             <h1 style={{fontSize:'2rem', margin:0}}>🦅 {selectedItem || 'Market'} Overview ({getTimeLabel(timeWindow)})</h1>
        </div>
        
        <div style={styles.kpiGrid}>
            <div style={styles.kpiCard}>
                <div style={styles.kpiLabel}>Trusted Floor</div>
                <div style={{...styles.kpiValue, color: theme.cyan}}>${marketData.trusted_floor.toFixed(6)}</div>
                <div style={{ marginTop: '4px' }}>
                    <PercentageBadge value={marketData.trusted_change} />
                </div>
            </div>

            <div style={styles.kpiCard}>
                <div style={styles.kpiLabel}>Raw Floor</div>
                <div style={styles.kpiValue}>${marketData.raw_floor.toFixed(6)}</div>
                <div style={{ marginTop: '4px' }}>
                    <PercentageBadge value={marketData.raw_change} />
                </div>
            </div>

            <div style={styles.kpiCard}>
                <div style={styles.kpiLabel}>Velocity</div>
                <div style={styles.kpiValue}>{marketVelocity} <span style={{fontSize:'1rem'}}>sold</span></div>
                <div style={styles.kpiSub}>{getTimeLabel(timeWindow)} Growth</div>
            </div>

            <div style={styles.kpiCard}>
                <div style={styles.kpiLabel}>Update</div>
                <div style={styles.kpiValue}>{formatLocalTime(marketData.timestamp)}</div>
            </div>
        </div>

        <h3 style={{marginBottom:'10px'}}>📊 Market Overview</h3>
        <div style={styles.chartContainer}>
            <div ref={mainLegendRef} style={styles.legend}></div>
            <div ref={mainChartContainerRef} style={{width:'100%', height:'350px'}} />
        </div>
        
        <h3 style={{marginBottom:'10px'}}>⚔️ Competitor Analysis</h3>
        <div style={styles.chartContainer}>
            <div ref={compLegendRef} style={styles.legend}></div>
            <div ref={compChartContainerRef} style={{width:'100%', height:'350px'}} />
        </div>

        <div style={{display:'flex', gap:'20px', flexWrap:'wrap'}}>
            <div style={{flex:1, minWidth:'300px'}}>
                <h3 style={{marginBottom:'10px'}}>🏆 {getTimeLabel(timeWindow)} Growth</h3>
                <div style={styles.tableWrapper}>
                    <div style={{maxHeight:'500px', overflowY:'auto'}}>
                    <table style={styles.table}>
                        <thead><tr><th style={styles.th}>#</th><th style={styles.th}>Seller</th><th style={styles.th}>Sold</th></tr></thead>
                        <tbody>
                            {leaderboard.length === 0 && <tr><td colSpan="3" style={{padding:'20px', textAlign:'center', color:'#666'}}>No data in this window</td></tr>}
                            {leaderboard.map(r => (
                                <tr key={r.seller} style={selectedCompetitors.includes(r.seller) ? {backgroundColor: competitorColors[r.seller] || theme.cyan, color:'black', fontWeight:'bold'} : {}}>
                                    <td style={styles.td}>{r.rank}</td><td style={styles.td}>{r.seller}</td><td style={styles.td}>+{r.amount}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    </div>
                </div>
            </div>

            <div style={{flex:1, minWidth:'300px'}}>
                <h3 style={{marginBottom:'10px'}}>📖 Order Book</h3>
                <div style={styles.tableWrapper}>
                    <div style={{maxHeight:'500px', overflowY:'auto'}}>
                    <table style={styles.table}>
                        <thead><tr><th style={styles.th}>#</th><th style={styles.th}>Seller</th><th style={styles.th}>S</th><th style={styles.th}>Price</th><th style={styles.th}>Sold</th></tr></thead>
                        <tbody>
                            {sortedBook.length === 0 && <tr><td colSpan="5" style={{padding:'20px', textAlign:'center', color:'#666'}}>Loading snapshot...</td></tr>}
                            {sortedBook.slice(0, 50).map((r, i) => {
                                const isSel = selectedCompetitors.includes(r.seller);
                                const rowStyle = isSel ? {backgroundColor: competitorColors[r.seller] || theme.cyan, color:'black', fontWeight:'bold'} : {backgroundColor: i%2===0?'transparent':'#232323'};
                                return (
                                    <tr key={i} style={rowStyle}>
                                        <td style={styles.td}>{i+1}</td>
                                        <td style={styles.td}>{r.seller}</td>
                                        <td style={styles.td}>{r.online==='Online'?'🟢':'⚪'}</td>
                                        <td style={{...styles.td, color: isSel?'black':theme.cyan}}>${r.unit_price.toFixed(6)}</td>
                                        <td style={styles.td}>{r.sold_total}</td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default App;