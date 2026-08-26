import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import time
import random
from datetime import datetime

# 1. Secure Layout Config
st.set_page_config(
    page_title="Live ATM Premium Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize Session Data safely 
if "premium_history" not in st.session_state:
    st.session_state.premium_history = pd.DataFrame(columns=["Timestamp", "CE_Price", "PE_Price", "Combined_Premium"])

# 2. Sidebar Controls
st.sidebar.header("🛠️ Dashboard Configurations")
asset_class = st.sidebar.selectbox("Select Asset Class", ["Indices (NSE)", "Commodities (MCX)"])

if asset_class == "Indices (NSE)":
    underlying = st.sidebar.selectbox("Underlying Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
    strike_gap = 50 if underlying == "NIFTY" else 100
else:
    underlying = st.sidebar.selectbox("Underlying Commodity", ["CRUDEOIL", "NATURALGAS", "GOLD"])
    strike_gap = 100 if underlying == "CRUDEOIL" else 5

dashboard_view = st.sidebar.radio("Dashboard Layout", ["Single Panel View", "Multi-Panel Split View"])
auto_refresh = st.sidebar.toggle("Enable Live Tracking", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (Seconds)", 2, 10, 3)

# 3. Dynamic Calculation Mechanics (Safe Fallback Pipeline)
def get_live_market_data(symbol, gap):
    mock_spots = {"NIFTY": 24200.0, "BANKNIFTY": 52100.0, "FINNIFTY": 23400.0, "CRUDEOIL": 6450.0, "NATURALGAS": 185.0, "GOLD": 72000.0}
    spot = mock_spots.get(symbol, 100.0) + random.uniform(-10, 10)
    atm = round(spot / gap) * gap
    
    ce = round((atm * 0.012) + random.uniform(-2, 2), 2)
    pe = round((atm * 0.011) + random.uniform(-2, 2), 2)
    return round(spot, 2), atm, ce, pe

# Run tick generation
spot_price, atm_strike, ce_price, pe_price = get_live_market_data(underlying, strike_gap)
combined_premium = round(ce_price + pe_price, 2)
current_time = datetime.now().strftime("%H:%M:%S")

# Update Data Storage Frame
new_tick = pd.DataFrame([{"Timestamp": current_time, "CE_Price": ce_price, "PE_Price": pe_price, "Combined_Premium": combined_premium}])
st.session_state.premium_history = pd.concat([st.session_state.premium_history, new_tick], ignore_index=True).tail(30)

# 4. Render Interface Panels
st.title("📈 Combined ATM Premium Live Dashboard")

# Row 1: Quick Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric(f"🎯 {underlying} Spot", f"₹{spot_price:,.2f}")
m2.metric("⚡ ATM Strike", f"{atm_strike}")
m3.metric("🟢 Call Premium (CE)", f"₹{ce_price}")
m4.metric("🔴 Put Premium (PE)", f"₹{pe_price}")

st.divider()

if dashboard_view == "Single Panel View":
    st.subheader(f"📊 Live Straddle Value Tracker: ₹{combined_premium}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=st.session_state.premium_history["Timestamp"], y=st.session_state.premium_history["Combined_Premium"], mode="lines+markers", name="Straddle Premium", line=dict(color="#FF4B4B", width=3)))
    fig.update_layout(xaxis_title="Time", yaxis_title="Premium (₹)", height=400, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    panel_col1, panel_col2 = st.columns(2)
    with panel_col1:
        st.subheader("📊 Combined Straddle Line")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=st.session_state.premium_history["Timestamp"], y=st.session_state.premium_history["Combined_Premium"], mode="lines+markers", name="Straddle", line=dict(color="#FF4B4B")))
        fig1.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig1, use_container_width=True)
    with panel_col2:
        st.subheader("⚖️ Decoupled CE vs PE Divergence")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=st.session_state.premium_history["Timestamp"], y=st.session_state.premium_history["CE_Price"], mode="lines", name="CE Price", line=dict(color="#00E676")))
        fig2.add_trace(go.Scatter(x=st.session_state.premium_history["Timestamp"], y=st.session_state.premium_history["PE_Price"], mode="lines", name="PE Price", line=dict(color="#FF1744")))
        fig2.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

# 5. Safe Streamlit Re-run Loop
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
