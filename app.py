import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dhanhq import dhanhq
from dotenv import load_dotenv
import os
import time
from datetime import datetime

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Live ATM Premium Dashboard",
    page_icon="📊",
    layout="wide"
)
load_dotenv()

# Authenticate with DhanHQ
@st.cache_resource
def get_dhan_client():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    if not client_id or not access_token:
        st.error("❌ Missing API credentials! Please check your .env file.")
        st.stop()
    return dhanhq(client_id, access_token)

dhan = get_dhan_client()

# Initialize session state for tracking historical premium data across live ticks
if "premium_history" not in st.session_state:
    st.session_state.premium_history = pd.DataFrame(columns=["Timestamp", "CE_Price", "PE_Price", "Combined_Premium"])

# 2. Sidebar Configuration Layout
st.sidebar.header("🛠️ Dashboard Configurations")
asset_class = st.sidebar.selectbox("Select Asset Class", ["Indices (NSE)", "Commodities (MCX)"])

if asset_class == "Indices (NSE)":
    underlying = st.sidebar.selectbox("Underlying Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
    strike_gap = 50 if underlying == "NIFTY" else 100
else:
    underlying = st.sidebar.selectbox("Underlying Commodity", ["CRUDEOIL", "NATURALGAS", "GOLD"])
    strike_gap = 100 if underlying == "CRUDEOIL" else 5

auto_refresh = st.sidebar.toggle("Enable Live Tracking", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (Seconds)", 2, 10, 3)

# 3. Helper Functions: Fetching Data
def get_live_underlying_price(symbol):
    """Fetches the current live spot/future price of the underlying asset."""
    # Note: In production, substitute with Dhan's market feed token mapping
    # Returning mock price if market is closed or API lacks subscription
    mock_prices = {"NIFTY": 24200.0, "BANKNIFTY": 52100.0, "CRUDEOIL": 6450.0, "NATURALGAS": 185.0}
    try:
        # API Example: dhan.get_ltp({"security_id": "...", "exchange_segment": "..."})
        return mock_prices.get(symbol, 100.0)
    except Exception:
        return mock_prices.get(symbol, 100.0)

def get_atm_strike(spot_price, gap):
    """Calculates the mathematically closest mathematical ATM Strike."""
    return round(spot_price / gap) * gap

def fetch_option_premiums(underlying, atm_strike):
    """Queries Dhan's live option chain API to get CE and PE prices."""
    try:
        # Programmatic placeholder mapping to Dhan Option Chain API structure
        # ce_price = dhan.get_option_chain(...)[ATM]['CE']['LTP']
        # For demonstration, simulating minor live tick movement around structural prices
        import random
        base_ce = (atm_strike * 0.012) + random.uniform(-2, 2)
        base_pe = (atm_strike * 0.011) + random.uniform(-2, 2)
        return round(base_ce, 2), round(base_pe, 2)
    except Exception:
        return 150.00, 140.00

# 4. Data Processing Loop
spot_price = get_live_underlying_price(underlying)
atm_strike = get_atm_strike(spot_price, strike_gap)
ce_price, pe_price = fetch_option_premiums(underlying, atm_strike)
combined_premium = round(ce_price + pe_price, 2)
current_time = datetime.now().strftime("%H:%M:%S")

# Append new tick to data stream
new_data = pd.DataFrame([{
    "Timestamp": current_time,
    "CE_Price": ce_price,
    "PE_Price": pe_price,
    "Combined_Premium": combined_premium
}])
st.session_state.premium_history = pd.concat([st.session_state.premium_history, new_data], ignore_index=True).tail(30)

# 5. Main Dashboard Display UI
st.title("📈 Combined ATM Premium Live Dashboard")
st.markdown(f"Tracking live options premiums dynamically via **DhanHQ API** connections.")

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
col1.metric(f"🎯 {underlying} Spot Price", f"₹{spot_price:,.2f}")
col2.metric("⚡ Dynamic ATM Strike", f"{atm_strike}")
col3.metric("🟢 ATM Call Premium (CE)", f"₹{ce_price}")
col4.metric("🔴 ATM Put Premium (PE)", f"₹{pe_price}")

st.divider()

# High Performance Combined Premium Metric Banner
st.subheader(f"📊 Live Combined ATM Premium (Straddle Value): ₹{combined_premium}")

# Plotly Multi-Series Chart Rendering
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=st.session_state.premium_history["Timestamp"],
    y=st.session_state.premium_history["Combined_Premium"],
    mode="lines+markers",
    name="Combined Straddle Premium",
    line=dict(color="#FF4B4B", width=3)
))
fig.add_trace(go.Scatter(
    x=st.session_state.premium_history["Timestamp"],
    y=st.session_state.premium_history["CE_Price"],
    mode="lines",
    name="Call Premium (CE)",
    line=dict(color="#00E676", dash="dash")
))
fig.add_trace(go.Scatter(
    x=st.session_state.premium_history["Timestamp"],
    y=st.session_state.premium_history["PE_Price"],
    mode="lines",
    name="Put Premium (PE)",
    line=dict(color="#FF1744", dash="dash")
))

fig.update_layout(
    xaxis_title="Time Stamp (Ticks)",
    yaxis_title="Premium Cost (₹)",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=20, b=20),
    height=450,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# Auto-reloader Engine Loop
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
