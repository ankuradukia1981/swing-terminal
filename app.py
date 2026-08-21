import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from groq import Groq

# ============================================================
# 1. PAGE CONFIG & CSS
# ============================================================
st.set_page_config(page_title="Quant Terminal", layout="wide", page_icon="📊")

APPLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
.stApp { background: linear-gradient(180deg, #FBFBFD 0%, #F5F5F7 100%); color: #1D1D1F; font-family: 'Inter', sans-serif; }
[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 600 !important; }
[data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #86868B !important; font-weight: 500 !important; }
div[data-testid="stVerticalBlock"] > div { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px); border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.5); padding: 20px; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04); }
.stButton>button { background: #0071E3; color: white; border-radius: 980px; font-weight: 500; border: none; }
.stButton>button:hover { background: #0077ED; box-shadow: 0 4px 12px rgba(0, 113, 227, 0.3); }
</style>
"""
st.markdown(APPLE_CSS, unsafe_allow_html=True)

# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================
@st.cache_data(ttl=3600)
def load_data(ticker, period="2y"):
    data = yf.download(ticker, period=period, progress=False)
    # Handle yfinance multi-index columns if they appear
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    return data

def add_technical_indicators(df):
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STD_20'] = df['Close'].rolling(window=20).std()
    df['Upper_BB'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_BB'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def calculate_quant_metrics(df):
    df['Daily Return'] = df['Close'].pct_change()
    df['Cumulative Return'] = (1 + df['Daily Return']).cumprod() - 1
    mean_daily_return = df['Daily Return'].mean()
    std_daily_return = df['Daily Return'].std()
    
    cagr = (1 + df['Cumulative Return'].iloc[-1]) ** (252 / len(df)) - 1
    volatility = std_daily_return * np.sqrt(252)
    sharpe_ratio = (mean_daily_return * 252) / (volatility + 1e-9)
    
    rolling_max = df['Cumulative Return'].cummax()
    drawdown = (df['Cumulative Return'] - rolling_max) / (rolling_max + 1)
    
    return {
        "CAGR": f"{cagr:.2%}",
        "Volatility": f"{volatility:.2%}",
        "Sharpe Ratio": f"{sharpe_ratio:.2f}",
        "Max Drawdown": f"{drawdown.min():.2%}"
    }

@st.cache_resource
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY", "")
    return Groq(api_key=api_key) if api_key else None

def get_ai_analyst_report(ticker, metrics, current_price, price_change_pct):
    client = get_groq_client()
    if not client:
        return "⚠️ *Add your GROQ_API_KEY to `.streamlit/secrets.toml` to enable AI insights.*"
    
    prompt = f"""Act as a senior quant analyst. Ticker: {ticker}. Price: ${current_price:.2f} ({price_change_pct:.2f}%). 
    Metrics: CAGR: {metrics['CAGR']}, Vol: {metrics['Volatility']}, Sharpe: {metrics['Sharpe Ratio']}, Max DD: {metrics['Max Drawdown']}.
    Provide a concise, 3-bullet-point executive summary of this asset's risk/reward profile. Be data-driven."""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Analysis unavailable: {e}"

# ============================================================
# 3. MAIN APP LOGIC
# ============================================================
st.title("📊 Quant Terminal")
st.markdown("Advanced analytics, AI insights, and institutional-grade metrics.")

col1, col2 = st.columns([1, 3])
with col1:
    ticker = st.text_input("Ticker Symbol", "AAPL").upper()
    period = st.selectbox("Time Horizon", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=4)

if ticker:
    with st.spinner(f"Fetching data for {ticker}..."):
        df = load_data(ticker, period)
        df = add_technical_indicators(df)
        metrics = calculate_quant_metrics(df)
        
    current_price = float(df['Close'].iloc[-1])
    start_price = float(df['Close'].iloc[0])
    price_change_pct = ((current_price / start_price) - 1) * 100
    
    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", f"${current_price:.2f}", f"{price_change_pct:.2f}%")
    m2.metric("Sharpe Ratio", metrics["Sharpe Ratio"], help=">1.0 is good, >2.0 is excellent")
    m3.metric("Max Drawdown", metrics["Max Drawdown"], delta_color="inverse")
    m4.metric("Annual Volatility", metrics["Volatility"])

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📈 Price & Bands", "📉 RSI", "🤖 AI Analyst"])
    
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"))
        fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], name="Upper BB", line=dict(color="rgba(0,113,227,0.5)")))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="SMA 20", line=dict(color="#0071E3")))
        fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], name="Lower BB", line=dict(color="rgba(0,113,227,0.5)")))
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_white", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color="#FF9500")))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
        fig_rsi.update_layout(height=300, yaxis_range=[0, 100], template="plotly_white", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_rsi, use_container_width=True)

    with tab3:
        st.subheader(f"🤖 AI Quant Report: {ticker}")
        with st.spinner("Generating AI insights..."):
            report = get_ai_analyst_report(ticker, metrics, current_price, price_change_pct)
            st.markdown(report)
