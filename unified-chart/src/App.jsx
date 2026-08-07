import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { createChart, LineSeries } from 'lightweight-charts';
import axios from 'axios';

// --- CONFIG AND API ENDPOINTS ---
const EXCHANGE_RATE_API = "https://open.er-api.com/v6/latest/USD";

const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

const DD373_API_BASE = isLocal ? "http://localhost:8000" : "https://dd373.gegechart.xyz";
const ELDORADO_API_BASE = isLocal ? "http://localhost:8001" : "https://eldo.gegechart.xyz";
const G2G_API_BASE = isLocal ? "http://localhost:8002" : "https://g2g.gegechart.xyz";
const QIANDAO_API_BASE = isLocal ? "http://localhost:8003" : "https://qiandao.gegechart.xyz";

const getWsUrl = (port, domain) => isLocal ? `ws://localhost:${port}/ws` : `wss://${domain}/ws`;

const theme = {
    bg: '#0a0d14',
    sidebar: '#111420',
    card: '#171b2a',
    text: '#f1f3f9',
    textSec: '#8a92b2',
    cyan: '#ff3b30', // Red (G2G)
    green: '#00e676',
    danger: '#ff1744',
    gold: '#007aff', // Blue (DD373)
    purple: '#d500f9',
    qiandao: '#00e676', // Green
    border: '#22283f',
    tableOdd: '#1c2134'
};

const styles = {
    app: { display: 'flex', width: '100vw', height: '100vh', backgroundColor: theme.bg, color: theme.text, overflow: 'hidden', fontFamily: 'system-ui, -apple-system, sans-serif' },

    sidebar: (isOpen) => ({
        width: isOpen ? '320px' : '0px',
        backgroundColor: theme.sidebar,
        padding: isOpen ? '20px' : '20px 0px',
        display: 'flex', flexDirection: 'column',
        gap: '15px',
        borderRight: `1px solid ${theme.border}`,
        height: '100%', overflowY: 'auto', overflowX: 'hidden', flexShrink: 0,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)', opacity: isOpen ? 1 : 0,
        visibility: isOpen ? 'visible' : 'hidden',
        boxSizing: 'border-box'
    }),

    main: {
        flex: 1, padding: '20px 30px', height: '100%', overflowY: 'auto', overflowX: 'auto',
        display: 'flex', flexDirection: 'column', gap: '20px',
        width: '100%', minWidth: 0, position: 'relative', boxSizing: 'border-box'
    },

    toggleBtn: {
        backgroundColor: theme.card, border: `1px solid ${theme.border}`,
        color: theme.text, width: '36px', height: '36px', borderRadius: '6px',
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginRight: '15px', flexShrink: 0, transition: 'all 0.2s',
        boxShadow: '0 4px 10px rgba(0,0,0,0.3)'
    },

    sectionHeader: {
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        paddingBottom: '8px', borderBottom: `2px solid ${theme.border}`
    },

    kpiGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px' },

    kpiCard: (borderColor) => ({
        backgroundColor: theme.card, padding: '12px 15px', borderRadius: '8px',
        borderLeft: `4px solid ${borderColor}`, boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        transition: 'transform 0.2s',
        cursor: 'default'
    }),
    kpiLabel: { fontSize: '0.7rem', color: theme.textSec, textTransform: 'uppercase', marginBottom: '4px', letterSpacing: '0.5px' },
    kpiValue: { fontSize: '1.25rem', fontWeight: 'bold', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },

    chartSection: {
        backgroundColor: theme.card, borderRadius: '8px', border: `1px solid ${theme.border}`,
        position: 'relative', overflow: 'hidden', padding: '10px',
        minHeight: '320px', height: '350px',
        display: 'flex', flexDirection: 'column',
        width: '100%'
    },

    tablesContainer: {
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '15px',
        flexShrink: 0,
        alignItems: 'start',
        minHeight: '400px',
        marginTop: '10px',
        width: '100%'
    },

    tableCard: {
        backgroundColor: theme.card, borderRadius: '8px', border: `1px solid ${theme.border}`,
        display: 'flex', flexDirection: 'column', overflow: 'hidden', height: 'auto'
    },
    tableHeader: {
        padding: '12px 15px', borderBottom: `1px solid ${theme.border}`, fontWeight: 'bold',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.02)'
    },
    tableWrapper: { flex: 1, overflowY: 'visible' },
    table: { width: '100%', borderCollapse: 'collapse', fontSize: '14px' },
    th: {
        textAlign: 'left', padding: '12px 12px', borderBottom: `1px solid ${theme.border}`,
        color: theme.textSec, backgroundColor: '#141825', position: 'sticky', top: 0, zIndex: 10,
        whiteSpace: 'nowrap'
    },
    td: { padding: '10px 12px', borderBottom: `1px solid ${theme.border}`, height: '52px' },

    currencyBtn: {
        padding: '6px 14px', fontSize: '0.85rem', fontWeight: 'bold',
        backgroundColor: '#1c2134', border: `1px solid ${theme.border}`, color: '#fff',
        borderRadius: '6px', cursor: 'pointer', transition: 'all 0.2s',
        display: 'inline-flex', alignItems: 'center', gap: '6px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
    },

    inputGroup: { display: 'flex', flexDirection: 'column', gap: '5px' },
    inputLabel: { color: theme.textSec, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' },
    input: {
        width: '100%', padding: '8px 10px', boxSizing: 'border-box',
        borderRadius: '6px', border: `1px solid ${theme.border}`, backgroundColor: '#090b11',
        color: 'white', fontSize: '13px', outline: 'none', transition: 'border-color 0.2s'
    },

    legend: { position: 'absolute', top: '10px', left: '10px', zIndex: 20, fontSize: '11px', color: '#fff', backgroundColor: 'rgba(15,18,30,0.85)', padding: '6px 10px', borderRadius: '4px', pointerEvents: 'none', border: `1px solid ${theme.border}` },
    statusBadge: (isLive) => ({
        display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '11px',
        backgroundColor: isLive ? 'rgba(0,230,118,0.1)' : 'rgba(255,23,68,0.1)',
        color: isLive ? theme.green : theme.danger,
        padding: '2px 8px', borderRadius: '20px', fontWeight: 'bold'
    }),
    statusDot: (isLive) => ({
        width: '6px', height: '6px', borderRadius: '50%',
        backgroundColor: isLive ? theme.green : theme.danger,
        boxShadow: isLive ? `0 0 8px ${theme.green}` : 'none'
    })
};

const COLORS = ['#e91e63', '#9c27b0', '#673ab7', '#2196f3', '#00bcd4', '#4caf50', '#ffeb3b', '#ff9800', '#ff5722', '#795548'];

const PercentageBadge = ({ value }) => {
    if (value === undefined || value === null) return null;
    const color = value === 0 ? '#888' : (value > 0 ? theme.green : theme.danger);
    return (
        <span style={{ color, fontSize: '0.75rem', fontWeight: 'bold', marginLeft: '5px' }}>
            {value > 0 ? '▲' : (value < 0 ? '▼' : '')} {Math.abs(value).toFixed(2)}%
        </span>
    );
};

const padOrderBook = (book, targetLength = 10) => {
    const padded = [...(book || [])];
    while (padded.length < targetLength) {
        padded.push(null);
    }
    return padded.slice(0, targetLength);
};

const Pagination = ({ currentPage, totalItems, onPageChange }) => {
    const totalPages = Math.max(1, Math.ceil(Math.min(40, totalItems) / 10));
    return (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '10px', gap: '8px', borderTop: '1px solid rgba(255,255,255,0.1)', backgroundColor: '#141825' }}>
            {[...Array(totalPages)].map((_, i) => (
                <button
                    key={i}
                    onClick={() => onPageChange(i + 1)}
                    style={{
                        backgroundColor: currentPage === i + 1 ? '#007aff' : '#1c2134',
                        color: currentPage === i + 1 ? '#fff' : '#8e8e93',
                        border: `1px solid ${currentPage === i + 1 ? '#007aff' : 'rgba(255,255,255,0.1)'}`,
                        borderRadius: '4px', padding: '4px 12px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold', transition: 'all 0.2s'
                    }}
                >
                    {i + 1}
                </button>
            ))}
        </div>
    );
};

const LoginScreen = ({ onLogin }) => {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const handleLogin = (e) => {
        e.preventDefault();
        // Tài khoản cố định (Chỉ cần nhập mật khẩu)
        if (password === 'Gegeteam!987654321') {
            localStorage.setItem('chart_auth', 'true');
            onLogin();
        } else {
            setError('Sai mật khẩu!');
        }
    };
    return (
        <div style={{ ...styles.app, justifyContent: 'center', alignItems: 'center' }}>
            <div style={{ backgroundColor: theme.card, padding: '30px', borderRadius: '12px', border: `1px solid ${theme.border}`, width: '300px', textAlign: 'center', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
                <h2 style={{ marginBottom: '20px', color: '#fff' }}>🔒 Đăng nhập hệ thống</h2>
                <form onSubmit={handleLogin}>
                    <input
                        type="password"
                        placeholder="Nhập mật khẩu truy cập..."
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        style={{ ...styles.input, marginBottom: '15px', height: '40px', fontSize: '16px', textAlign: 'center' }}
                    />
                    {error && <div style={{ color: theme.danger, marginBottom: '15px', fontSize: '13px' }}>{error}</div>}
                    <button type="submit" style={{ ...styles.currencyBtn, width: '100%', justifyContent: 'center', height: '40px', fontSize: '16px' }}>Vào xem Chart</button>
                </form>
            </div>
        </div>
    );
};

const App = () => {
    const [isLoggedIn, setIsLoggedIn] = useState(localStorage.getItem('chart_auth') === 'true');
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    if (!isLoggedIn) {
        return <LoginScreen onLogin={() => setIsLoggedIn(true)} />;
    }

    // --- UNIFIED CONTROLS ---
    const [timeWindow, setTimeWindow] = useState(24);
    const [showVND, setShowVND] = useState(false);
    const [showDD373Line, setShowDD373Line] = useState(true);
    const [showG2GLine, setShowG2GLine] = useState(true);
    const [showEldoradoLine, setShowEldoradoLine] = useState(true);
    const [showQiandaoLine, setShowQiandaoLine] = useState(true);
    const [exchangeRateUSD_VND, setExchangeRateUSD_VND] = useState(25400);
    const [exchangeRateCNY_VND, setExchangeRateCNY_VND] = useState(3650);

    // --- DD373 STATE ---
    const [availableDD373Items] = useState(['DD373 POE2 Divine Orb', 'DD373 POE1 Divine Orb']);
    const [selectedDD373Item, setDD373Item] = useState('DD373 POE2 Divine Orb');
    const selectedDD373ItemRef = useRef(selectedDD373Item);
    const [dd373MarketData, setDD373MarketData] = useState({
        raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0,
        timestamp: '--:--', order_book: [], item_name: 'Loading...', platform: 'dd373'
    });
    const [dd373Status, setDD373Status] = useState("Offline");

    // --- G2G STATE ---
    const [availableG2GItems] = useState(['PoE 1 Divine Orb', 'PoE 2 Divine Orb', 'PoE 1 Chaos']);
    const [selectedG2GItem, setG2GItem] = useState(() => {
        const saved = localStorage.getItem('unified_g2g_selected');
        return saved === 'PoE 2 Divine Orb' ? 'PoE 2 Divine Orb' : 'PoE 1 Divine Orb';
    });
    const selectedG2GItemRef = useRef(selectedG2GItem);
    const [g2gMarketData, setG2GMarketData] = useState({
        raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0,
        timestamp: '--:--', order_book: [], item_name: 'Loading...'
    });
    const [prevG2GOrderBook, setPrevG2GOrderBook] = useState({});
    const [g2gMarketVelocity, setG2GMarketVelocity] = useState(0);
    const [g2gSalesLog, setG2GSalesLog] = useState([]);
    const [g2gStatus, setG2GStatus] = useState("Offline");

    // --- ELDORADO STATE ---
    const [availableEldoradoItems] = useState(['Eldorado PoE 1 Divine Orb', 'Eldorado PoE 2 Divine Orb', 'Eldorado PoE 1 Chaos']);
    const [selectedEldoradoItem, setEldoradoItem] = useState(() => {
        const saved = localStorage.getItem('unified_eldorado_selected');
        return saved === 'Eldorado PoE 1 Divine Orb' ? 'Eldorado PoE 1 Divine Orb' : 'Eldorado PoE 2 Divine Orb';
    });
    const selectedEldoradoItemRef = useRef(selectedEldoradoItem);
    const [eldoradoMarketData, setEldoradoMarketData] = useState({
        raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0,
        timestamp: '--:--', order_book: [], item_name: 'Loading...', platform: 'eldorado'
    });
    const [eldoradoStatus, setEldoradoStatus] = useState("Offline");

    // --- QIANDAO STATE ---
    const [availableQiandaoItems] = useState(['Qiandao PoE 1 Divine Orb', 'Qiandao PoE 2 Divine Orb', 'Qiandao PoE 1 Chaos']);
    const [selectedQiandaoItem, setQiandaoItem] = useState(() => {
        const saved = localStorage.getItem('unified_qiandao_selected');
        return saved === 'Qiandao PoE 1 Divine Orb' ? 'Qiandao PoE 1 Divine Orb' : 'Qiandao PoE 2 Divine Orb';
    });
    const selectedQiandaoItemRef = useRef(selectedQiandaoItem);
    const [qiandaoMarketData, setQiandaoMarketData] = useState({
        raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0,
        timestamp: '--:--', order_book: [], item_name: 'Loading...', platform: 'qiandao'
    });
    const [qiandaoSellMarketData, setQiandaoSellMarketData] = useState({
        raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0,
        timestamp: '--:--', order_book: [], item_name: 'Loading...', platform: 'qiandao'
    });
    const [qiandaoStatus, setQiandaoStatus] = useState("Offline");

    // G2G Competitor Highlights in tables
    const [selectedCompetitors, setSelectedCompetitors] = useState(() => {
        try { return JSON.parse(localStorage.getItem('unified_g2g_competitors')) || []; } catch { return []; }
    });
    const [competitorColors, setCompetitorColors] = useState(() => {
        try { return JSON.parse(localStorage.getItem('unified_g2g_comp_colors')) || {}; } catch { return {}; }
    });
    const [searchTerm, setSearchTerm] = useState("");
    const [showResults, setShowResults] = useState(false);

    // Unified Target Selection
    const [selectedGame, setSelectedGame] = useState(() => {
        return localStorage.getItem('unified_selected_game') || 'poe1';
    });
    const [selectedCurrency, setSelectedCurrency] = useState(() => {
        return localStorage.getItem('unified_selected_currency') || 'divine';
    });

    // Dynamic currency options per game
    const currencyOptions = useMemo(() => {
        if (selectedGame === 'poe1') {
            return [
                { id: 'chaos', label: 'Chaos Orb', color: '#00bcd4' },
                { id: 'divine', label: 'Divine Orb', color: '#fbc02d' },
                { id: 'mirror', label: 'Mirror', color: '#e040fb' }
            ];
        }
        return [
            { id: 'divine', label: 'Divine Orb', color: '#fbc02d' },
            { id: 'mirror', label: 'Mirror', color: '#e040fb' }
        ];
    }, [selectedGame]);

    // Auto-switch currency when game changes if current currency is not available
    useEffect(() => {
        const validIds = currencyOptions.map(c => c.id);
        if (!validIds.includes(selectedCurrency)) {
            setSelectedCurrency('divine');
        }
    }, [selectedGame, currencyOptions]);

    // UI Search Highlights
    const [highlightDD373Text, setHighlightDD373Text] = useState("");

    // Pagination
    const [dd373Page, setDd373Page] = useState(1);
    const [g2gPage, setG2gPage] = useState(1);
    const [eldoradoPage, setEldoradoPage] = useState(1);
    const [qiandaoPage, setQiandaoPage] = useState(1);

    // --- REFS FOR UNIFIED CHART ---
    const unifiedChartContainerRef = useRef(null);
    const unifiedChartInstance = useRef(null);
    const unifiedSeriesRef = useRef({});
    const unifiedLegendRef = useRef(null);
    const competitorColorsRef = useRef(competitorColors);

    // Sync competitor colors ref
    useEffect(() => { competitorColorsRef.current = competitorColors; }, [competitorColors]);

    // Sync local storage
    useEffect(() => { if (selectedDD373Item) localStorage.setItem('unified_dd373_selected', selectedDD373Item); }, [selectedDD373Item]);
    useEffect(() => { if (selectedG2GItem) localStorage.setItem('unified_g2g_selected', selectedG2GItem); }, [selectedG2GItem]);
    useEffect(() => { if (selectedEldoradoItem) localStorage.setItem('unified_eldorado_selected', selectedEldoradoItem); }, [selectedEldoradoItem]);
    useEffect(() => { if (selectedQiandaoItem) localStorage.setItem('unified_qiandao_selected', selectedQiandaoItem); }, [selectedQiandaoItem]);
    useEffect(() => { localStorage.setItem('unified_g2g_competitors', JSON.stringify(selectedCompetitors)); }, [selectedCompetitors]);
    useEffect(() => { localStorage.setItem('unified_g2g_comp_colors', JSON.stringify(competitorColors)); }, [competitorColors]);

    // Keep refs in sync
    useEffect(() => { selectedDD373ItemRef.current = selectedDD373Item; }, [selectedDD373Item]);
    useEffect(() => { selectedG2GItemRef.current = selectedG2GItem; }, [selectedG2GItem]);
    useEffect(() => { selectedEldoradoItemRef.current = selectedEldoradoItem; }, [selectedEldoradoItem]);

    // Unified game/currency selection persistence & mapping
    useEffect(() => { localStorage.setItem('unified_selected_game', selectedGame); }, [selectedGame]);
    useEffect(() => { localStorage.setItem('unified_selected_currency', selectedCurrency); }, [selectedCurrency]);

    useEffect(() => {
        const g2gMap = {
            'poe1-divine': 'PoE 1 Divine Orb', 'poe2-divine': 'PoE 2 Divine Orb',
            'poe1-chaos': 'PoE 1 Chaos', 'poe2-mirror': 'PoE 2 Mirror',
            'poe1-mirror': 'PoE 1 Mirror'
        };
        const eldoMap = {
            'poe1-divine': 'Eldorado PoE 1 Divine Orb', 'poe2-divine': 'Eldorado PoE 2 Divine Orb',
            'poe1-chaos': 'Eldorado PoE 1 Chaos', 'poe2-mirror': 'Eldorado PoE 2 Mirror',
            'poe1-mirror': 'Eldorado PoE 1 Mirror'
        };
        const dd373Map = {
            'poe2-divine': 'DD373 POE2 Divine Orb',
            'poe1-divine': 'DD373 POE1 Divine Orb'
        };
        const qiandaoMap = {
            'poe1-divine': 'poe1 div', 'poe2-divine': 'poe2 div',
            'poe1-chaos': 'poe1 chaos', 'poe2-mirror': 'poe2 mirror'
        };
        const key = `${selectedGame}-${selectedCurrency}`;

        const newG2G = g2gMap[key] || null;
        setG2GItem(newG2G); selectedG2GItemRef.current = newG2G;
        setG2GMarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0 }));
        setPrevG2GOrderBook({}); setG2gPage(1);

        const newEldo = eldoMap[key] || null;
        setEldoradoItem(newEldo); selectedEldoradoItemRef.current = newEldo;
        setEldoradoMarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0 }));
        setEldoradoPage(1);

        const newDD373 = dd373Map[key] || null;
        setDD373Item(newDD373); selectedDD373ItemRef.current = newDD373;
        setDD373MarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0 }));
        setDd373Page(1);

        const newQiandao = qiandaoMap[key] || null;
        setQiandaoItem(newQiandao); selectedQiandaoItemRef.current = newQiandao;
        setQiandaoMarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0 }));
        setQiandaoSellMarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0, raw_change: 0, trusted_change: 0 }));
        setQiandaoPage(1);

    }, [selectedGame, selectedCurrency]);

    // --- FETCH EXCHANGE RATES (USD-Based) ---
    useEffect(() => {
        const fetchRate = async () => {
            try {
                const res = await axios.get(EXCHANGE_RATE_API);
                if (res.data && res.data.result === "success") {
                    const usdToVnd = res.data.rates.VND;
                    if (usdToVnd) {
                        setExchangeRateUSD_VND(usdToVnd);
                    }
                }
                try {
                    const cnyRes = await axios.get(`${DD373_API_BASE}/api/exchange_rate`);
                    if (cnyRes.data && cnyRes.data.cny_vnd) {
                        setExchangeRateCNY_VND(cnyRes.data.cny_vnd);
                    }
                } catch (err) {
                    console.error('Lỗi lấy tỷ giá CNY từ backend:', err);

                }
            } catch (error) {
                console.error("Lỗi lấy tỷ giá:", error);
            }
        };
        fetchRate();
        const intervalId = setInterval(fetchRate, 60000); // Fetch every 60 seconds
        return () => clearInterval(intervalId);
    }, []);

    const formatDD373Price = (price, isVND) => {
        if (!price) return '0';
        if (isVND) {
            return (price * exchangeRateCNY_VND).toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₫';
        }
        return price.toFixed(4) + ' ¥';
    };

    const formatG2GPrice = (price, isVND) => {
        if (!price) return '0';
        if (isVND) {
            return (price * 0.9405 * 25700).toLocaleString('vi-VN', { maximumFractionDigits: 0 }) + ' ₫';
        }
        return price.toFixed(6) + ' $';
    };

    const formatEldoradoPrice = (price, isVND) => {
        if (!price) return '0';
        if (isVND) {
            return (price * 0.912 * 25700).toLocaleString('vi-VN', { maximumFractionDigits: 0 }) + ' ₫';
        }
        return price.toFixed(6) + ' $';
    };

    // --- DATA FETCHING (DD373) ---
    const fetchDD373Data = useCallback(async () => {
        if (!selectedDD373Item) return;
        try {
            const snapRes = await axios.get(`${DD373_API_BASE}/snapshot?item_name=${encodeURIComponent(selectedDD373Item)}&hours=${timeWindow}`);
            const data = snapRes.data;
            if (data && data.order_book) {
                setDD373MarketData(prev => ({ ...prev, ...data, item_name: selectedDD373Item }));
            }
            const histRes = await axios.get(`${DD373_API_BASE}/history?item_name=${encodeURIComponent(selectedDD373Item)}&hours=${timeWindow}`);
            const hist = histRes.data.history;
            if (hist && hist.length > 0 && unifiedSeriesRef.current.dd373) {
                // Convert CNY price to VND for the unified chart
                unifiedSeriesRef.current.dd373.setData(hist.map(x => ({
                    time: x.time,
                    value: x.trusted_floor * exchangeRateCNY_VND
                })));
                if (unifiedChartInstance.current) unifiedChartInstance.current.timeScale().fitContent();
            }
        } catch (e) { console.error("DD373 API Error:", e); }
    }, [selectedDD373Item, timeWindow, exchangeRateCNY_VND]);

    useEffect(() => { fetchDD373Data(); }, [fetchDD373Data]);

    // --- DATA FETCHING (G2G) ---
    const fetchG2GData = useCallback(async () => {
        if (!selectedG2GItem) return;
        try {
            // Snapshot G2G
            const snapRes = await axios.get(`${G2G_API_BASE}/snapshot?item_name=${encodeURIComponent(selectedG2GItem)}&hours=${timeWindow}`);
            const data = snapRes.data;
            if (data && data.order_book) {
                setG2GMarketData({
                    ...data, item_name: selectedG2GItem, timestamp: data.timestamp,
                    raw_change: data.raw_change || 0, trusted_change: data.trusted_change || 0
                });
                if (data.recent_sales) {
                    setG2GSalesLog(data.recent_sales);
                    setG2GMarketVelocity(data.recent_sales.reduce((acc, curr) => acc + curr.amount, 0));
                } else {
                    setG2GSalesLog([]); setG2GMarketVelocity(0);
                }
                const map = {};
                data.order_book.forEach(i => map[i.seller] = i.sold_total);
                setPrevG2GOrderBook(map);
            }
            // History Price G2G
            const histRes = await axios.get(`${G2G_API_BASE}/history?item_name=${encodeURIComponent(selectedG2GItem)}&hours=${timeWindow}`);
            const hist = histRes.data.history;
            if (hist && hist.length > 0 && unifiedChartInstance.current && unifiedSeriesRef.current.g2g) {
                // Convert USD price to VND for the unified chart
                unifiedSeriesRef.current.g2g.setData(hist.map(x => ({
                    time: x.time,
                    value: x.trusted_floor * 0.9405 * 25700
                })));
                if (unifiedChartInstance.current) unifiedChartInstance.current.timeScale().fitContent();
            }
        } catch (e) { console.error("G2G API Error:", e); }
    }, [selectedG2GItem, timeWindow]);

    useEffect(() => { fetchG2GData(); }, [fetchG2GData]);

    const fetchEldoradoData = useCallback(async () => {
        if (!selectedEldoradoItem) return;
        try {
            const snapRes = await axios.get(`${ELDORADO_API_BASE}/snapshot?item_name=${encodeURIComponent(selectedEldoradoItem)}&hours=${timeWindow}`);
            const data = snapRes.data;
            if (data && data.order_book) {
                setEldoradoMarketData(prev => ({ ...prev, ...data, item_name: selectedEldoradoItem }));
            }
            const histRes = await axios.get(`${ELDORADO_API_BASE}/history?item_name=${encodeURIComponent(selectedEldoradoItem)}&hours=${timeWindow}`);
            const hist = histRes.data.history;
            if (hist && hist.length > 0 && unifiedSeriesRef.current.eldorado) {
                unifiedSeriesRef.current.eldorado.setData(hist.map(x => ({
                    time: x.time,
                    value: x.trusted_floor * 0.912 * 25700
                })));
                if (unifiedChartInstance.current) unifiedChartInstance.current.timeScale().fitContent();
            }
        } catch (e) { console.error("Eldorado API Error:", e); }
    }, [selectedEldoradoItem, timeWindow]);

    useEffect(() => { fetchEldoradoData(); }, [fetchEldoradoData]);

    // --- DATA FETCHING (QIANDAO) ---
    const fetchQiandaoData = useCallback(async () => {
        if (!selectedQiandaoItem) return;
        try {
            const snapRes = await axios.get(`${QIANDAO_API_BASE}/snapshot?item_name=${encodeURIComponent(selectedQiandaoItem)}&hours=${timeWindow}`);
            const data = snapRes.data;
            if (data && data.order_book) {
                setQiandaoMarketData(prev => ({ ...prev, ...data, item_name: selectedQiandaoItem }));
            }

            try {
                const sellSnapRes = await axios.get(`${QIANDAO_API_BASE}/snapshot?item_name=${encodeURIComponent(selectedQiandaoItem + ' (Sell)')}&hours=${timeWindow}`);
                const sellData = sellSnapRes.data;
                if (sellData && sellData.order_book) {
                    setQiandaoSellMarketData(prev => ({ ...prev, ...sellData }));
                }
            } catch (e) { }

            const histRes = await axios.get(`${QIANDAO_API_BASE}/history?item_name=${encodeURIComponent(selectedQiandaoItem)}&hours=${timeWindow}`);
            const hist = histRes.data.history;
            if (hist && hist.length > 0 && unifiedSeriesRef.current.qiandao) {
                unifiedSeriesRef.current.qiandao.setData(hist.map(x => ({
                    time: x.time,
                    value: x.trusted_floor * exchangeRateCNY_VND
                })));
                if (unifiedChartInstance.current) unifiedChartInstance.current.timeScale().fitContent();
            }
        } catch (e) { console.error("Qiandao API Error:", e); }
    }, [selectedQiandaoItem, timeWindow, exchangeRateCNY_VND]);

    useEffect(() => { fetchQiandaoData(); }, [fetchQiandaoData]);

    // --- INITIALIZE UNIFIED CHART ---
    useEffect(() => {
        if (!unifiedChartContainerRef.current) return;

        const chartConfig = {
            layout: { background: { type: 'solid', color: theme.card }, textColor: theme.textSec },
            grid: { vertLines: { color: '#22283f' }, horzLines: { color: '#22283f' } },
            crosshair: { vertLine: { labelVisible: true }, horzLine: { labelVisible: true } },
            timeScale: {
                timeVisible: true, secondsVisible: true, rightOffset: 5, fixRightEdge: true,
                tickMarkFormatter: (time) => new Date(time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
            },
            localization: {
                timeFormatter: (timestamp) => new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
            }
        };

        // Unified Price Chart (VND axis)
        const chart = createChart(unifiedChartContainerRef.current, {
            ...chartConfig,
            height: 320,
            width: unifiedChartContainerRef.current.clientWidth,
            rightPriceScale: {
                borderVisible: false,
                scaleMargins: { top: 0.25, bottom: 0.2 }
            }
        });

        const dd373Series = chart.addSeries(LineSeries, {
            color: theme.gold,
            lineWidth: 3,
            title: 'DD373',
            priceLineVisible: false,
            priceFormat: {
                type: 'custom',
                formatter: (price) => '₫ ' + price.toLocaleString('vi-VN', { maximumFractionDigits: 0 }),
                minMove: 100
            }
        });

        const g2gSeries = chart.addSeries(LineSeries, {
            color: theme.cyan,
            lineWidth: 3,
            title: 'G2G',
            priceLineVisible: false,
            priceFormat: {
                type: 'custom',
                formatter: (price) => '₫ ' + price.toLocaleString('vi-VN', { maximumFractionDigits: 0 }),
                minMove: 100
            }
        });

        const eldoradoSeries = chart.addSeries(LineSeries, {
            color: '#fbc02d',
            lineWidth: 3,
            title: 'Eldorado',
            priceLineVisible: false,
            priceFormat: {
                type: 'custom',
                formatter: (price) => '₫ ' + price.toLocaleString('vi-VN', { maximumFractionDigits: 0 }),
                minMove: 100
            }
        });

        const qiandaoSeries = chart.addSeries(LineSeries, {
            color: theme.qiandao,
            lineWidth: 3,
            title: 'Qiandao',
            priceLineVisible: false,
            priceFormat: {
                type: 'custom',
                formatter: (price) => '₫ ' + price.toLocaleString('vi-VN', { maximumFractionDigits: 0 }),
                minMove: 100
            }
        });

        unifiedChartInstance.current = chart;
        unifiedSeriesRef.current = { dd373: dd373Series, g2g: g2gSeries, eldorado: eldoradoSeries, qiandao: qiandaoSeries };

        const updateUnifiedLegend = (param) => {
            if (!unifiedLegendRef.current) return;
            const valid = !(param === undefined || param.time === undefined || param.point.x < 0);

            const getVal = (series) => {
                let itemData;
                if (valid) {
                    itemData = param.seriesData.get(series);
                } else {
                    const arr = series.data();
                    itemData = arr && arr.length > 0 ? arr[arr.length - 1] : null;
                }
                return itemData ? '₫ ' + itemData.value.toLocaleString('vi-VN', { maximumFractionDigits: 0 }) : 'N/A';
            };

            const timeStr = valid ? new Date(param.time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';

            unifiedLegendRef.current.innerHTML = `
            <div style="display:flex; gap:15px; align-items:center; flex-wrap:wrap">
                ${timeStr ? `<span style="color:#888; font-size:11px">[${timeStr}]</span>` : ''}
                <span>DD373 Price (VND): <b style="color:${theme.gold}">${getVal(dd373Series)}</b></span>
                <span style="color:#444">|</span>
                <span>G2G Price (VND): <b style="color:${theme.cyan}">${getVal(g2gSeries)}</b></span>
                <span style="color:#444">|</span>
                <span>Eldorado Price (VND): <b style="color:#fbc02d">${getVal(eldoradoSeries)}</b></span>
                <span style="color:#444">|</span>
                <span>Qiandao Price (VND): <b style="color:${theme.qiandao}">${getVal(qiandaoSeries)}</b></span>
            </div>
        `;
        };
        chart.subscribeCrosshairMove(updateUnifiedLegend);
        // Initial display
        setTimeout(() => updateUnifiedLegend(undefined), 100);

        // Resize Observer to keep charts responsive
        const resizeObserver = new ResizeObserver(() => {
            window.requestAnimationFrame(() => {
                if (unifiedChartContainerRef.current && unifiedChartInstance.current) {
                    unifiedChartInstance.current.applyOptions({ width: unifiedChartContainerRef.current.clientWidth });
                }
            });
        });

        resizeObserver.observe(unifiedChartContainerRef.current);

        return () => {
            resizeObserver.disconnect();
            chart.remove();
        };
    }, []);

    // Toggle line visibilities reactive hooks
    useEffect(() => {
        if (unifiedSeriesRef.current.dd373) {
            unifiedSeriesRef.current.dd373.applyOptions({ visible: showDD373Line });
        }
    }, [showDD373Line]);

    useEffect(() => {
        if (unifiedSeriesRef.current.g2g) {
            unifiedSeriesRef.current.g2g.applyOptions({ visible: showG2GLine });
        }
    }, [showG2GLine]);

    useEffect(() => {
        if (unifiedSeriesRef.current.eldorado) {
            unifiedSeriesRef.current.eldorado.applyOptions({ visible: showEldoradoLine });
        }
    }, [showEldoradoLine]);

    useEffect(() => {
        if (unifiedSeriesRef.current.qiandao) {
            unifiedSeriesRef.current.qiandao.applyOptions({ visible: showQiandaoLine });
        }
    }, [showQiandaoLine]);

    // Force chart resize when sidebar toggles
    useEffect(() => {
        const timer = setTimeout(() => {
            if (unifiedChartInstance.current && unifiedChartContainerRef.current) {
                unifiedChartInstance.current.applyOptions({ width: unifiedChartContainerRef.current.clientWidth });
            }
        }, 310);
        return () => clearTimeout(timer);
    }, [isSidebarOpen]);

    // --- WEBSOCKET CONNECTION (DD373 on Port 8000) ---
    useEffect(() => {
        let ws = new WebSocket(getWsUrl(8000, "dd373.gegechart.xyz"));
        ws.onopen = () => setDD373Status("Live");
        ws.onclose = () => setDD373Status("Offline");
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'UPDATE' && data.platform === 'dd373') {
                const item = data.item_name;

                const norm = (s) => (s || '').replace(/\s+/g, '').toLowerCase();
                if (!selectedDD373ItemRef.current) {
                    setDD373Item(item); selectedDD373ItemRef.current = item;
                }
                if (norm(selectedDD373ItemRef.current) === norm(item)) {
                    setDD373MarketData(prev => ({ ...prev, ...data }));
                    const ts = new Date(data.timestamp).getTime() / 1000;
                    if (unifiedSeriesRef.current.dd373) {
                        const seriesData = unifiedSeriesRef.current.dd373.data();
                        const lastTime = seriesData.length > 0 ? seriesData[seriesData.length - 1].time : 0;
                        const finalTs = Math.max(ts, lastTime + 1);
                        try {
                            unifiedSeriesRef.current.dd373.update({
                                time: finalTs,
                                value: data.trusted_floor * exchangeRateCNY_VND
                            });
                        } catch (e) { }
                    }
                }
            }
        };
        return () => ws.close();
    }, [exchangeRateCNY_VND]);

    // --- WEBSOCKET CONNECTION (ELDORADO on Port 8001) ---
    useEffect(() => {
        let ws = new WebSocket(getWsUrl(8001, "eldo.gegechart.xyz"));
        ws.onopen = () => setEldoradoStatus("Live");
        ws.onclose = () => setEldoradoStatus("Offline");
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'UPDATE') {
                const item = data.item_name;

                if (!selectedEldoradoItemRef.current) {
                    setEldoradoItem(item); selectedEldoradoItemRef.current = item;
                }
                if (selectedEldoradoItemRef.current === item) {
                    setEldoradoMarketData(prev => ({ ...prev, ...data }));
                    const ts = new Date(data.timestamp.replace(' ', 'T')).getTime() / 1000;
                    if (unifiedSeriesRef.current.eldorado) {
                        const seriesData = unifiedSeriesRef.current.eldorado.data();
                        const lastTime = seriesData.length > 0 ? seriesData[seriesData.length - 1].time : 0;
                        const finalTs = Math.max(ts, lastTime + 1);
                        try {
                            unifiedSeriesRef.current.eldorado.update({
                                time: finalTs,
                                value: data.trusted_floor * 0.912 * 25700
                            });
                        } catch (e) { }
                    }
                }
            }
        };
        return () => ws.close();
    }, []);

    // --- WEBSOCKET CONNECTION (G2G on Port 8002) ---
    useEffect(() => {
        let ws = new WebSocket(getWsUrl(8002, "g2g.gegechart.xyz"));
        ws.onopen = () => setG2GStatus("Live");
        ws.onclose = () => setG2GStatus("Offline");
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'UPDATE') {
                const incomingItem = data.item_name;

                if (!selectedG2GItemRef.current) {
                    setG2GItem(incomingItem); selectedG2GItemRef.current = incomingItem;
                    fetchG2GData();
                }
                if (selectedG2GItemRef.current !== incomingItem) return;

                const ts = new Date(data.timestamp).getTime() / 1000;
                let sessionVol = 0;
                let newSales = [];

                data.order_book.forEach(item => {
                    const prev = prevG2GOrderBook[item.seller] || item.sold_total;
                    const diff = item.sold_total - prev;
                    if (diff > 0) {
                        sessionVol += diff;
                        newSales.push({ seller: item.seller, amount: diff, time: data.timestamp });
                    }
                });
                if (sessionVol > 0) {
                    setG2GMarketVelocity(prev => prev + sessionVol);
                    setG2GSalesLog(prev => [...newSales, ...prev].slice(0, 50));
                }
                const map = {};
                data.order_book.forEach(i => map[i.seller] = i.sold_total);
                setPrevG2GOrderBook(map);

                setG2GMarketData(prev => ({ ...prev, ...data, item_name: data.item_name }));

                if (unifiedSeriesRef.current.g2g) {
                    const seriesData = unifiedSeriesRef.current.g2g.data();
                    const lastTime = seriesData.length > 0 ? seriesData[seriesData.length - 1].time : 0;
                    const finalTs = Math.max(ts, lastTime + 1);
                    try {
                        unifiedSeriesRef.current.g2g.update({
                            time: finalTs,
                            value: data.trusted_floor * 0.9405 * 25700
                        });
                    } catch (e) { }
                }
            }
        };
        return () => ws.close();
    }, [prevG2GOrderBook, fetchG2GData]);

    // --- WEBSOCKET CONNECTION (QIANDAO on Port 8003) ---
    useEffect(() => {
        let ws = new WebSocket(getWsUrl(8003, "qiandao.gegechart.xyz"));
        ws.onopen = () => setQiandaoStatus("Live");
        ws.onclose = () => setQiandaoStatus("Offline");
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'UPDATE') {
                const item = data.item_name;

                if (item && item.includes('(Sell)')) {
                    if (selectedQiandaoItemRef.current && item === `${selectedQiandaoItemRef.current} (Sell)`) {
                        setQiandaoSellMarketData(prev => ({ ...prev, ...data }));
                    }
                    return;
                }

                if (!selectedQiandaoItemRef.current) {
                    setQiandaoItem(item); selectedQiandaoItemRef.current = item;
                }
                if (selectedQiandaoItemRef.current === item) {
                    setQiandaoMarketData(prev => ({ ...prev, ...data }));
                    const ts = new Date(data.timestamp.replace(' ', 'T')).getTime() / 1000;
                    if (unifiedSeriesRef.current.qiandao) {
                        const seriesData = unifiedSeriesRef.current.qiandao.data();
                        const lastTime = seriesData.length > 0 ? seriesData[seriesData.length - 1].time : 0;
                        const finalTs = Math.max(ts, lastTime + 1);
                        try {
                            unifiedSeriesRef.current.qiandao.update({
                                time: finalTs,
                                value: data.trusted_floor * exchangeRateCNY_VND
                            });
                        } catch (e) { }
                    }
                }
            }
        };
        return () => ws.close();
    }, [exchangeRateCNY_VND]);

    // --- FORWARD FILL (HEARTBEAT) ---
    // Giữ cho các đường đồ thị kéo dài liên tục tới hiện tại ngay cả khi không có data mới
    useEffect(() => {
        const interval = setInterval(() => {
            const now = Math.floor(Date.now() / 1000);

            try {
                if (unifiedSeriesRef.current.dd373) {
                    const data = unifiedSeriesRef.current.dd373.data();
                    const lastData = data.length > 0 ? data[data.length - 1] : null;
                    if (lastData && now > lastData.time) {
                        unifiedSeriesRef.current.dd373.update({
                            time: now,
                            value: lastData.value
                        });
                    }
                }

                if (unifiedSeriesRef.current.g2g) {
                    const data = unifiedSeriesRef.current.g2g.data();
                    const lastData = data.length > 0 ? data[data.length - 1] : null;
                    if (lastData && now > lastData.time) {
                        unifiedSeriesRef.current.g2g.update({
                            time: now,
                            value: lastData.value
                        });
                    }
                }

                if (unifiedSeriesRef.current.eldorado) {
                    const data = unifiedSeriesRef.current.eldorado.data();
                    const lastData = data.length > 0 ? data[data.length - 1] : null;
                    if (lastData && now > lastData.time) {
                        unifiedSeriesRef.current.eldorado.update({
                            time: now,
                            value: lastData.value
                        });
                    }
                }

                if (unifiedSeriesRef.current.qiandao) {
                    const data = unifiedSeriesRef.current.qiandao.data();
                    const lastData = data.length > 0 ? data[data.length - 1] : null;
                    if (lastData && now > lastData.time) {
                        unifiedSeriesRef.current.qiandao.update({
                            time: now,
                            value: lastData.value
                        });
                    }
                }
            } catch (e) { }
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    // --- ITEM DROPDOWN HANDLERS ---
    const handleDD373ItemChange = (e) => {
        const newItem = e.target.value;
        setDD373Item(newItem); selectedDD373ItemRef.current = newItem;
        setDD373MarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0 }));
        setDd373Page(1);
    };

    const handleG2GItemChange = (e) => {
        const newItem = e.target.value;
        setG2GItem(newItem); selectedG2GItemRef.current = newItem;
        setG2GMarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0 }));
        setPrevG2GOrderBook({});
        setG2gPage(1);
    };

    const handleEldoradoItemChange = (e) => {
        const newItem = e.target.value;
        setEldoradoItem(newItem); selectedEldoradoItemRef.current = newItem;
        setEldoradoMarketData(prev => ({ ...prev, order_book: [], raw_floor: 0, trusted_floor: 0 }));
        setEldoradoPage(1);
    };

    // --- G2G COMPETITOR SELECTIONS ---
    const handleAddCompetitor = (seller) => {
        if (!selectedCompetitors.includes(seller)) {
            setSelectedCompetitors(prev => [...prev, seller]);
            if (!competitorColors[seller]) {
                const nextColor = COLORS[selectedCompetitors.length % COLORS.length];
                setCompetitorColors(prev => ({ ...prev, [seller]: nextColor }));
            }
        }
        setSearchTerm("");
        setShowResults(false);
    };

    const handleRemoveCompetitor = (seller) => {
        setSelectedCompetitors(prev => prev.filter(s => s !== seller));
    };

    const handleColorChange = (seller, newColor) => {
        setCompetitorColors(prev => ({ ...prev, [seller]: newColor }));
    };

    // --- MEMOIZED DERIVED STATES ---
    const dd373SortedBook = useMemo(() => {
        const book = [...dd373MarketData.order_book];
        return book.sort((a, b) => b.unit_price - a.unit_price); // Recycle: high price on top
    }, [dd373MarketData.order_book]);

    const g2gSortedBook = useMemo(() => {
        const book = [...g2gMarketData.order_book];
        return book.sort((a, b) => a.unit_price - b.unit_price); // Sell: low price on top
    }, [g2gMarketData.order_book]);

    const eldoradoSortedBook = useMemo(() => {
        const book = [...eldoradoMarketData.order_book];
        return book.sort((a, b) => a.unit_price - b.unit_price); // Sell: low price on top
    }, [eldoradoMarketData.order_book]);

    const uniqueG2GSellers = useMemo(() => {
        return [...new Set(g2gMarketData.order_book.map(i => i.seller))].sort();
    }, [g2gMarketData.order_book]);

    const filteredG2GSellers = uniqueG2GSellers.filter(s => s.toLowerCase().includes(searchTerm.toLowerCase()));

    const dd373CurrencySymbol = showVND ? '₫' : '¥';
    const g2gCurrencySymbol = showVND ? '₫' : '$';

    return (
        <div style={styles.app}>

            {/* SIDEBAR */}
            <div style={styles.sidebar(isSidebarOpen)}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '0 5px' }}>

                    {/* Server Connections */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 'bold', color: theme.textSec }}>SERVERS STATUS</span>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#181c2e', padding: '10px', borderRadius: '6px', border: `1px solid ${theme.border}` }}>
                            <span style={{ fontSize: '12px', fontWeight: 'bold' }}>DD373 (dd373.gegechart.xyz)</span>
                            <span style={styles.statusBadge(dd373Status === "Live")}>
                                <span style={styles.statusDot(dd373Status === "Live")} /> {dd373Status}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#181c2e', padding: '10px', borderRadius: '6px', border: `1px solid ${theme.border}` }}>
                            <span style={{ fontSize: '12px', fontWeight: 'bold' }}>G2G (g2g.gegechart.xyz)</span>
                            <span style={styles.statusBadge(g2gStatus === "Live")}>
                                <span style={styles.statusDot(g2gStatus === "Live")} /> {g2gStatus}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#181c2e', padding: '10px', borderRadius: '6px', border: `1px solid ${theme.border}` }}>
                            <span style={{ fontSize: '12px', fontWeight: 'bold' }}>Eldorado (eldo.gegechart.xyz)</span>
                            <span style={styles.statusBadge(eldoradoStatus === "Live")}>
                                <span style={styles.statusDot(eldoradoStatus === "Live")} /> {eldoradoStatus}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#181c2e', padding: '10px', borderRadius: '6px', border: `1px solid ${theme.border}` }}>
                            <span style={{ fontSize: '12px', fontWeight: 'bold' }}>Qiandao (qiandao.gegechart.xyz)</span>
                            <span style={styles.statusBadge(qiandaoStatus === "Live")}>
                                <span style={styles.statusDot(qiandaoStatus === "Live")} /> {qiandaoStatus}
                            </span>
                        </div>
                    </div>

                    <hr style={{ border: 'none', borderTop: `1px solid ${theme.border}`, margin: '5px 0' }} />

                    {/* Global configurations */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <h3 style={{ margin: 0, fontSize: '14px', color: theme.purple, display: 'flex', alignItems: 'center', gap: '6px' }}>
                            ⚙️ Global Settings
                        </h3>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Time Window</label>
                            <select style={styles.input} value={timeWindow} onChange={(e) => setTimeWindow(Number(e.target.value))}>
                                <option value={0.25}>15 Minutes</option>
                                <option value={1}>1 Hour</option>
                                <option value={4}>4 Hours</option>
                                <option value={24}>24 Hours</option>
                            </select>
                        </div>
                        <div style={{ padding: '8px 10px', backgroundColor: '#1c2134', borderRadius: '6px', fontSize: '11px', color: theme.textSec, border: `1px solid ${theme.border}`, display: 'flex', flexDirection: 'column', gap: '5px' }}>
                            <div>G2G USD/VND (Custom: 25.7k * 94.05%): <b>1 USD ≈ 24.171 VND</b></div>
                            <div>Eldo USD/VND (Custom: 25.7k * 91.2%): <b>1 USD ≈ 23.438 VND</b></div>
                            <div>CNY/VND: <b>1 CNY ≈ {exchangeRateCNY_VND.toFixed(0)} VND</b></div>
                        </div>
                    </div>

                    <hr style={{ border: 'none', borderTop: `1px solid ${theme.border}`, margin: '5px 0' }} />

                    {/* Unified Target Selection */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <h3 style={{ margin: 0, fontSize: '14px', color: '#2196f3', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            🎯 Target Selection
                        </h3>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Game</label>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                {[{ id: 'poe1', label: 'PoE 1' }, { id: 'poe2', label: 'PoE 2' }].map(game => (
                                    <button key={game.id}
                                        onClick={() => setSelectedGame(game.id)}
                                        style={{
                                            flex: 1, padding: '10px 12px', borderRadius: '8px',
                                            border: `2px solid ${selectedGame === game.id ? '#2196f3' : theme.border}`,
                                            backgroundColor: selectedGame === game.id ? 'rgba(33, 150, 243, 0.15)' : '#1c2134',
                                            color: selectedGame === game.id ? '#fff' : theme.textSec,
                                            cursor: 'pointer', fontWeight: 'bold', fontSize: '13px',
                                            transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                                            boxShadow: selectedGame === game.id ? '0 0 12px rgba(33, 150, 243, 0.3)' : 'none'
                                        }}
                                    >
                                        <span style={{
                                            width: '16px', height: '16px', borderRadius: '4px',
                                            border: `2px solid ${selectedGame === game.id ? '#2196f3' : theme.textSec}`,
                                            backgroundColor: selectedGame === game.id ? '#2196f3' : 'transparent',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: '10px', color: '#fff', flexShrink: 0
                                        }}>
                                            {selectedGame === game.id ? '✓' : ''}
                                        </span>
                                        {game.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Currency</label>
                            <div style={{ display: 'flex', gap: '6px' }}>
                                {currencyOptions.map(cur => (
                                    <button key={cur.id}
                                        onClick={() => setSelectedCurrency(cur.id)}
                                        style={{
                                            flex: 1, padding: '8px 4px', borderRadius: '8px',
                                            border: `2px solid ${selectedCurrency === cur.id ? cur.color : theme.border}`,
                                            backgroundColor: selectedCurrency === cur.id ? `${cur.color}20` : '#1c2134',
                                            color: selectedCurrency === cur.id ? '#fff' : theme.textSec,
                                            cursor: 'pointer', fontWeight: 'bold', fontSize: '11px',
                                            transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
                                            boxShadow: selectedCurrency === cur.id ? `0 0 12px ${cur.color}40` : 'none',
                                            whiteSpace: 'nowrap'
                                        }}
                                    >
                                        <span style={{
                                            width: '14px', height: '14px', borderRadius: '4px',
                                            border: `2px solid ${selectedCurrency === cur.id ? cur.color : theme.textSec}`,
                                            backgroundColor: selectedCurrency === cur.id ? cur.color : 'transparent',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: '9px', color: '#fff', flexShrink: 0
                                        }}>
                                            {selectedCurrency === cur.id ? '✓' : ''}
                                        </span>
                                        {cur.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div style={{ padding: '8px 10px', backgroundColor: '#1c2134', borderRadius: '6px', fontSize: '11px', color: theme.textSec, border: `1px solid ${theme.border}`, textAlign: 'center' }}>
                            Active: <b style={{ color: '#fff' }}>{selectedGame === 'poe1' ? 'PoE 1' : 'PoE 2'} — {(currencyOptions.find(c => c.id === selectedCurrency) || currencyOptions[0]).label}</b>
                        </div>
                    </div>

                    <hr style={{ border: 'none', borderTop: `1px solid ${theme.border}`, margin: '5px 0' }} />

                    {/* DD373 Controls */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <h3 style={{ margin: 0, fontSize: '14px', color: theme.gold, display: 'flex', alignItems: 'center', gap: '6px' }}>
                            🦅 DD373 Configuration
                        </h3>
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Highlight DD373 Seller</label>
                            <input style={styles.input} placeholder="Highlight seller name..."
                                value={highlightDD373Text} onChange={(e) => setHighlightDD373Text(e.target.value)} />
                        </div>
                    </div>

                    <hr style={{ border: 'none', borderTop: `1px solid ${theme.border}`, margin: '5px 0' }} />

                    {/* G2G Controls */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <h3 style={{ margin: 0, fontSize: '14px', color: theme.cyan, display: 'flex', alignItems: 'center', gap: '6px' }}>
                            🦅 G2G Configuration
                        </h3>
                        {/* G2G Competitor Selector */}
                        <div style={styles.inputGroup}>
                            <label style={styles.inputLabel}>Highlight G2G Competitors</label>
                            <div style={{ position: 'relative', width: '100%' }}>
                                <input style={styles.input} placeholder="Search competitors..." value={searchTerm}
                                    onChange={(e) => { setSearchTerm(e.target.value); setShowResults(true); }}
                                    onFocus={() => setShowResults(true)}
                                    onBlur={() => setTimeout(() => setShowResults(false), 200)} />
                                {showResults && searchTerm && (
                                    <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, backgroundColor: theme.card, border: `1px solid ${theme.border}`, borderRadius: '6px', zIndex: 100, maxHeight: '150px', overflowY: 'auto', boxShadow: '0 8px 16px rgba(0,0,0,0.5)' }}>
                                        {filteredG2GSellers.length > 0 ? filteredG2GSellers.map(seller => (
                                            <div key={seller} style={{ padding: '8px 10px', cursor: 'pointer', borderBottom: `1px solid ${theme.border}`, fontSize: '12px' }} onMouseDown={() => handleAddCompetitor(seller)}> {seller} </div>
                                        )) : <div style={{ padding: '8px 10px', color: '#777', fontSize: '12px' }}>No matches</div>}
                                    </div>
                                )}
                            </div>

                            {/* Active G2G Competitor Tags */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: '6px' }}>
                                {selectedCompetitors.map((seller) => (
                                    <div key={seller} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#1c2134', padding: '6px 8px', borderRadius: '4px', border: `1px solid ${theme.border}` }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <div style={{ width: '12px', height: '12px', borderRadius: '50%', overflow: 'hidden', border: '1px solid #fff', cursor: 'pointer', position: 'relative', backgroundColor: competitorColors[seller] || '#fff' }}>
                                                <input type="color" style={{ position: 'absolute', top: '-50%', left: '-50%', width: '200%', height: '200%', opacity: 0, cursor: 'pointer' }} value={competitorColors[seller] || '#ffffff'} onChange={(e) => handleColorChange(seller, e.target.value)} />
                                            </div>
                                            <span style={{ fontSize: '12px' }}>{seller}</span>
                                        </div>
                                        <span style={{ cursor: 'pointer', color: theme.danger, fontWeight: 'bold', fontSize: '14px', padding: '0 4px' }} onClick={() => handleRemoveCompetitor(seller)}>×</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <hr style={{ border: 'none', borderTop: `1px solid ${theme.border}`, margin: '5px 0' }} />

                    {/* Eldorado Controls */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <h3 style={{ margin: 0, fontSize: '14px', color: '#fbc02d', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            ⚡ Eldorado Configuration
                        </h3>
                        {/* Rainbow Highlighted Currency Display Button */}
                        <button
                            style={{
                                width: '100%',
                                padding: '11px 14px',
                                fontSize: '0.92rem',
                                fontWeight: '900',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                border: '2px solid rgba(255,255,255,0.8)',
                                color: '#ffffff',
                                textShadow: '0 2px 4px rgba(0,0,0,0.85)',
                                background: 'linear-gradient(90deg, #ff0000, #ff7f00, #e6c800, #00c853, #0088ff, #6200ea, #aa00ff)',
                                boxShadow: '0 4px 16px rgba(255, 127, 0, 0.45)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                transition: 'all 0.3s ease',
                                marginTop: '4px'
                            }}
                            onClick={() => setShowVND(!showVND)}
                        >
                            🌈 {showVND ? 'Show Native Currencies (¥ / $)' : 'Show VND (₫)'}
                        </button>
                    </div>

                </div>
            </div>

            {/* MAIN CONTENT AREA */}
            <div style={styles.main}>

                {/* TOP DASHBOARD NAV BAR */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                        <button style={styles.toggleBtn} onClick={() => setIsSidebarOpen(!isSidebarOpen)}>☰</button>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <img src="/media__1782216597739.png" alt="GEGE ESPORTS Logo" style={{ height: '40px', borderRadius: '8px' }} />
                            <h1 style={{ fontSize: '1.6rem', fontWeight: 'bold', margin: 0, background: 'linear-gradient(to right, #ff3b30, #007aff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                Unified Market Sniper Dashboard
                            </h1>
                        </div>
                    </div>
                </div>

                {/* ================= SECTION 1: KPI CARDS ================= */}
                <div style={styles.kpiGrid}>

                    {/* DD373 KPI */}
                    <div style={styles.kpiCard(theme.gold)}>
                        <div style={styles.kpiLabel}>DD373 Max Price (Trusted)</div>
                        <div style={{ ...styles.kpiValue, color: theme.gold }}>
                            {formatDD373Price(dd373MarketData.trusted_floor, showVND)}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                            <PercentageBadge value={dd373MarketData.trusted_change} />
                            <span style={{ fontSize: '0.75rem', color: theme.textSec }}>Stock: {dd373SortedBook[0]?.stock || 0}</span>
                        </div>
                    </div>

                    {/* G2G KPI */}
                    <div style={styles.kpiCard(theme.cyan)}>
                        <div style={styles.kpiLabel}>G2G Trusted Floor Price</div>
                        <div style={{ ...styles.kpiValue, color: theme.cyan }}>
                            {formatG2GPrice(g2gMarketData.trusted_floor, showVND)}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                            <PercentageBadge value={g2gMarketData.trusted_change} />
                            <span style={{ fontSize: '0.75rem', color: theme.textSec }}>Offers: {g2gSortedBook.length}</span>
                        </div>
                    </div>

                    {/* Eldorado KPI */}
                    <div style={styles.kpiCard('#fbc02d')}>
                        <div style={styles.kpiLabel}>Eldorado Floor Price (Trusted)</div>
                        <div style={{ ...styles.kpiValue, color: '#fbc02d' }}>
                            {formatEldoradoPrice(eldoradoMarketData.trusted_floor, showVND)}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                            <PercentageBadge value={eldoradoMarketData.trusted_change} />
                            <span style={{ fontSize: '0.75rem', color: theme.textSec }}>Offers: {eldoradoMarketData.order_book?.length || 0}</span>
                        </div>
                    </div>

                    {/* Combined Info KPI */}
                    <div style={styles.kpiCard(theme.purple)}>
                        <div style={styles.kpiLabel}>Selected Target Items</div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            <span style={{ color: theme.gold }}>DD373:</span> {selectedDD373Item || 'None'}
                        </div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '3px' }}>
                            <span style={{ color: theme.cyan }}>G2G:</span> {selectedG2GItem || 'None'}
                        </div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '3px' }}>
                            <span style={{ color: '#fbc02d' }}>Eldo:</span> {selectedEldoradoItem || 'None'}
                        </div>
                    </div>

                </div>

                {/* ================= SECTION 2: SINGLE COMPARISON CHART ================= */}
                <div style={styles.sectionHeader}>
                    <h2 style={{ fontSize: '1.25rem', margin: 0, color: theme.purple, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        📈 DD373 vs G2G vs Eldorado Price Comparison (VND Axis)
                    </h2>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <button
                            style={{
                                ...styles.currencyBtn,
                                borderColor: showDD373Line ? theme.gold : theme.border,
                                color: showDD373Line ? theme.gold : theme.textSec,
                                backgroundColor: showDD373Line ? 'rgba(0, 122, 255, 0.1)' : '#1c2134',
                                padding: '4px 10px',
                                fontSize: '0.75rem'
                            }}
                            onClick={() => setShowDD373Line(!showDD373Line)}
                        >
                            {showDD373Line ? '👁️ DD373 On' : '👁️‍🗨️ DD373 Off'}
                        </button>
                        <button
                            style={{
                                ...styles.currencyBtn,
                                borderColor: showG2GLine ? theme.cyan : theme.border,
                                color: showG2GLine ? theme.cyan : theme.textSec,
                                backgroundColor: showG2GLine ? 'rgba(255, 59, 48, 0.1)' : '#1c2134',
                                padding: '4px 10px',
                                fontSize: '0.75rem'
                            }}
                            onClick={() => setShowG2GLine(!showG2GLine)}
                        >
                            {showG2GLine ? '👁️ G2G On' : '👁️‍🗨️ G2G Off'}
                        </button>
                        <button
                            style={{
                                ...styles.currencyBtn,
                                borderColor: showEldoradoLine ? '#fbc02d' : theme.border,
                                color: showEldoradoLine ? '#fbc02d' : theme.textSec,
                                backgroundColor: showEldoradoLine ? 'rgba(251, 192, 45, 0.1)' : '#1c2134',
                                padding: '4px 10px',
                                fontSize: '0.75rem'
                            }}
                            onClick={() => setShowEldoradoLine(!showEldoradoLine)}
                        >
                            {showEldoradoLine ? '👁️ Eldo On' : '👁️‍🗨️ Eldo Off'}
                        </button>
                        <button
                            style={{
                                ...styles.currencyBtn,
                                borderColor: showQiandaoLine ? theme.qiandao : theme.border,
                                color: showQiandaoLine ? theme.qiandao : theme.textSec,
                                backgroundColor: showQiandaoLine ? 'rgba(0, 230, 118, 0.1)' : '#1c2134',
                                padding: '4px 10px',
                                fontSize: '0.75rem'
                            }}
                            onClick={() => setShowQiandaoLine(!showQiandaoLine)}
                        >
                            {showQiandaoLine ? '👁️ Qian On' : '👁️‍🗨️ Qian Off'}
                        </button>
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
                                gap: '6px'
                            }}
                            onClick={() => {
                                unifiedChartInstance.current?.timeScale().scrollToRealTime();
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
                        <span style={{ fontSize: '0.8rem', color: theme.textSec, marginLeft: '10px' }}>
                            History scale: {timeWindow} hours
                        </span>
                    </div>
                </div>

                <div style={styles.chartSection}>
                    <div ref={unifiedLegendRef} style={styles.legend}>Loading unified comparison chart...</div>
                    <div ref={unifiedChartContainerRef} style={{ width: '100%', flex: 1 }} />
                </div>

                {/* ================= SECTION 3: SIDE-BY-SIDE TABLES ================= */}
                <div style={styles.tablesContainer}>

                    {/* Left side: DD373 Live Order Book */}
                    <div style={styles.tableCard}>
                        <div style={styles.tableHeader}>
                            <span style={{ color: theme.gold }}>📖 DD373 Live Order Book</span>
                            <span style={{ fontSize: '0.75rem', color: theme.textSec }}>Recycling Buyers (Highest Price first)</span>
                        </div>
                        <div style={styles.tableWrapper}>
                            <table style={styles.table}>
                                <thead>
                                    <tr>
                                        <th style={{ ...styles.th, width: '40px' }}>#</th>
                                        <th style={styles.th}>Buyer</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Price ({dd373CurrencySymbol})</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Stock</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {dd373SortedBook.slice((dd373Page - 1) * 10, dd373Page * 10).map((row, index) => {
                                        const i = (dd373Page - 1) * 10 + index;
                                        const isHighlight = highlightDD373Text && row.seller.toLowerCase().includes(highlightDD373Text.toLowerCase());
                                        const bg = isHighlight ? 'rgba(0, 230, 118, 0.15)' : (index % 2 === 0 ? 'transparent' : theme.tableOdd);

                                        return (
                                            <tr key={i} style={{ backgroundColor: bg, transition: '0.2s' }}>
                                                <td style={{ ...styles.td, color: '#666' }}>{i + 1}</td>
                                                <td style={styles.td}>
                                                    <div style={{ fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{row.seller}</div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                                                        <div style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(255, 215, 0, 0.15)', border: '1px solid rgba(255, 215, 0, 0.3)', color: theme.gold, fontWeight: '900', fontSize: '0.9rem', lineHeight: '1.2' }}>
                                                            {formatDD373Price(row.unit_price, true)}
                                                        </div>
                                                        <div style={{ padding: '2px 5px', borderRadius: '4px', background: '#252932', border: '1px solid rgba(255,255,255,0.1)', color: '#ccc', fontWeight: 'bold', fontSize: '0.75rem', lineHeight: '1.2' }}>
                                                            {formatDD373Price(row.unit_price, false)}
                                                        </div>
                                                    </div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right' }}>{row.stock}</td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                        <Pagination currentPage={dd373Page} totalItems={dd373SortedBook.length} onPageChange={setDd373Page} />
                    </div>

                    {/* Right side: G2G Live Order Book */}
                    <div style={styles.tableCard}>
                        <div style={styles.tableHeader}>
                            <span style={{ color: theme.cyan }}>📖 G2G Live Order Book</span>
                            <span style={{ fontSize: '0.75rem', color: theme.textSec }}>Active Sellers (Lowest Price first)</span>
                        </div>
                        <div style={styles.tableWrapper}>
                            <table style={styles.table}>
                                <thead>
                                    <tr>
                                        <th style={{ ...styles.th, width: '40px' }}>#</th>
                                        <th style={styles.th}>Seller</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Price (VND / USD)</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Stock</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {padOrderBook(g2gSortedBook.slice((g2gPage - 1) * 10, g2gPage * 10), 10).map((row, index) => {
                                        const i = (g2gPage - 1) * 10 + index;
                                        if (!row) {
                                            return (
                                                <tr key={i} style={{ backgroundColor: index % 2 === 0 ? 'transparent' : theme.tableOdd }}>
                                                    <td style={{ ...styles.td, color: '#666' }}>{i + 1}</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                </tr>
                                            );
                                        }
                                        const isComp = selectedCompetitors.includes(row.seller);
                                        const compColor = competitorColors[row.seller];

                                        const bg = isComp
                                            ? (compColor ? `${compColor}20` : 'rgba(255, 59, 48, 0.15)')
                                            : (index % 2 === 0 ? 'transparent' : theme.tableOdd);

                                        return (
                                            <tr key={i} style={{ backgroundColor: bg, transition: '0.2s', borderLeft: isComp ? `3px solid ${compColor || theme.cyan}` : 'none' }}>
                                                <td style={{ ...styles.td, color: '#666' }}>{i + 1}</td>
                                                <td style={{ ...styles.td, fontWeight: 'bold', color: isComp ? (compColor || '#fff') : '#fff' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                        {row.seller && row.seller.toLowerCase() === 'gegeteam' && (
                                                            <img src="/media__1782216597739.png" alt="Gege Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '1px solid #ff3b30' }} />
                                                        )}
                                                        {row.seller && row.seller.toLowerCase() === 'cnlteam' && (
                                                            <img src="/anh-cnl.png" alt="CNL Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '1px solid #ff3b30' }} />
                                                        )}
                                                        {row.seller && row.seller.toLowerCase() === 'thanku' && (
                                                            <img src="/thanku.png" alt="Thanku Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '1px solid #ff3b30' }} />
                                                        )}
                                                        {row.seller && row.seller.toLowerCase() === 'alotofgold' && (
                                                            <img src="/Alot of gold.png" alt="AlotofGold Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '1px solid #ff3b30' }} />
                                                        )}
                                                        <span>{row.seller}</span>
                                                    </div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                                                        <div style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(0, 229, 255, 0.15)', border: '1px solid rgba(0, 229, 255, 0.3)', color: theme.cyan, fontWeight: '900', fontSize: '0.9rem', lineHeight: '1.2' }}>
                                                            {formatG2GPrice(row.unit_price, true)}
                                                        </div>
                                                        <div style={{ padding: '2px 5px', borderRadius: '4px', background: '#252932', border: '1px solid rgba(255,255,255,0.1)', color: '#ccc', fontWeight: 'bold', fontSize: '0.75rem', lineHeight: '1.2' }}>
                                                            {formatG2GPrice(row.unit_price, false)}
                                                        </div>
                                                    </div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right' }}>{row.stock}</td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                        <Pagination currentPage={g2gPage} totalItems={g2gSortedBook.length} onPageChange={setG2gPage} />
                    </div>

                    {/* Eldorado Live Order Book */}
                    <div style={styles.tableCard}>
                        <div style={styles.tableHeader}>
                            <span style={{ color: '#fbc02d' }}>📖 Eldorado Live Order Book</span>
                            <span style={{ fontSize: '0.75rem', color: theme.textSec }}>Active Sellers (Lowest Price first)</span>
                        </div>
                        <div style={styles.tableWrapper}>
                            <table style={styles.table}>
                                <thead>
                                    <tr>
                                        <th style={{ ...styles.th, width: '30px' }}>#</th>
                                        <th style={styles.th}>Seller</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Price (VND / USD)</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Stock</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {padOrderBook(eldoradoSortedBook.slice((eldoradoPage - 1) * 10, eldoradoPage * 10), 10).map((row, index) => {
                                        const i = (eldoradoPage - 1) * 10 + index;
                                        if (!row) {
                                            return (
                                                <tr key={i} style={{ backgroundColor: index % 2 === 0 ? 'transparent' : theme.tableOdd }}>
                                                    <td style={{ ...styles.td, color: '#666' }}>{i + 1}</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                </tr>
                                            );
                                        }
                                        const bg = index % 2 === 0 ? 'transparent' : theme.tableOdd;
                                        const isFast = ['20 Phút', '1 Giờ', 'Minute20', 'Hour1', 'Minute', 'Hour'].some(k => row.online && row.online.includes(k));
                                        return (
                                            <tr key={i} style={{ backgroundColor: bg, transition: '0.2s' }}>
                                                <td style={{ ...styles.td, color: '#666' }}>{i + 1}</td>
                                                <td style={{ ...styles.td, fontWeight: 'bold' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                        {row.seller && row.seller.toLowerCase() === 'gegeteam' && (
                                                            <img src="/media__1782216597739.png" alt="Gege Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '1px solid #fbc02d' }} />
                                                        )}
                                                        {row.seller && row.seller.toLowerCase() === 'cnlteam' && (
                                                            <img src="/anh-cnl.png" alt="CNL Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '1px solid #fbc02d' }} />
                                                        )}
                                                        <span>{row.seller}</span>
                                                    </div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                                                        <div style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(251, 192, 45, 0.15)', border: '1px solid rgba(251, 192, 45, 0.3)', color: '#fbc02d', fontWeight: '900', fontSize: '0.9rem', lineHeight: '1.2' }}>
                                                            {formatEldoradoPrice(row.unit_price, true)}
                                                        </div>
                                                        <div style={{ padding: '2px 5px', borderRadius: '4px', background: '#252932', border: '1px solid rgba(255,255,255,0.1)', color: '#ccc', fontWeight: 'bold', fontSize: '0.75rem', lineHeight: '1.2' }}>
                                                            {formatEldoradoPrice(row.unit_price, false)}
                                                        </div>
                                                    </div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right' }}>{row.stock?.toLocaleString() || 0}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                        <Pagination currentPage={eldoradoPage} totalItems={eldoradoSortedBook.length} onPageChange={setEldoradoPage} />
                    </div>

                    {/* Qiandao Live Order Book */}
                    <div style={styles.tableCard}>
                        <div style={styles.tableHeader}>
                            <span style={{ color: theme.qiandao }}>📖 Qiandao Live Order Book</span>
                            <span style={{ fontSize: '0.75rem', color: theme.textSec }}>Active Buyers (Highest Price first)</span>
                        </div>
                        <div style={styles.tableWrapper}>
                            <table style={styles.table}>
                                <thead>
                                    <tr>
                                        <th style={{ ...styles.th, width: '30px' }}>#</th>
                                        <th style={styles.th}>Buyer</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Price (VND / RMB)</th>
                                        <th style={{ ...styles.th, textAlign: 'right' }}>Stock</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {padOrderBook((qiandaoMarketData.order_book || []).slice((qiandaoPage - 1) * 10, qiandaoPage * 10), 10).map((row, index) => {
                                        const i = (qiandaoPage - 1) * 10 + index;
                                        if (!row) {
                                            return (
                                                <tr key={index} style={{ backgroundColor: index % 2 === 0 ? 'transparent' : theme.tableOdd }}>
                                                    <td style={{ ...styles.td, color: '#666' }}>{i + 1}</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                    <td style={styles.td}>&nbsp;</td>
                                                </tr>
                                            );
                                        }
                                        const bg = index % 2 === 0 ? 'transparent' : theme.tableOdd;
                                        return (
                                            <tr key={index} style={{ backgroundColor: bg, transition: '0.2s' }}>
                                                <td style={{ ...styles.td, color: '#666' }}>{i + 1}</td>
                                                <td style={{ ...styles.td, fontWeight: 'bold' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                        {row.seller && row.seller.toLowerCase() === 'gegeteam' && (
                                                            <img src="/media__1782216597739.png" alt="Gege Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: `1px solid ${theme.qiandao}` }} />
                                                        )}
                                                        <span>{row.seller}</span>
                                                    </div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                                                        <div style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(0, 230, 118, 0.15)', border: '1px solid rgba(0, 230, 118, 0.3)', color: theme.qiandao, fontWeight: '900', fontSize: '0.9rem', lineHeight: '1.2' }}>
                                                            {formatDD373Price(row.unit_price, true)}
                                                        </div>
                                                        <div style={{ padding: '2px 5px', borderRadius: '4px', background: '#252932', border: '1px solid rgba(255,255,255,0.1)', color: '#ccc', fontWeight: 'bold', fontSize: '0.75rem', lineHeight: '1.2' }}>
                                                            {formatDD373Price(row.unit_price, false)}
                                                        </div>
                                                    </div>
                                                </td>
                                                <td style={{ ...styles.td, textAlign: 'right' }}>{row.stock?.toLocaleString() || 0}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                        <Pagination currentPage={qiandaoPage} totalItems={(qiandaoMarketData.order_book || []).length} onPageChange={setQiandaoPage} />
                    </div>


                </div>

            </div>
        </div>
    );
};

export default App;
