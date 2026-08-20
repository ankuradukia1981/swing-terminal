import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from groq import Groq
from nsepython import NsePython
import requests
import json

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="QUANT TERMINAL PRO", layout="wide", page_icon="🟧")

# ============================================================
# BLOOMBERG CSS
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
.tab-container { background-color: #141B2D; border: 1px solid #1E2638; 
         border-radius: 4px; padding: 20px; margin-top: 20px; }
#MainMenu, header, footer {visibility: hidden;}
</style>
"""
st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
@st.cache_data(ttl=60)
def fetch_live_data(symbols):
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
        except:
            continue
    return pd.DataFrame(results)

@st.cache_data(ttl=300)
def fetch_stock_detail(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        news = ticker.news[:5] if ticker.news else []
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
            'hist': ticker.history(period="6mo"),
            'news': news
        }
    except:
        return None

def send_email_alert(subject, body, email_config):
    try:
        msg = MIMEMultipart()
        msg['From'] = email_config['sender_email']
        msg['To'] = email_config['receiver_email']
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        server.starttls()
        server.login(email_config['sender_email'], email_config['sender_password'])
        text = msg.as_string()
        server.sendmail(email_config['sender_email'], email_config['receiver_email'], text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {str(e)}")
        return False

def generate_ai_analysis(symbol, stock_data):
    try:
        client = Groq(api_key=st.session_state.get('groq_api_key'))
        
        prompt = f"""Analyze this Indian stock for swing trading:
Symbol: {symbol}
Current Price: ₹{stock_data.get('CMP_Rs', 'N/A')}
Market Cap: ₹{stock_data.get('MarCap_Cr', 'N/A')} Cr
1M Return: {stock_data.get('Ret_1M', 'N/A')}%
YoY Revenue Growth: {stock_data.get('YoY_Rev_Growth_Pct', 'N/A')}%
YoY Profit Growth: {stock_data.get('YoY_NP_Growth_Pct', 'N/A')}%
Net Margin: {stock_data.get('NetMargin_Jun26_Pct', 'N/A')}%

Provide a concise 3-point analysis:
1. Technical outlook (momentum, trend)
2. Fundamental strength (growth, margins)
3. Risk factors and recommendation

Keep it under 150 words."""
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Analysis unavailable: {str(e)}"

def fetch_options_chain(symbol):
    try:
        nse = NsePython()
        oc = nse.get_option_chain_stock(symbol)
        return oc
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
                ▌QUANT TERMINAL <span style='color:#00FF88;'>PRO</span>
            </h1>
            <div style='color: #8892A8; font-size: 0.75rem; letter-spacing: 2px;'>
                INSTITUTIONAL TRADING DESK • AI + LIVE DATA + F&O • v4.0
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
    live_mode = st.toggle("Enable Live Prices", value=True)
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
    
    st.markdown("---")
    st.markdown("#### 📧 EMAIL ALERTS")
    email_enabled = st.toggle("Enable Email Alerts", value=False)
    if email_enabled:
        st.session_state['email_config'] = {
            'sender_email': st.text_input("Sender Email (Gmail)"),
            'sender_password': st.text_input("App Password", type="password"),
            'receiver_email': st.text_input("Receiver Email"),
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587
        }
        st.caption("💡 Use Gmail App Password: https://myaccount.google.com/apppasswords")
    
    st.markdown("---")
    st.markdown("#### 🤖 AI ANALYSIS")
    st.session_state['groq_api_key'] = st.text_input("Groq API Key", type="password", 
                                                      help="Get free key: https://console.groq.com")

# ============================================================
# MAIN CONTENT WITH TABS
# ============================================================
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    df = df.replace(['ERROR:#N/A', '#N/A', 'N/A', 'inf', '-inf'], np.nan)
    
    # Apply filters
    filtered = df[df['MarCap_Cr'] >= min_mcap].copy()
    if require_leverage:
        filtered = filtered[filtered['YoY_NP_Growth_Pct'] > filtered['YoY_Rev_Growth_Pct']]
        filtered = filtered[filtered['NetMargin_Jun26_Pct'] >= min_margin]
    filtered = filtered[filtered['Ret_1M'] >= min_1m]
    filtered = filtered[filtered['Ret_1W'] <= max_1w]
    filtered = filtered.sort_values('YoY_NP_Growth_Pct', ascending=False)
    
    # Fetch live data if enabled
    if live_mode and not filtered.empty:
        with st.spinner("📡 Fetching live data..."):
            symbols = filtered['Symbol'].head(30).tolist()
            live_df = fetch_live_data(symbols)
            if not live_df.empty:
                filtered = filtered.merge(live_df, on='Symbol', how='left')
                for col in ['Ret_1D', 'Ret_1W', 'Ret_1M']:
                    live_col = f"{col}_Live"
                    if live_col in filtered.columns:
                        filtered[col] = filtered[live_col].fillna(filtered[col])
                if 'CMP_Live' in filtered.columns:
                    filtered['CMP_Rs'] = filtered['CMP_Live'].fillna(filtered['CMP_Rs'])
    
    # Ticker tape
    if not filtered.empty:
        top_movers = filtered.nlargest(10, 'Ret_1M')[['Symbol', 'Ret_1M']].values.tolist()
        ticker_html = "<div class='ticker-tape'><div class='ticker-content'>"
        for sym, ret in top_movers:
            color_class = 'ticker-up' if ret > 0 else 'ticker-down'
            arrow = '▲' if ret > 0 else '▼'
            ticker_html += f"<span class='ticker-symbol'>{sym}</span> <span class='{color_class}'>{arrow}{ret:.2f}%</span> │ "
        ticker_html += "</div></div>"
        st.markdown(ticker_html, unsafe_allow_html=True)
    
    # TABS
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 SCREENER", "🔍 STOCK DEEP DIVE", "💼 PORTFOLIO", "📈 OPTIONS CHAIN", "🤖 AI ANALYSIS"])
    
    # ========================================================
    # TAB 1: SCREENER
    # ========================================================
    with tab1:
        st.markdown("#### 📊 INSTITUTIONAL CONFLUENCE SCREENER")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("SETUPS", len(filtered))
        c2.metric("LIVE FEED", "🟢 ACTIVE" if live_mode else "⚪ OFFLINE")
        c3.metric("AVG NP GROWTH", f"{filtered['YoY_NP_Growth_Pct'].mean():.1f}%" if not filtered.empty else "—")
        c4.metric("TOP GAINER", f"{filtered['Ret_1M'].max():.1f}%" if not filtered.empty else "—")
        c5.metric("UNIVERSE", len(df))
        
        left, right = st.columns([1.2, 1])
        
        with left:
            st.markdown("##### MOMENTUM vs FUNDAMENTALS")
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
            st.markdown("##### SECTOR HEATMAP")
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
        
        st.markdown("##### WATCHLIST")
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
            
            # Email alert trigger
            if email_enabled and st.session_state.get('email_config', {}).get('sender_email'):
                if st.button("📧 Send Watchlist Alert"):
                    subject = f"🎯 Quant Terminal: {len(filtered)} Setups Found"
                    body = f"Top 5 setups:\n\n"
                    for _, row in filtered.head(5).iterrows():
                        body += f"{row['Symbol']} | {row['Industry']} | NP Growth: {row['YoY_NP_Growth_Pct']:.1f}% | 1M: {row['Ret_1M']:.2f}%\n"
                    
                    if send_email_alert(subject, body, st.session_state['email_config']):
                        st.success("✅ Alert sent successfully!")
    
    # ========================================================
    # TAB 2: STOCK DEEP DIVE
    # ========================================================
    with tab2:
        st.markdown("#### 🔍 STOCK DEEP DIVE WITH NEWS")
        
        selected = st.selectbox("Select Symbol", filtered['Symbol'].tolist() if not filtered.empty else [], index=0)
        
        if selected:
            with st.spinner(f"Loading {selected}..."):
                detail = fetch_stock_detail(selected)
                if detail:
                    col_a, col_b, col_c, col_d, col_e = st.columns(5)
                    col_a.metric("P/E", f"{detail['pe']:.2f}" if isinstance(detail['pe'], (int, float)) else "N/A")
                    col_b.metric("P/B", f"{detail['pb']:.2f}" if isinstance(detail['pb'], (int, float)) else "N/A")
                    col_c.metric("ROE", f"{detail['roe']*100:.1f}%" if isinstance(detail['roe'], (int, float)) else "N/A")
                    col_d.metric("52W HIGH", f"₹{detail['52w_high']:,.2f}" if isinstance(detail['52w_high'], (int, float)) else "N/A")
                    col_e.metric("52W LOW", f"₹{detail['52w_low']:,.2f}" if isinstance(detail['52w_low'], (int, float)) else "N/A")
                    
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
                    
                    # News feed
                    if detail['news']:
                        st.markdown("##### 📰 LATEST NEWS")
                        for article in detail['news']:
                            st.markdown(f"**[{article['title']}]({article['link']})**")
                            st.caption(f"{article['publisher']} • {datetime.fromtimestamp(article['providerPublishTime']).strftime('%Y-%m-%d %H:%M')}")
                            st.markdown("---")
    
    # ========================================================
    # TAB 3: PORTFOLIO TRACKER
    # ========================================================
    with tab3:
        st.markdown("#### 💼 PORTFOLIO TRACKER")
        
        if 'portfolio' not in st.session_state:
            st.session_state.portfolio = []
        
        # Add position
        st.markdown("##### ADD POSITION")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            new_symbol = st.text_input("Symbol")
        with col2:
            new_qty = st.number_input("Quantity", min_value=1, value=10)
        with col3:
            new_buy_price = st.number_input("Buy Price (₹)", min_value=0.0, value=100.0)
        with col4:
            if st.button("➕ Add Position"):
                st.session_state.portfolio.append({
                    'Symbol': new_symbol,
                    'Quantity': new_qty,
                    'Buy_Price': new_buy_price,
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
                st.success(f"✅ Added {new_symbol}")
        
        # Display portfolio
        if st.session_state.portfolio:
            st.markdown("##### CURRENT POSITIONS")
            portfolio_df = pd.DataFrame(st.session_state.portfolio)
            
            # Fetch live prices
            symbols = portfolio_df['Symbol'].tolist()
            live_prices = fetch_live_data(symbols)
            
            if not live_prices.empty:
                portfolio_df = portfolio_df.merge(live_prices[['Symbol', 'CMP_Live']], on='Symbol', how='left')
                portfolio_df['Current_Value'] = portfolio_df['Quantity'] * portfolio_df['CMP_Live']
                portfolio_df['Invested_Value'] = portfolio_df['Quantity'] * portfolio_df['Buy_Price']
                portfolio_df['P&L'] = portfolio_df['Current_Value'] - portfolio_df['Invested_Value']
                portfolio_df['P&L_%'] = (portfolio_df['P&L'] / portfolio_df['Invested_Value']) * 100
                
                st.dataframe(portfolio_df.style.format({
                    'Buy_Price': '₹{:,.2f}',
                    'CMP_Live': '₹{:,.2f}',
                    'Current_Value': '₹{:,.0f}',
                    'Invested_Value': '₹{:,.0f}',
                    'P&L': '₹{:,.0f}',
                    'P&L_%': '{:+.2f}%'
                }), use_container_width=True)
                
                total_invested = portfolio_df['Invested_Value'].sum()
                total_current = portfolio_df['Current_Value'].sum()
                total_pnl = portfolio_df['P&L'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("TOTAL INVESTED", f"₹{total_invested:,.0f}")
                c2.metric("CURRENT VALUE", f"₹{total_current:,.0f}")
                c3.metric("TOTAL P&L", f"₹{total_pnl:,.0f}", f"{(total_pnl/total_invested)*100:+.2f}%")
        
        # Remove position
        if st.session_state.portfolio:
            st.markdown("##### REMOVE POSITION")
            remove_symbol = st.selectbox("Select Symbol to Remove", [p['Symbol'] for p in st.session_state.portfolio])
            if st.button("🗑️ Remove"):
                st.session_state.portfolio = [p for p in st.session_state.portfolio if p['Symbol'] != remove_symbol]
                st.rerun()
    
    # ========================================================
    # TAB 4: OPTIONS CHAIN
    # ========================================================
    with tab4:
        st.markdown("#### 📈 OPTIONS CHAIN (F&O)")
        
        fno_symbols = filtered[filtered['Symbol'].isin(['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK'])]['Symbol'].tolist() if not filtered.empty else []
        
        if fno_symbols:
            oc_symbol = st.selectbox("Select F&O Symbol", fno_symbols)
            
            if oc_symbol:
                with st.spinner(f"Fetching options chain for {oc_symbol}..."):
                    oc_data = fetch_options_chain(oc_symbol)
                    
                    if oc_data:
                        st.markdown("##### CALL OPTIONS")
                        st.dataframe(oc_data['calls'].head(10), use_container_width=True)
                        
                        st.markdown("##### PUT OPTIONS")
                        st.dataframe(oc_data['puts'].head(10), use_container_width=True)
                    else:
                        st.warning("Could not fetch options chain. Symbol may not be in F&O segment.")
        else:
            st.info("No F&O symbols found in current watchlist. Add stocks like RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK to your data.")
    
    # ========================================================
    # TAB 5: AI ANALYSIS
    # ========================================================
    with tab5:
        st.markdown("#### 🤖 AI-POWERED STOCK ANALYSIS")
        
        if not st.session_state.get('groq_api_key'):
            st.warning("⚠️ Please enter your Groq API Key in the sidebar to enable AI analysis.")
            st.markdown("**Get your free API key:** https://console.groq.com")
        else:
            ai_symbol = st.selectbox("Select Symbol for AI Analysis", 
                                    filtered['Symbol'].tolist() if not filtered.empty else [], 
                                    key="ai_select")
            
            if ai_symbol:
                stock_row = filtered[filtered['Symbol'] == ai_symbol].iloc[0] if not filtered.empty else None
                
                if stock_row is not None:
                    if st.button("🧠 Generate AI Analysis"):
                        with st.spinner("Analyzing with AI..."):
                            analysis = generate_ai_analysis(ai_symbol, stock_row.to_dict())
                            st.markdown("##### ANALYSIS RESULT")
                            st.markdown(analysis)
    
    # STATUS BAR
    st.markdown(f"""
    <div class='status-bar'>
        <div><span class='status-indicator'></span>LIVE: {'ON' if live_mode else 'OFF'} | AI: {'ON' if st.session_state.get('groq_api_key') else 'OFF'} | SYMBOLS: {len(df)} | FILTERED: {len(filtered)}</div>
        <div>QUANT TERMINAL PRO v4.0 • © 2026</div>
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
