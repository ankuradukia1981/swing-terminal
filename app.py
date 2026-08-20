import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import time

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="QUANT TERMINAL LIVE", layout="wide", page_icon="🟧")

# ============================================================
# BLOOMBERG CSS (same as before - abbreviated for space)
# ============================================================
BLOOMBERG_CSS = """
<style>
.stApp { background-color: #0A0E1A !important; color: #E8EAF0 !important; 
         font-family: 'Consolas', monospace !important; }
section[data-testid="stSidebar"] { background-color: #0F1420 !important; 
         border-right: 1px solid #1E2638 !important; }
h1, h2, h3, h4 { color: #FF8C00 !important; font-family: 'Consolas', monospace !important; }
[data-testid="stMetric"] { background-color: #141B2D; border: 1px solid #1E2638; 
         border-left: 3px solid #FF8C00; border-radius: 4px; padding: 12px; }
[data-testid="stMetricLabel"] { color: #8892A8 !important; font-size: 0.75rem !important; 
         text-transform: uppercase !important; letter-spacing: 1px !important; }
[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.5rem !important; 
         font-weight: bold !important; }
.status-bar { background-color: #0F1420; border-top: 1px solid #1E2638; 
         padding: 8px 16px; font-size: 0.8rem; color: #8892A8; 
         display: flex; justify-content: space-between; }
.status-indicator { display: inline-block; width: 8px; height: 8px; border-radius: 50%; 
         background-color: #00FF88; margin-right: 8px; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100% {opacity:1;} 50% {opacity:0.4;} }
.ticker-tape { background-color: #000; border-bottom: 2px solid #FF8C00; 
         padding: 6px 0; overflow: hidden; white-space: nowrap; font-size: 0.85rem; }
.ticker-content { display: inline-block; animation: scroll 40s linear infinite; }
@keyframes scroll { 0% {transform: translateX(100%);} 100% {transform: translateX(-100%);} }
.ticker-up { color: #00FF88; } .ticker-down { color: #FF4444; }
.ticker-symbol { color: #FFF; font-weight: bold; }
#MainMenu, header, footer {visibility: hidden;}
</style>
"""
st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)

# ============================================================
# HELPER: FETCH LIVE DATA FROM YAHOO FINANCE
# ============================================================
@st.cache_data(ttl=60)  # Cache for 60 seconds to avoid rate limits
def fetch_live_data(symbols):
    """Fetch live prices and calculate returns for a list of NSE symbols."""
    results = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            hist = ticker.history(period="1mo")
            if hist.empty:
                continue
            current_price = hist['Close'].iloc[-1]
            price_1d = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            price_1w = hist['Close'].iloc[-6] if len(hist) > 5 else current_price
            price_1m = hist['Close'].iloc[0]
            
            ret_1d = ((current_price - price_1d) / price_1d) * 100
            ret_1w = ((current_price - price_1w) / price_1w) * 100
            ret_1m = ((current_price - price_1m) / price_1m) * 100
            
            results.append({
                'Symbol': sym,
                'CMP_Live': round(current_price, 2),
                'Ret_1D_Live': round(ret_1d, 2),
                'Ret_1W_Live': round(ret_1w, 2),
                'Ret_1M_Live': round(ret_1m, 2)
            })
        except Exception as e:
            continue
    return pd.DataFrame(results)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_stock_detail(symbol):
    """Fetch detailed info for a single stock."""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        return {
            'name': info.get('longName', symbol),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'pe': info.get('trailingPE', 'N/A'),
            'pb': info.get('priceToBook', 'N/A'),
            'roe': info.get('returnOnEquity', 'N/A'),
            'mcap': info.get('marketCap', 0),
            'div_yield': info.get('dividendYield', 0),
            '52w_high': info.get('fiftyTwoWeekHigh', 'N/A'),
            '52w_low': info.get('fiftyTwoWeekLow', 'N/A'),
            'hist': ticker.history(period="6mo")
        }
    except:
        return None

# ============================================================
# HEADER
# ============================================================
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
st.markdown(f"""
<div style='background: linear-gradient(90deg, #0A0E1A 0%, #141B2D 100%); 
            padding: 20px; border-bottom: 2px solid #FF8C00;'>
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div>
            <h1 style='margin: 0; color: #FF8C00; font-size: 1.8rem; letter-spacing: 3px;'>
                ▌QUANT TERMINAL <span style='color:#00FF88;'>LIVE</span>
            </h1>
            <div style='color: #8892A8; font-size: 0.75rem; letter-spacing: 2px;'>
                REAL-TIME NSE DATA • YAHOO FINANCE API • v3.0
            </div>
        </div>
        <div style='text-align: right;'>
            <div style='color: #00FF88; font-size: 0.85rem;'>
                <span class='status-indicator'></span>LIVE FEED ACTIVE
            </div>
            <div style='color: #8892A8; font-size: 0.75rem;'>{now}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### ⌨️ COMMAND PALETTE")
    uploaded_file = st.file_uploader("📂 LOAD FUNDAMENTAL DATA", type=['xlsx'])
    
    st.markdown("---")
    st.markdown("#### 📡 LIVE DATA MODE")
    live_mode = st.toggle("Enable Live Prices (yfinance)", value=True, 
                          help="Fetches real-time NSE prices. Slower but accurate.")
    auto_refresh = st.toggle("Auto-Refresh (60s)", value=False)
    
    if auto_refresh and live_mode:
        time.sleep(60)
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### 🎯 FILTERS")
    min_mcap = st.slider("Min Market Cap (₹ Cr)", 0, 100000, 2000, step=500)
    min_margin = st.slider("Min Net Margin (%)", 0, 50, 5)
    min_1m = st.slider("Min 1M Return (%)", 0, 100, 15)
    max_1w = st.slider("Max 1W Pullback (%)", -10, 10, 3)
    require_leverage = st.checkbox("Require Operating Leverage", value=True)
    
    st.markdown("---")
    st.markdown("#### 💼 POSITION SIZER")
    capital = st.number_input("Total Capital (₹)", value=500000, step=50000)
    risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.5, step=0.5)
    stop_loss_pct = st.slider("Stop Loss (%)", 2.0, 15.0, 5.0, step=0.5)

# ============================================================
# MAIN CONTENT
# ============================================================
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    df = df.replace(['ERROR:#N/A', '#N/A', 'N/A', 'inf', '-inf'], np.nan)
    
    # Apply fundamental filters
    filtered = df[df['MarCap_Cr'] >= min_mcap].copy()
    if require_leverage:
        filtered = filtered[filtered['YoY_NP_Growth_Pct'] > filtered['YoY_Rev_Growth_Pct']]
        filtered = filtered[filtered['NetMargin_Jun26_Pct'] >= min_margin]
    filtered = filtered[filtered['Ret_1M'] >= min_1m]
    filtered = filtered[filtered['Ret_1W'] <= max_1w]
    filtered = filtered.sort_values('YoY_NP_Growth_Pct', ascending=False)
    
    # ========================================================
    # LIVE DATA INTEGRATION
    # ========================================================
    if live_mode and not filtered.empty:
        with st.spinner("📡 Fetching live NSE prices..."):
            symbols = filtered['Symbol'].head(30).tolist()  # Limit to avoid rate limits
            live_df = fetch_live_data(symbols)
            
            if not live_df.empty:
                # Merge live data with fundamental data
                filtered = filtered.merge(live_df, on='Symbol', how='left')
                # Override returns with live data where available
                for col in ['Ret_1D', 'Ret_1W', 'Ret_1M']:
                    live_col = f"{col}_Live"
                    if live_col in filtered.columns:
                        filtered[col] = filtered[live_col].fillna(filtered[col])
                if 'CMP_Live' in filtered.columns:
                    filtered['CMP_Rs'] = filtered['CMP_Live'].fillna(filtered['CMP_Rs'])
    
    # ========================================================
    # METRIC CARDS
    # ========================================================
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("SETUPS", len(filtered))
    c2.metric("LIVE FEED", "🟢 ACTIVE" if live_mode else "⚪ OFFLINE")
    c3.metric("AVG NP GROWTH", f"{filtered['YoY_NP_Growth_Pct'].mean():.1f}%" if not filtered.empty else "—")
    c4.metric("TOP GAINER", filtered['Ret_1M'].max() if not filtered.empty else 0)
    c5.metric("UNIVERSE", len(df))
    
    # ========================================================
    # TICKER TAPE (Live Top Movers)
    # ========================================================
    if not filtered.empty:
        top_movers = filtered.nlargest(10, 'Ret_1M')[['Symbol', 'Ret_1M']].values.tolist()
        ticker_html = "<div class='ticker-tape'><div class='ticker-content'>"
        for sym, ret in top_movers:
            color_class = 'ticker-up' if ret > 0 else 'ticker-down'
            arrow = '▲' if ret > 0 else '▼'
            ticker_html += f"<span class='ticker-symbol'>{sym}</span> <span class='{color_class}'>{arrow}{ret:.2f}%</span> │ "
        ticker_html += "</div></div>"
        st.markdown(ticker_html, unsafe_allow_html=True)
    
    st.markdown("<br>")
    
    # ========================================================
    # CHARTS
    # ========================================================
    left, right = st.columns([1.2, 1])
    
    with left:
        st.markdown("#### 📊 MOMENTUM vs FUNDAMENTALS")
        if not filtered.empty:
            fig = px.scatter(filtered, x='Ret_1M', y='YoY_NP_Growth_Pct',
                           size='MarCap_Cr', color='Industry', hover_name='Symbol',
                           size_max=40, color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(plot_bgcolor='#141B2D', paper_bgcolor='#141B2D',
                            font=dict(family='Consolas', color='#8892A8'),
                            xaxis=dict(gridcolor='#1E2638'), yaxis=dict(gridcolor='#1E2638'),
                            height=420)
            st.plotly_chart(fig, use_container_width=True)
    
    with right:
        st.markdown("#### 🌡️ SECTOR HEATMAP")
        if not filtered.empty:
            sector = filtered.groupby('Industry')['Ret_1M'].mean().sort_values(ascending=True)
            fig_h = go.Figure(go.Heatmap(
                z=sector.values.reshape(-1, 1), x=['1M Avg'], y=sector.index,
                colorscale=[[0, '#1E2638'], [0.5, '#FF8C00'], [1, '#00FF88']],
                showscale=False, text=[[f"{v:.1f}%"] for v in sector.values],
                texttemplate="%{text}", textfont=dict(size=11, color='white')
            ))
            fig_h.update_layout(plot_bgcolor='#141B2D', paper_bgcolor='#141B2D',
                              height=420, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_h, use_container_width=True)
    
    # ========================================================
    # WATCHLIST TABLE
    # ========================================================
    st.markdown("#### 📋 LIVE WATCHLIST")
    
    if not filtered.empty:
        display_cols = ['Symbol', 'Industry', 'CMP_Rs', 'MarCap_Cr', 
                       'YoY_NP_Growth_Pct', 'Ret_1M', 'Ret_1W', 'Ret_1D']
        
        display_df = filtered[display_cols].copy()
        
        def color_returns(val):
            if pd.isna(val): return ''
            if val > 5: return 'color: #00FF88; font-weight: bold'
            elif val > 0: return 'color: #00FF88'
            elif val < -3: return 'color: #FF4444; font-weight: bold'
            elif val < 0: return 'color: #FF4444'
            return 'color: #8892A8'
        
        styled = display_df.style.format({
            'CMP_Rs': '₹{:,.2f}', 'MarCap_Cr': '₹{:,.0f}',
            'YoY_NP_Growth_Pct': '{:+.1f}%',
            'Ret_1M': '{:+.2f}%', 'Ret_1W': '{:+.2f}%', 'Ret_1D': '{:+.2f}%'
        }).map(color_returns, subset=['Ret_1M', 'Ret_1W', 'Ret_1D', 'YoY_NP_Growth_Pct'])
        
        st.dataframe(styled, use_container_width=True, height=500)
        
        # ====================================================
        # STOCK DETAIL PANEL (NEW!)
        # ====================================================
        st.markdown("---")
        st.markdown("#### 🔍 STOCK DEEP DIVE (Click a Symbol)")
        
        selected = st.selectbox("Select Symbol for Analysis", 
                               filtered['Symbol'].tolist(), index=0)
        
        if selected:
            with st.spinner(f"Loading {selected}..."):
                detail = fetch_stock_detail(selected)
                if detail:
                    col_a, col_b, col_c, col_d, col_e = st.columns(5)
                    col_a.metric("P/E RATIO", f"{detail['pe']:.2f}" if isinstance(detail['pe'], (int, float)) else "N/A")
                    col_b.metric("P/B RATIO", f"{detail['pb']:.2f}" if isinstance(detail['pb'], (int, float)) else "N/A")
                    col_c.metric("ROE", f"{detail['roe']*100:.1f}%" if isinstance(detail['roe'], (int, float)) else "N/A")
                    col_d.metric("52W HIGH", f"₹{detail['52w_high']:,.2f}" if isinstance(detail['52w_high'], (int, float)) else "N/A")
                    col_e.metric("52W LOW", f"₹{detail['52w_low']:,.2f}" if isinstance(detail['52w_low'], (int, float)) else "N/A")
                    
                    # 6-month price chart
                    hist = detail['hist']
                    if not hist.empty:
                        fig_line = go.Figure()
                        fig_line.add_trace(go.Scatter(
                            x=hist.index, y=hist['Close'],
                            mode='lines', name=selected,
                            line=dict(color='#FF8C00', width=2),
                            fill='tozeroy', fillcolor='rgba(255,140,0,0.1)'
                        ))
                        fig_line.update_layout(
                            plot_bgcolor='#141B2D', paper_bgcolor='#141B2D',
                            font=dict(family='Consolas', color='#8892A8'),
                            xaxis=dict(gridcolor='#1E2638'), yaxis=dict(gridcolor='#1E2638'),
                            height=350, margin=dict(l=20, r=20, t=20, b=20),
                            title=f"{selected} • 6-MONTH PRICE ACTION"
                        )
                        st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.warning(f"Could not fetch live data for {selected}. Symbol may not be listed on NSE.")
        
        # ====================================================
        # POSITION SIZER
        # ====================================================
        st.markdown("---")
        st.markdown("#### 💼 RISK MANAGEMENT")
        risk_amount = capital * (risk_pct / 100)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("MAX RISK ₹", f"₹{risk_amount:,.0f}")
        col_b.metric("STOP LOSS", f"{stop_loss_pct}%")
        col_c.metric("MAX POSITION SIZE", f"₹{risk_amount / (stop_loss_pct/100):,.0f}")
    
    # ========================================================
    # STATUS BAR
    # ========================================================
    st.markdown(f"""
    <div class='status-bar'>
        <div><span class='status-indicator'></span>LIVE: {'ON' if live_mode else 'OFF'} | SYMBOLS: {len(df)} | FILTERED: {len(filtered)}</div>
        <div>QUANT TERMINAL v3.0 • yfinance API • © 2026</div>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style='text-align: center; padding: 80px 20px; border: 1px dashed #FF8C00; 
                background-color: #141B2D; border-radius: 4px; margin-top: 40px;'>
        <h2 style='color: #FF8C00;'>⚠ AWAITING DATA FEED</h2>
        <p style='color: #8892A8;'>Upload Excel file via sidebar to initialize terminal.</p>
    </div>
    """, unsafe_allow_html=True)
