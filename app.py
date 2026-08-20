import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ============================================================
# PAGE CONFIG & CUSTOM BLOOMBERG CSS
# ============================================================
st.set_page_config(page_title="QUANT TERMINAL", layout="wide", page_icon="🟧")

BLOOMBERG_CSS = """
<style>
/* GLOBAL DARK THEME */
.stApp {
    background-color: #0A0E1A !important;
    color: #E8EAF0 !important;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background-color: #0F1420 !important;
    border-right: 1px solid #1E2638 !important;
}

/* HEADERS */
h1, h2, h3, h4 {
    color: #FF8C00 !important;
    font-family: 'Consolas', monospace !important;
    letter-spacing: 1px;
}

/* METRIC CARDS */
[data-testid="stMetric"] {
    background-color: #141B2D;
    border: 1px solid #1E2638;
    border-left: 3px solid #FF8C00;
    border-radius: 4px;
    padding: 12px;
}
[data-testid="stMetricLabel"] {
    color: #8892A8 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}
[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-family: 'Consolas', monospace !important;
    font-size: 1.5rem !important;
    font-weight: bold !important;
}

/* DATAFRAME */
[data-testid="stDataFrame"] {
    font-family: 'Consolas', monospace !important;
    font-size: 0.8rem !important;
}

/* BUTTONS */
.stButton > button {
    background-color: #FF8C00 !important;
    color: #000000 !important;
    border: none !important;
    font-family: 'Consolas', monospace !important;
    font-weight: bold !important;
    letter-spacing: 1px !important;
}
.stButton > button:hover {
    background-color: #FFA500 !important;
}

/* SLIDERS */
.stSlider > div > div {
    color: #8892A8 !important;
}

/* STATUS BAR */
.status-bar {
    background-color: #0F1420;
    border-top: 1px solid #1E2638;
    border-bottom: 1px solid #1E2638;
    padding: 8px 16px;
    font-family: 'Consolas', monospace;
    font-size: 0.8rem;
    color: #8892A8;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #00FF88;
    margin-right: 8px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* TICKER TAPE */
.ticker-tape {
    background-color: #000000;
    border-bottom: 2px solid #FF8C00;
    padding: 6px 0;
    overflow: hidden;
    white-space: nowrap;
    font-family: 'Consolas', monospace;
    font-size: 0.85rem;
}
.ticker-content {
    display: inline-block;
    animation: scroll 40s linear infinite;
}
@keyframes scroll {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}
.ticker-up { color: #00FF88; }
.ticker-down { color: #FF4444; }
.ticker-symbol { color: #FFFFFF; font-weight: bold; }

/* PANELS */
.panel {
    background-color: #141B2D;
    border: 1px solid #1E2638;
    border-radius: 4px;
    padding: 16px;
    margin-bottom: 12px;
}
.panel-title {
    color: #FF8C00;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 12px;
    border-bottom: 1px solid #1E2638;
    padding-bottom: 6px;
}

/* HIDE STREAMLIT BRANDING */
#MainMenu, header, footer {visibility: hidden;}
</style>
"""
st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)

# ============================================================
# HEADER & STATUS BAR
# ============================================================
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

st.markdown(f"""
<div style='background: linear-gradient(90deg, #0A0E1A 0%, #141B2D 100%); 
            padding: 20px; border-bottom: 2px solid #FF8C00;'>
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div>
            <h1 style='margin: 0; color: #FF8C00; font-size: 1.8rem; letter-spacing: 3px;'>
                ▌QUANT TERMINAL
            </h1>
            <div style='color: #8892A8; font-size: 0.75rem; letter-spacing: 2px;'>
                INSTITUTIONAL SWING TRADING DESK • v2.0
            </div>
        </div>
        <div style='text-align: right; font-family: Consolas, monospace;'>
            <div style='color: #00FF88; font-size: 0.85rem;'>
                <span class='status-indicator'></span>LIVE • NSE/BSE
            </div>
            <div style='color: #8892A8; font-size: 0.75rem;'>
                {now}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR: COMMAND PALETTE
# ============================================================
with st.sidebar:
    st.markdown("### ⌨️ COMMAND PALETTE")
    
    uploaded_file = st.file_uploader("📂 LOAD DATA FEED", type=['xlsx'])
    
    st.markdown("---")
    st.markdown("#### 🎯 FILTER PARAMETERS")
    
    preset = st.selectbox("Quick Preset", [
        "🟢 Conservative (Large Cap)",
        "🟡 Aggressive (Mid Cap)",
        "🔴 Momentum Hunter",
        "⚙️ Custom"
    ])
    
    if preset == "🟢 Conservative (Large Cap)":
        mcap_def, min_margin_def, min_1m_def = 10000, 8, 10
    elif preset == "🟡 Aggressive (Mid Cap)":
        mcap_def, min_margin_def, min_1m_def = 3000, 5, 15
    elif preset == "🔴 Momentum Hunter":
        mcap_def, min_margin_def, min_1m_def = 2000, 3, 25
    else:
        mcap_def, min_margin_def, min_1m_def = 2000, 5, 15
    
    min_mcap = st.slider("MIN MARKET CAP (₹ Cr)", 0, 100000, mcap_def, step=500)
    min_margin = st.slider("MIN NET MARGIN (%)", 0, 50, min_margin_def)
    min_1m = st.slider("MIN 1M MOMENTUM (%)", 0, 100, min_1m_def)
    max_1w = st.slider("MAX 1W PULLBACK (%)", -10, 10, 3)
    require_leverage = st.checkbox("Require Operating Leverage", value=True)
    hide_missing = st.checkbox("Hide Incomplete Data", value=True)
    
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
    df = df.replace(['ERROR:#N/A', 'ERROR: #N/A', '#N/A', 'N/A', 'inf', '-inf'], np.nan)
    
    # APPLY FILTERS
    filtered = df.copy()
    if hide_missing:
        filtered = filtered[filtered['Data_Quality'] == '✅ Clean']
    filtered = filtered[filtered['MarCap_Cr'] >= min_mcap]
    if require_leverage:
        filtered = filtered[filtered['YoY_NP_Growth_Pct'] > filtered['YoY_Rev_Growth_Pct']]
        filtered = filtered[filtered['NetMargin_Jun26_Pct'] >= min_margin]
    filtered = filtered[
        (filtered['Ret_1M'] >= min_1m) & 
        (filtered['Ret_1W'] <= max_1w)
    ]
    filtered = filtered.sort_values('YoY_NP_Growth_Pct', ascending=False)
    
    # ========================================================
    # TICKER TAPE (Top Movers)
    # ========================================================
    top_movers = df.nlargest(8, 'Ret_1M')[['Symbol', 'Ret_1M']].values.tolist()
    ticker_html = "<div class='ticker-tape'><div class='ticker-content'>"
    for sym, ret in top_movers:
        color_class = 'ticker-up' if ret > 0 else 'ticker-down'
        arrow = '▲' if ret > 0 else '▼'
        ticker_html += f"<span class='ticker-symbol'>{sym}</span> <span class='{color_class}'>{arrow} {ret:.2f}%</span> &nbsp;&nbsp;│&nbsp;&nbsp; "
    ticker_html += "</div></div>"
    st.markdown(ticker_html, unsafe_allow_html=True)
    
    st.markdown("<br>")
    
    # ========================================================
    # METRIC CARDS
    # ========================================================
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("SETUPS FOUND", len(filtered))
    c2.metric("AVG MKT CAP", f"₹{filtered['MarCap_Cr'].mean():,.0f} Cr" if not filtered.empty else "—")
    c3.metric("AVG NP GROWTH", f"{filtered['YoY_NP_Growth_Pct'].mean():.1f}%" if not filtered.empty else "—")
    c4.metric("AVG 1M RETURN", f"{filtered['Ret_1M'].mean():.1f}%" if not filtered.empty else "—")
    c5.metric("UNIVERSE SIZE", len(df))
    
    st.markdown("<br>")
    
    # ========================================================
    # MULTI-PANEL GRID
    # ========================================================
    left_col, right_col = st.columns([1.2, 1])
    
    with left_col:
        st.markdown("#### 📊 MOMENTUM vs FUNDAMENTALS (The Sweet Spot)")
        if not filtered.empty:
            fig = px.scatter(
                filtered, x='Ret_1M', y='YoY_NP_Growth_Pct',
                size='MarCap_Cr', color='Industry',
                hover_name='Symbol',
                size_max=40,
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig.update_layout(
                plot_bgcolor='#141B2D',
                paper_bgcolor='#141B2D',
                font=dict(family='Consolas', color='#8892A8'),
                xaxis=dict(gridcolor='#1E2638', title='1M Return (%)'),
                yaxis=dict(gridcolor='#1E2638', title='YoY NP Growth (%)'),
                legend=dict(bgcolor='rgba(0,0,0,0)'),
                margin=dict(l=40, r=20, t=20, b=40),
                height=420
            )
            # Add quadrant lines
            fig.add_vline(x=filtered['Ret_1M'].median(), line_dash="dash", line_color="#FF8C00", opacity=0.5)
            fig.add_hline(y=filtered['YoY_NP_Growth_Pct'].median(), line_dash="dash", line_color="#FF8C00", opacity=0.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No setups match current filters. Adjust parameters.")
    
    with right_col:
        st.markdown("#### 🌡️ SECTOR RELATIVE STRENGTH")
        if not filtered.empty:
            sector = filtered.groupby('Industry').agg({
                'Ret_1M': 'mean',
                'Symbol': 'count'
            }).rename(columns={'Symbol': 'Count'}).sort_values('Ret_1M', ascending=True)
            
            fig_heat = go.Figure(go.Heatmap(
                z=sector[['Ret_1M']].values,
                x=['1M Avg Return'],
                y=sector.index,
                colorscale=[[0, '#1E2638'], [0.5, '#FF8C00'], [1, '#00FF88']],
                showscale=False,
                text=[[f"{v:.1f}%"] for v in sector['Ret_1M'].values],
                texttemplate="%{text}",
                textfont=dict(family='Consolas', size=11, color='white')
            ))
            fig_heat.update_layout(
                plot_bgcolor='#141B2D',
                paper_bgcolor='#141B2D',
                font=dict(family='Consolas', color='#8892A8'),
                xaxis=dict(showticklabels=False),
                yaxis=dict(gridcolor='#1E2638'),
                margin=dict(l=10, r=10, t=10, b=10),
                height=420
            )
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("No sector data available.")
    
    st.markdown("---")
    
    # ========================================================
    # PROFESSIONAL DATA TABLE
    # ========================================================
    st.markdown("#### 📋 WATCHLIST • INSTITUTIONAL CONFLUENCE SETUPS")
    
    if not filtered.empty:
        display_cols = ['Symbol', 'Industry', 'CMP_Rs', 'MarCap_Cr', 
                        'YoY_Rev_Growth_Pct', 'YoY_NP_Growth_Pct', 'NetMargin_Jun26_Pct',
                        'Ret_1M', 'Ret_1W', 'Ret_1D']
        
        display_df = filtered[display_cols].copy()
        
        # Color-code returns
        def color_returns(val):
            if pd.isna(val): return ''
            if val > 5: return 'color: #00FF88; font-weight: bold'
            elif val > 0: return 'color: #00FF88'
            elif val < -3: return 'color: #FF4444; font-weight: bold'
            elif val < 0: return 'color: #FF4444'
            return 'color: #8892A8'
        
        styled = display_df.style.format({
            'CMP_Rs': '₹{:,.2f}',
            'MarCap_Cr': '₹{:,.0f}',
            'YoY_Rev_Growth_Pct': '{:+.1f}%',
            'YoY_NP_Growth_Pct': '{:+.1f}%',
            'NetMargin_Jun26_Pct': '{:.1f}%',
            'Ret_1M': '{:+.2f}%',
            'Ret_1W': '{:+.2f}%',
            'Ret_1D': '{:+.2f}%'
           }).map(color_returns, subset=['Ret_1M', 'Ret_1W', 'Ret_1D', 
                                  'YoY_Rev_Growth_Pct', 'YoY_NP_Growth_Pct'])
        
        st.dataframe(styled, use_container_width=True, height=500)
        
        # ====================================================
        # POSITION SIZER OUTPUT
        # ====================================================
        st.markdown("---")
        st.markdown("#### 💼 RISK MANAGEMENT • POSITION SIZER")
        
        risk_amount = capital * (risk_pct / 100)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("MAX RISK ₹", f"₹{risk_amount:,.0f}")
        col_b.metric("STOP LOSS", f"{stop_loss_pct}%")
        col_c.metric("MAX POSITION SIZE", f"₹{risk_amount / (stop_loss_pct/100):,.0f}")
        
        st.caption(f"⚠️ Risk per trade: ₹{risk_amount:,.0f} | If stop-loss hit, loss = ₹{risk_amount:,.0f}")
    
    # ========================================================
    # FOOTER STATUS BAR
    # ========================================================
    st.markdown(f"""
    <div class='status-bar'>
        <div><span class='status-indicator'></span>DATA FEED: ACTIVE | SYMBOLS: {len(df)} | FILTERED: {len(filtered)}</div>
        <div>QUANT TERMINAL v2.0 | BLOOMBERG-STYLE INTERFACE | © 2026</div>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style='text-align: center; padding: 80px 20px; border: 1px dashed #FF8C00; 
                background-color: #141B2D; border-radius: 4px; margin-top: 40px;'>
        <h2 style='color: #FF8C00; letter-spacing: 3px;'>⚠ AWAITING DATA FEED</h2>
        <p style='color: #8892A8; font-family: Consolas, monospace;'>
            Upload your <code style='color: #00FF88;'>aug_dataai_IMPROVED.xlsx</code> file via the sidebar to initialize terminal.
        </p>
        <p style='color: #8892A8; font-size: 0.8rem; margin-top: 30px;'>
            TIP: Use keyboard shortcuts • Ctrl+R to refresh • Adjust filters in Command Palette
        </p>
    </div>
    """, unsafe_allow_html=True)
