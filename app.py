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

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Quant Terminal", layout="wide", page_icon="📊")

# ============================================================
# APPLE-STYLE CSS
# ============================================================
APPLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* GLOBAL */
.stApp {
    background: linear-gradient(180deg, #FBFBFD 0%, #F5F5F7 100%);
    color: #1D1D1F;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(0, 0, 0, 0.1);
}

/* HEADERS */
h1 {
    font-size: 2.5rem;
    font-weight: 600;
    color: #1D1D1F;
    letter-spacing: -0.02em;
    margin-bottom: 0.5rem;
}
h2, h3, h4 {
    font-weight: 600;
    color: #1D1D1F;
    letter-spacing: -0.01em;
}

/* METRIC CARDS */
[data-testid="stMetric"] {
    background: white;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    transition: all 0.3s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    color: #86868B;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="stMetricValue"] {
    color: #1D1D1F;
    font-size: 2rem;
    font-weight: 600;
    letter-spacing: -0.02em;
}

/* BUTTONS */
.stButton > button {
    background: linear-gradient(180deg, #007AFF 0%, #0051D5 100%);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 24px;
    font-weight: 500;
    font-size: 0.95rem;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}
.stButton > button:hover {
    background: linear-gradient(180deg, #0051D5 0%, #003D99 100%);
    box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4);
    transform: translateY(-1px);
}

/* DATAFRAME */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(0, 0, 0, 0.03);
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    color: #86868B;
    font-weight: 500;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: white;
    color: #007AFF;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* SLIDERS */
.stSlider > div > div > div {
    background: #007AFF;
}

/* SELECTBOX */
.stSelectbox > div > div {
    border-radius: 12px;
    border: 1px solid rgba(0, 0, 0, 0.1);
}

/* HERO SECTION */
.hero-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 24px;
    padding: 48px;
    margin-bottom: 32px;
    color: white;
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
}
.hero-title {
    font-size: 3rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-bottom: 8px;
}
.hero-subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    font-weight: 400;
}

/* HIDE STREAMLIT BRANDING */
#MainMenu, header, footer {visibility: hidden;}
</style>
"""
st.markdown(APPLE_CSS, unsafe_allow_html=True)

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

@st.cache_data(ttl=120)
def fetch_options_chain(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        expirations = ticker.options
        if not expirations:
            return None
        
        exp_date = expirations[0]
        opt_chain = ticker.option_chain(exp_date)
        
        calls = opt_chain.calls[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].copy()
        puts = opt_chain.puts[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].copy()
        
        calls.columns = ['Strike', 'LTP', 'Bid', 'Ask', 'Volume', 'OI', 'IV']
        puts.columns = ['Strike', 'LTP', 'Bid', 'Ask', 'Volume', 'OI', 'IV']
        
        spot = ticker.history(period='1d')['Close'].iloc[-1]
        calls = calls[(calls['Strike'] >= spot * 0.9) & (calls['Strike'] <= spot * 1.1)]
        puts = puts[(puts['Strike'] >= spot * 0.9) & (puts['Strike'] <= spot * 1.1)]
        
        return {
            'calls': calls.sort_values('Strike'),
            'puts': puts.sort_values('Strike'),
            'expiry': exp_date,
            'spot': round(spot, 2)
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
        server.sendmail(email_config['sender_email'], email_config['receiver_email'], msg.as_string())
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
        
        # Hardcoded to Qwen 3.6 27B as requested
        completion = client.chat.completions.create(
            model="qwen-3.6-27b", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Analysis unavailable: {str(e)}"

# ============================================================
# HERO HEADER
# ============================================================
now = datetime.now().strftime("%B %d, %Y")

st.markdown(f"""
<div class='hero-section'>
    <div class='hero-title'>Quant Terminal</div>
    <div class='hero-subtitle'>Institutional-grade swing trading • {now}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## Settings")
    uploaded_file = st.file_uploader("Upload Data", type=['xlsx'])
    
    st.markdown("---")
    st.markdown("### Live Data")
    live_mode = st.toggle("Enable Live Prices", value=True)
    auto_refresh = st.toggle("Auto-Refresh (60s)", value=False)
    
    if auto_refresh and live_mode:
        time.sleep(60)
        st.rerun()
    
    st.markdown("---")
    st.markdown("### Filters")
    min_mcap = st.slider("Min Market Cap (₹ Cr)", 0, 100000, 2000, step=500)
    min_margin = st.slider("Min Net Margin (%)", 0, 50, 5)
    min_1m = st.slider("Min 1M Return (%)", 0, 100, 15)
    max_1w = st.slider("Max 1W Pullback (%)", -10, 10, 3)
    require_leverage = st.checkbox("Require Operating Leverage", value=True)
    
    st.markdown("---")
    st.markdown("### Position Sizer")
    capital = st.number_input("Total Capital (₹)", value=500000, step=50000)
    risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.5, step=0.5)
    stop_loss_pct = st.slider("Stop Loss (%)", 2.0, 15.0, 5.0, step=0.5)
    
    st.markdown("---")
    st.markdown("### Email Alerts")
    email_enabled = st.toggle("Enable Email Alerts", value=False)
    if email_enabled:
        st.session_state['email_config'] = {
            'sender_email': st.text_input("Sender Email"),
            'sender_password': st.text_input("App Password", type="password"),
            'receiver_email': st.text_input("Receiver Email"),
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587
        }
    
    st.markdown("---")
    st.markdown("### AI Analysis")
    st.session_state['groq_api_key'] = st.text_input("Groq API Key", type="password", help="Get free key: https://console.groq.com")

# ============================================================
# MAIN CONTENT
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
    
    # Fetch live data
    if live_mode and not filtered.empty:
        with st.spinner("Fetching live data..."):
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
    
    # ========================================================
    # METRIC CARDS
    # ========================================================
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Setups Found", len(filtered))
    col2.metric("Live Feed", "Active" if live_mode else "Offline")
    col3.metric("Avg NP Growth", f"{filtered['YoY_NP_Growth_Pct'].mean():.1f}%" if not filtered.empty else "—")
    col4.metric("Top Gainer", f"{filtered['Ret_1M'].max():.1f}%" if not filtered.empty else "—")
    col5.metric("Universe", len(df))
    
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Screener", "🔍 Stock Details", " Portfolio", "📈 Options", " AI Analysis"])
    
    # TAB 1: SCREENER
    with tab1:
        st.markdown("### Institutional Confluence Screener")
        
        left, right = st.columns([1.2, 1])
        
        with left:
            st.markdown("#### Momentum vs Fundamentals")
            if not filtered.empty:
                fig = px.scatter(filtered, x='Ret_1M', y='YoY_NP_Growth_Pct',
                               size='MarCap_Cr', color='Industry', hover_name='Symbol',
                               size_max=40, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family='Inter', color='#1D1D1F'),
                    xaxis=dict(gridcolor='rgba(0,0,0,0.05)', title='1M Return (%)'),
                    yaxis=dict(gridcolor='rgba(0,0,0,0.05)', title='YoY NP Growth (%)'),
                    height=450,
                    margin=dict(l=40, r=20, t=20, b=40)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with right:
            st.markdown("#### Sector Performance")
            if not filtered.empty:
                sector = filtered.groupby('Industry')['Ret_1M'].mean().sort_values(ascending=True)
                fig_bar = px.bar(
                    x=sector.values, y=sector.index,
                    orientation='h',
                    color=sector.values,
                    color_continuous_scale='Blues'
                )
                fig_bar.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family='Inter', color='#1D1D1F'),
                    xaxis=dict(gridcolor='rgba(0,0,0,0.05)', title='Avg 1M Return (%)'),
                    yaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
                    height=450,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("#### Watchlist")
        if not filtered.empty:
            display_cols = ['Symbol', 'Industry', 'CMP_Rs', 'MarCap_Cr', 
                           'YoY_NP_Growth_Pct', 'Ret_1M', 'Ret_1W', 'Ret_1D']
            display_df = filtered[display_cols].copy()
            
            def color_returns(val):
                if pd.isna(val): return ''
                if val > 5: return 'color: #34C759; font-weight: 600'
                elif val > 0: return 'color: #34C759'
                elif val < -3: return 'color: #FF3B30; font-weight: 600'
                elif val < 0: return 'color: #FF3B30'
                return 'color: #86868B'
            
            styled = display_df.style.format({
                'CMP_Rs': '₹{:,.2f}', 'MarCap_Cr': '₹{:,.0f}',
                'YoY_NP_Growth_Pct': '{:+.1f}%',
                'Ret_1M': '{:+.2f}%', 'Ret_1W': '{:+.2f}%', 'Ret_1D': '{:+.2f}%'
            }).map(color_returns, subset=['Ret_1M', 'Ret_1W', 'Ret_1D', 'YoY_NP_Growth_Pct'])
            
            st.dataframe(styled, use_container_width=True, height=500)
            
            if email_enabled and st.session_state.get('email_config', {}).get('sender_email'):
                if st.button("📧 Send Watchlist Alert"):
                    subject = f"Quant Terminal: {len(filtered)} Setups Found"
                    body = f"Top 5 setups:\n\n"
                    for _, row in filtered.head(5).iterrows():
                        body += f"{row['Symbol']} | {row['Industry']} | NP Growth: {row['YoY_NP_Growth_Pct']:.1f}% | 1M: {row['Ret_1M']:.2f}%\n"
                    
                    if send_email_alert(subject, body, st.session_state['email_config']):
                        st.success("✅ Alert sent successfully!")
    
    # TAB 2: STOCK DEEP DIVE
    with tab2:
        st.markdown("### Stock Deep Dive")
        
        selected = st.selectbox("Select Symbol", filtered['Symbol'].tolist() if not filtered.empty else [], index=0)
        
        if selected:
            with st.spinner(f"Loading {selected}..."):
                detail = fetch_stock_detail(selected)
                if detail:
                    col_a, col_b, col_c, col_d, col_e = st.columns(5)
                    col_a.metric("P/E", f"{detail['pe']:.2f}" if isinstance(detail['pe'], (int, float)) else "N/A")
                    col_b.metric("P/B", f"{detail['pb']:.2f}" if isinstance(detail['pb'], (int, float)) else "N/A")
                    col_c.metric("ROE", f"{detail['roe']*100:.1f}%" if isinstance(detail['roe'], (int, float)) else "N/A")
                    col_d.metric("52W High", f"₹{detail['52w_high']:,.2f}" if isinstance(detail['52w_high'], (int, float)) else "N/A")
                    col_e.metric("52W Low", f"₹{detail['52w_low']:,.2f}" if isinstance(detail['52w_low'], (int, float)) else "N/A")
                    
                    hist = detail['hist']
                    if not hist.empty:
                        fig_line = go.Figure()
                        fig_line.add_trace(go.Scatter(
                            x=hist.index, y=hist['Close'],
                            mode='lines', name=selected,
                            line=dict(color='#007AFF', width=2),
                            fill='tozeroy', fillcolor='rgba(0,122,255,0.1)'
                        ))
                        fig_line.update_layout(
                            plot_bgcolor='white', paper_bgcolor='white',
                            font=dict(family='Inter', color='#1D1D1F'),
                            xaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
                            yaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
                            height=350, margin=dict(l=20, r=20, t=20, b=20),
                            title=f"{selected} • 6-Month Price Action"
                        )
                        st.plotly_chart(fig_line, use_container_width=True)
                    
                    if detail['news']:
                        st.markdown("#### Latest News")
                        for article in detail['news']:
                            st.markdown(f"**[{article['title']}]({article['link']})**")
                            st.caption(f"{article['publisher']} • {datetime.fromtimestamp(article['providerPublishTime']).strftime('%B %d, %Y')}")
                            st.markdown("---")
    
    # TAB 3: PORTFOLIO
    with tab3:
        st.markdown("### Portfolio Tracker")
        
        if 'portfolio' not in st.session_state:
            st.session_state.portfolio = []
        
        st.markdown("#### Add Position")
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
        
        if st.session_state.portfolio:
            st.markdown("#### Current Positions")
            portfolio_df = pd.DataFrame(st.session_state.portfolio)
            symbols = portfolio_df['Symbol'].tolist()
            live_prices = fetch_live_data(symbols)
            
            if not live_prices.empty:
                portfolio_df = portfolio_df.merge(live_prices[['Symbol', 'CMP_Live']], on='Symbol', how='left')
                portfolio_df['Current_Value'] = portfolio_df['Quantity'] * portfolio_df['CMP_Live']
                portfolio_df['Invested_Value'] = portfolio_df['Quantity'] * portfolio_df['Buy_Price']
                portfolio_df['P&L'] = portfolio_df['Current_Value'] - portfolio_df['Invested_Value']
                portfolio_df['P&L_%'] = (portfolio_df['P&L'] / portfolio_df['Invested_Value']) * 100
                
                st.dataframe(portfolio_df.style.format({
                    'Buy_Price': '₹{:,.2f}', 'CMP_Live': '₹{:,.2f}',
                    'Current_Value': '₹{:,.0f}', 'Invested_Value': '₹{:,.0f}',
                    'P&L': '₹{:,.0f}', 'P&L_%': '{:+.2f}%'
                }), use_container_width=True)
                
                total_invested = portfolio_df['Invested_Value'].sum()
                total_current = portfolio_df['Current_Value'].sum()
                total_pnl = portfolio_df['P&L'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Invested", f"₹{total_invested:,.0f}")
                c2.metric("Current Value", f"₹{total_current:,.0f}")
                c3.metric("Total P&L", f"₹{total_pnl:,.0f}", f"{(total_pnl/total_invested)*100:+.2f}%")
        
        if st.session_state.portfolio:
            st.markdown("#### Remove Position")
            remove_symbol = st.selectbox("Select Symbol to Remove", [p['Symbol'] for p in st.session_state.portfolio])
            if st.button("🗑️ Remove"):
                st.session_state.portfolio = [p for p in st.session_state.portfolio if p['Symbol'] != remove_symbol]
                st.rerun()
    
    # TAB 4: OPTIONS CHAIN
    with tab4:
        st.markdown("### Options Chain")
        
        fno_list = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 
                   'SBIN', 'ITC', 'LT', 'HINDUNILVR', 'BAJFINANCE',
                   'TATAMOTORS', 'MARUTI', 'SUNPHARMA', 'WIPRO', 'ADANIENT']
        
        oc_symbol = st.selectbox("Select F&O Symbol", fno_list, key="oc_select")
        
        if oc_symbol:
            with st.spinner(f"Fetching options chain for {oc_symbol}..."):
                oc_data = fetch_options_chain(oc_symbol)
                
                if oc_data:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Spot Price", f"₹{oc_data['spot']:,.2f}")
                    c2.metric("Expiry", oc_data['expiry'])
                    c3.metric("PCR (OI)", f"{oc_data['puts']['OI'].sum() / max(oc_data['calls']['OI'].sum(), 1):.2f}")
                    
                    st.markdown("---")
                    
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        st.markdown("#### Calls")
                        st.dataframe(
                            oc_data['calls'].style.format({
                                'Strike': '₹{:,.2f}', 'LTP': '₹{:,.2f}',
                                'Bid': '₹{:,.2f}', 'Ask': '₹{:,.2f}',
                                'Volume': '{:,.0f}', 'OI': '{:,.0f}', 'IV': '{:.2%}'
                            }),
                            use_container_width=True, height=400
                        )
                    
                    with col_right:
                        st.markdown("#### Puts")
                        st.dataframe(
                            oc_data['puts'].style.format({
                                'Strike': '₹{:,.2f}', 'LTP': '₹{:,.2f}',
                                'Bid': '{:,.2f}', 'Ask': '₹{:,.2f}',
                                'Volume': '{:,.0f}', 'OI': '{:,.0f}', 'IV': '{:.2%}'
                            }),
                            use_container_width=True, height=400
                        )
                    
                    st.markdown("#### Key Levels")
                    max_call_oi_strike = oc_data['calls'].loc[oc_data['calls']['OI'].idxmax(), 'Strike']
                    max_put_oi_strike = oc_data['puts'].loc[oc_data['puts']['OI'].idxmax(), 'Strike']
                    
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Max Call OI (Resistance)", f"₹{max_call_oi_strike:,.2f}")
                    mc2.metric("Max Put OI (Support)", f"₹{max_put_oi_strike:,.2f}")
                    mc3.metric("ATM Strike", f"₹{oc_data['spot']:,.2f}")
                else:
                    st.warning(f"Could not fetch options chain for {oc_symbol}.")
    
    # TAB 5: AI ANALYSIS
    with tab5:
        st.markdown("### AI-Powered Stock Analysis")
        st.caption("Powered by Qwen 3.6 27B")
        
        if not st.session_state.get('groq_api_key'):
            st.warning("Please enter your Groq API Key in the sidebar.")
            st.markdown("**Get your free API key:** https://console.groq.com")
        else:
            ai_symbol = st.selectbox("Select Symbol for AI Analysis", 
                                    filtered['Symbol'].tolist() if not filtered.empty else [], 
                                    key="ai_select")
            
            if ai_symbol:
                stock_row = filtered[filtered['Symbol'] == ai_symbol].iloc[0] if not filtered.empty else None
                
                if stock_row is not None:
                    if st.button(" Generate AI Analysis"):
                        with st.spinner("Analyzing with AI..."):
                            analysis = generate_ai_analysis(ai_symbol, stock_row.to_dict())
                            st.markdown("#### Analysis Result")
                            st.markdown(analysis)
    
    # FOOTER
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: #86868B; font-size: 0.85rem; padding: 20px;'>
        Quant Terminal • Built with Streamlit • {now}
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style='text-align: center; padding: 80px 20px; background: white; 
                border-radius: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-top: 40px;'>
        <h2 style='color: #1D1D1F; font-weight: 600;'>Upload Your Data</h2>
        <p style='color: #86868B; font-size: 1.1rem;'>
            Upload your Excel file via the sidebar to get started.
        </p>
    </div>
    """, unsafe_allow_html=True)
