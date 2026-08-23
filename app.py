"""
NSE / MCX Combined-Premium Terminal (v3)
------------------------------------------
A Bloomberg-terminal-style Streamlit dashboard tracking ATM (CE+PE) combined
option premium across NSE indices, NSE stocks, and MCX commodities, flagging
>=X% spikes from session baseline. Uses live Dhan API data when valid
credentials are configured, and falls back to a realistic simulated feed
otherwise (e.g. local dev without keys, market closed, API hiccup).

v3 rebuilds the UI around the latest static-HTML mockup's UX:
  - No chart on the main dashboard page. The main page is ticker + controls
    + a 2-panel row (Spike Alerts / Session Stats) + the full watchlist.
  - Click a watchlist row -> a dedicated full-page chart view opens
    (Spot vs Combined Premium vs Volume), with a "Back to Dashboard" button
    and a best-effort Esc-key handler. This is implemented with Streamlit's
    native dataframe row-selection + a session_state view flag rather than
    <a href> links, specifically so switching views does NOT blow away the
    session's accumulated tick history the way a real page navigation would.
  - Volume column/series (with volume surging alongside big premium moves,
    matching the reference tick model) feeds both the watchlist and the new
    chart's volume bars.
  - "Show only >= threshold" filter, Pause/Reset, and the same terminal
    palette + market-hours badge as before.

Run:
    streamlit run app.py

Requires a .env (local) or Streamlit Secrets (cloud) with:
    DHAN_CLIENT_ID=...
    DHAN_ACCESS_TOKEN=...
"""
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from config import (
    ALL_INSTRUMENTS, DEFAULT_THRESHOLD_PCT, DEFAULT_REFRESH_SECONDS, MAX_HISTORY_POINTS,
)
from dhan_service import (
    get_dhan, dhan_is_connected, fetch_atm_combined_premium,
    resolve_mcx_underlying, resolve_equity_underlying, search_scrip_master,
    init_sim_state, step_sim, is_market_hours,
)

st.set_page_config(
    page_title="NSE/MCX Premium Terminal",
    page_icon="\U0001F4C8",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================================
# THEME - matches the standalone premium-terminal.html palette exactly
# ==========================================================================
st.markdown("""
<style>
:root{
  --bg-void:#05080f; --bg-panel:#0d121d; --bg-alt:#151b2b; --border:#1e293b;
  --text-main:#e2e8f0; --text-dim:#64748b;
  --amber:#fbbf24; --cyan:#06b6d4; --up:#10b981; --down:#ef4444; --alert:#f97316;
}
html, body, [class*="css"]  { font-family: 'JetBrains Mono','SF Mono',Consolas,monospace; }
.stApp { background: var(--bg-void); }
section[data-testid="stSidebar"] { background: var(--bg-panel); border-right: 1px solid var(--border); }
h1, h2, h3, h4, h5 { color: var(--text-main) !important; font-family: 'JetBrains Mono',monospace !important; }
.term-header{
  display:flex; justify-content:space-between; align-items:center;
  padding:10px 4px 10px; border-bottom:1px solid var(--border); margin-bottom:2px;
}
.term-brand{ font-size:22px; font-weight:800; letter-spacing:1px; color:var(--amber); }
.term-sub{ font-size:11px; letter-spacing:2px; color:var(--text-dim); text-transform:uppercase; }
.badge{ display:inline-block; padding:3px 10px; border-radius:4px; font-size:11px; font-weight:700;
  letter-spacing:.5px; text-transform:uppercase; }
.badge-live{ background:rgba(16,185,129,.15); color:var(--up); border:1px solid rgba(16,185,129,.35); }
.badge-sim{ background:rgba(251,191,36,.15); color:var(--amber); border:1px solid rgba(251,191,36,.35); }
.badge-open{ background:rgba(16,185,129,.15); color:var(--up); border:1px solid rgba(16,185,129,.35); }
.badge-closed{ background:rgba(239,68,68,.15); color:var(--down); border:1px solid rgba(239,68,68,.35); }
.ticker-strip{
  display:flex; gap:20px; overflow-x:auto; white-space:nowrap; padding:7px 10px;
  background:var(--bg-alt); border:1px solid var(--border); border-radius:4px; margin-bottom:14px;
  font-size:11.5px;
}
.ticker-item b{ color:var(--text-main); margin-right:5px; }
.tick-up{ color:var(--up); font-weight:600; } .tick-down{ color:var(--down); font-weight:600; }
.tick-spike{ color:var(--alert); font-weight:800; }
.panel{
  background:var(--bg-alt); border:1px solid var(--border); border-radius:4px;
  padding:12px 14px; height:238px; overflow-y:auto;
}
.panel-title{
  font-size:11px; color:var(--amber); text-transform:uppercase; letter-spacing:1px;
  margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid var(--border);
  display:flex; justify-content:space-between; align-items:center;
}
.alert-row{
  display:flex; justify-content:space-between; align-items:center;
  padding:6px 8px; margin-bottom:6px; background:var(--bg-panel);
  border-left:3px solid var(--alert); border-radius:2px; font-size:11px;
}
.alert-time{ color:var(--text-dim); font-size:10px; }
.alert-sym{ color:var(--cyan); font-weight:700; }
.alert-pct{ color:var(--alert); font-weight:700; }
.empty-state{ color:var(--text-dim); font-style:italic; font-size:11px; text-align:center; padding:24px 0; }
.stat-row{ display:flex; justify-content:space-between; padding-bottom:7px; margin-bottom:7px;
  border-bottom:1px dashed var(--border); font-size:12px; }
.stat-lbl{ color:var(--text-dim); font-size:11px; } .stat-val{ color:var(--text-main); font-weight:700; font-size:13px; }
.wl-header{ font-size:11px; color:var(--amber); text-transform:uppercase; letter-spacing:1px;
  padding:8px 2px; }
.tag-spike{ background:rgba(249,115,22,.18); color:var(--alert); padding:2px 7px; border-radius:3px;
  font-size:10px; font-weight:700; }
.chart-title{ font-size:18px; color:var(--amber); font-weight:800; }
.chart-sub{ font-size:11px; color:var(--text-dim); margin-top:2px; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono',monospace; }
div[data-testid="stDataFrame"] { font-family: 'JetBrains Mono',monospace !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================================================
# STATE
# ==========================================================================
if "history" not in st.session_state:
    st.session_state.history = {sym: [] for sym in ALL_INSTRUMENTS}
if "sim_state" not in st.session_state:
    st.session_state.sim_state = {sym: init_sim_state(cfg) for sym, cfg in ALL_INSTRUMENTS.items()}
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "resolved_ids" not in st.session_state:
    st.session_state.resolved_ids = {}
if "paused" not in st.session_state:
    st.session_state.paused = False
if "spike_count_today" not in st.session_state:
    st.session_state.spike_count_today = 0
if "chart_open" not in st.session_state:
    st.session_state.chart_open = False
if "active_sym" not in st.session_state:
    st.session_state.active_sym = "NIFTY"

dhan_client = get_dhan()
LIVE = dhan_is_connected(dhan_client)
MARKET_OPEN = is_market_hours()

# controls persisted via widget `key=` so they're readable even from the
# chart-page view (where the widgets themselves aren't rendered)
threshold = st.session_state.get("threshold_input", DEFAULT_THRESHOLD_PCT)
only_spikes = st.session_state.get("only_spikes_cb", False)
refresh_secs = st.session_state.get("refresh_slider", DEFAULT_REFRESH_SECONDS)


# ==========================================================================
# SIDEBAR (live-data specific controls that don't belong on the static-style
# dashboard page itself)
# ==========================================================================
with st.sidebar:
    st.markdown("### \u25c6 TERMINAL CONTROLS")
    badge = '<span class="badge badge-live">\u25cf LIVE \u2014 DHAN</span>' if LIVE \
        else '<span class="badge badge-sim">\u25cf SIMULATED</span>'
    st.markdown(badge, unsafe_allow_html=True)
    if not LIVE:
        st.caption(
            "No valid Dhan credentials found (or connection failed) — running "
            "on a realistic simulated feed. Add DHAN_CLIENT_ID / "
            "DHAN_ACCESS_TOKEN to `.env` (local) or Streamlit Secrets (cloud) to go live."
        )
    st.slider("Auto-refresh (seconds)", 5, 60, DEFAULT_REFRESH_SECONDS, key="refresh_slider")
    st.toggle("Auto-refresh", value=True, key="auto_refresh_toggle")

    st.markdown("---")
    st.markdown("##### \U0001F50D Look up a Security ID")
    st.caption("MCX commodity underlyings roll monthly — search Dhan's "
               "live scrip master here instead of relying on a hardcoded ID.")
    q = st.text_input("Search trading symbol", placeholder="e.g. CRUDEOIL, RELIANCE")
    if q:
        try:
            hits = search_scrip_master(q, limit=15)
            if hits.empty:
                st.caption("No matches.")
            else:
                st.dataframe(hits, width="stretch", height=220)
        except Exception as e:
            st.caption(f"Lookup failed: {e}")


# ==========================================================================
# DATA FETCH
# ==========================================================================
def resolve_security_id(sym: str, cfg: dict):
    if cfg["security_id"] is not None:
        return cfg["security_id"], cfg["segment"]
    cached = st.session_state.resolved_ids.get(sym)
    if cached:
        return cached[0], cfg["segment"]
    if cfg["asset_class"] == "COMMODITY":
        sec_id, expiry, tsym = resolve_mcx_underlying(cfg["lookup_symbol"])
    elif cfg["asset_class"] == "EQUITY":
        sec_id = resolve_equity_underlying(cfg["lookup_symbol"])
    else:
        sec_id = None
    st.session_state.resolved_ids[sym] = (sec_id, cfg["segment"])
    return sec_id, cfg["segment"]


def get_reading(sym: str, cfg: dict):
    if LIVE:
        try:
            security_id, segment = resolve_security_id(sym, cfg)
            if security_id is not None:
                reading = fetch_atm_combined_premium(dhan_client, security_id, segment, cfg["strike_step"])
                if reading is not None:
                    reading["source"] = "LIVE"
                    return reading
        except Exception:
            pass
    reading = step_sim(st.session_state.sim_state[sym])
    reading["source"] = "SIM"
    return reading


# ---- refresh the WHOLE universe every cycle (unless paused) ----
current_records = {}
if not st.session_state.paused:
    now_str = datetime.now().strftime("%H:%M:%S")
    for sym, cfg in ALL_INSTRUMENTS.items():
        reading = get_reading(sym, cfg)
        hist = st.session_state.history[sym]
        baseline = hist[0]["combined_premium"] if hist else reading["combined_premium"]
        pct_chg = ((reading["combined_premium"] - baseline) / baseline) * 100 if baseline else 0.0
        is_spike = abs(pct_chg) >= threshold

        record = {**reading, "time": now_str, "pct_chg": pct_chg, "is_spike": is_spike, "baseline": baseline}
        hist.append(record)
        if len(hist) > MAX_HISTORY_POINTS:
            hist.pop(0)
        current_records[sym] = record

        if is_spike:
            already_recent = any(
                a["symbol"] == sym and (datetime.now() - a["ts"]).seconds < 25 for a in st.session_state.alerts
            )
            if not already_recent:
                st.session_state.alerts.insert(0, {
                    "symbol": sym, "ts": datetime.now(),
                    "time": now_str, "pct": pct_chg,
                    "premium": reading["combined_premium"], "spot": reading["spot"],
                })
                st.session_state.alerts = st.session_state.alerts[:50]
                st.session_state.spike_count_today += 1
else:
    for sym in ALL_INSTRUMENTS:
        h = st.session_state.history[sym]
        if h:
            current_records[sym] = h[-1]

label_to_sym = {cfg["label"]: sym for sym, cfg in ALL_INSTRUMENTS.items()}


# ==========================================================================
# CHART PAGE VIEW
# ==========================================================================
def render_chart_page():
    sym = st.session_state.active_sym
    cfg = ALL_INSTRUMENTS[sym]
    hist = st.session_state.history[sym]

    top = st.columns([4, 1])
    with top[0]:
        st.markdown(f'<div class="chart-title">{cfg["label"]} — Spot vs Combined Premium & Volume</div>',
                    unsafe_allow_html=True)
        if hist:
            last = hist[-1]
            st.markdown(
                f'<div class="chart-sub">ATM {last["atm_strike"]:,.0f} \u2022 IV {last.get("atm_iv","-")}% '
                f'\u2022 PCR {last.get("pcr","-")} \u2022 \u0394 CE/PE {last.get("ce_delta","-")}/'
                f'{last.get("pe_delta","-")} \u2022 Expiry {last.get("expiry","-")} \u2022 {last.get("source","-")}'
                f'</div>', unsafe_allow_html=True,
            )
    with top[1]:
        if st.button("\u2190 Back to Dashboard (Esc)", width="stretch", key="back_btn"):
            st.session_state.chart_open = False
            st.rerun()

    # best-effort Esc-key handler: reaches into the parent document (same
    # origin as the Streamlit page) and clicks the Back button for us.
    components.html("""
    <script>
    (function(){
      function bindEsc(){
        try {
          const doc = window.parent.document;
          if (doc.__premiumTerminalEscBound) return;
          doc.__premiumTerminalEscBound = true;
          doc.addEventListener('keydown', function(e){
            if (e.key === 'Escape') {
              const btns = doc.querySelectorAll('button');
              for (const b of btns) {
                if (b.innerText && b.innerText.indexOf('Back to Dashboard') !== -1) { b.click(); break; }
              }
            }
          });
        } catch (err) {}
      }
      bindEsc();
    })();
    </script>
    """, height=0)

    if not hist:
        st.info("No ticks recorded yet for this symbol.")
        return

    df = pd.DataFrame(hist)
    baseline = df.iloc[0]["combined_premium"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["time"], y=df["volume"], name="Volume",
        marker_color="rgba(100,116,139,0.35)", yaxis="y3",
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["combined_premium"], name="Combined Premium",
        line=dict(color="#fbbf24", width=2.5), fill="tozeroy",
        fillcolor="rgba(251,191,36,0.1)", yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["spot"], name="Spot",
        line=dict(color="#06b6d4", width=1.5, dash="dash"), yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=[baseline * (1 + threshold / 100)] * len(df), name=f"+{threshold:.1f}% threshold",
        line=dict(color="#f97316", width=1, dash="dot"), yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=[baseline * (1 - threshold / 100)] * len(df), name=f"-{threshold:.1f}% threshold",
        line=dict(color="#f97316", width=1, dash="dot"), yaxis="y1", showlegend=False,
    ))
    fig.update_layout(
        height=560, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#0d121d", plot_bgcolor="#0d121d",
        font=dict(color="#e2e8f0", family="JetBrains Mono"),
        legend=dict(orientation="h", y=1.06, font=dict(size=10)),
        barmode="overlay",
        xaxis=dict(showgrid=True, gridcolor="#1e293b", nticks=14),
        yaxis=dict(title="Premium (\u20b9)", showgrid=True, gridcolor="#1e293b",
                    title_font=dict(color="#fbbf24"), tickfont=dict(color="#fbbf24")),
        yaxis2=dict(title="Spot", overlaying="y", side="right", showgrid=False,
                     title_font=dict(color="#06b6d4"), tickfont=dict(color="#06b6d4")),
        yaxis3=dict(overlaying="y", side="left", showgrid=False, visible=False, range=[0, df["volume"].max() * 4]),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown("##### \U0001F4CA Session Stats — " + cfg["label"])
    prems = [h["combined_premium"] for h in hist]
    sym_alert_count = sum(1 for a in st.session_state.alerts if a["symbol"] == sym)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Max Premium", f"\u20b9{max(prems):.2f}")
    s2.metric("Min Premium", f"\u20b9{min(prems):.2f}")
    s3.metric("Avg Premium", f"\u20b9{sum(prems)/len(prems):.2f}")
    s4.metric("Vol Events", f"{sym_alert_count}")


# ==========================================================================
# DASHBOARD VIEW
# ==========================================================================
def render_dashboard():
    h1, h2, h3 = st.columns([2.4, 0.9, 0.9])
    with h1:
        st.markdown(
            '<div class="term-header">'
            '<div><div class="term-brand">\u25c6 NSE/MCX PREMIUM TERMINAL</div>'
            '<div class="term-sub">ATM Combined Premium Spike Monitor</div></div>'
            '</div>', unsafe_allow_html=True
        )
    with h2:
        mkt_badge = '<span class="badge badge-open">\u25cf MARKET OPEN</span>' if MARKET_OPEN \
            else '<span class="badge badge-closed">\u25cf MARKET CLOSED</span>'
        live_badge = '<span class="badge badge-live">\u25cf LIVE</span>' if LIVE \
            else '<span class="badge badge-sim">\u25cf SIMULATED</span>'
        st.markdown(f"<div style='padding-top:14px'>{mkt_badge} {live_badge}</div>", unsafe_allow_html=True)
    with h3:
        st.markdown(f"<div style='text-align:right; padding-top:16px; color:#64748b; font-size:13px;'>"
                    f"{datetime.now().strftime('%H:%M:%S')} IST &nbsp;|&nbsp; {datetime.now().strftime('%d %b %Y')}"
                    f"</div>", unsafe_allow_html=True)

    # ---- ticker ----
    ticker_html = '<div class="ticker-strip">'
    for sym, cfg in ALL_INSTRUMENTS.items():
        r = current_records.get(sym)
        if not r:
            ticker_html += f'<span class="ticker-item"><b>{cfg["label"]}</b>: \u2014</span>'
            continue
        cls = "tick-spike" if r["is_spike"] else ("tick-up" if r["pct_chg"] >= 0 else "tick-down")
        arrow = "\u25b2" if r["pct_chg"] >= 0 else "\u25bc"
        spike_tag = ' <span class="tick-spike">SPIKE</span>' if r["is_spike"] else ""
        ticker_html += (f'<span class="ticker-item"><b>{cfg["label"]}</b>: {r["spot"]:,.1f} '
                         f'<span class="{cls}">{arrow}{abs(r["pct_chg"]):.2f}%</span>{spike_tag}</span>')
    ticker_html += '</div>'
    st.markdown(ticker_html, unsafe_allow_html=True)

    # ---- controls row ----
    c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
    with c1:
        st.number_input("Spike threshold (%)", min_value=0.5, max_value=50.0,
                         value=DEFAULT_THRESHOLD_PCT, step=0.5, key="threshold_input")
    with c2:
        st.checkbox("Show only \u2265 threshold", value=False, key="only_spikes_cb")
    with c4:
        st.write("")
        if st.button("\u23f8\ufe0f Pause" if not st.session_state.paused else "\u25b6\ufe0f Resume",
                      width="stretch"):
            st.session_state.paused = not st.session_state.paused
            st.rerun()
    with c5:
        st.write("")
        if st.button("\u21bb Reset", width="stretch"):
            st.session_state.history = {s: [] for s in ALL_INSTRUMENTS}
            st.session_state.sim_state = {s: init_sim_state(c) for s, c in ALL_INSTRUMENTS.items()}
            st.session_state.alerts = []
            st.session_state.spike_count_today = 0
            st.rerun()

    # ---- 2-panel row: alerts + stats ----
    p1, p2 = st.columns(2)
    with p1:
        alerts_html = '<div class="panel"><div class="panel-title"><span>\u26a1 Spike Alerts</span>' \
                      f'<span style="color:var(--alert)">{st.session_state.spike_count_today} today</span></div>'
        if not st.session_state.alerts:
            alerts_html += '<div class="empty-state">Waiting for spikes\u2026</div>'
        else:
            for a in st.session_state.alerts[:18]:
                lbl = ALL_INSTRUMENTS.get(a["symbol"], {}).get("label", a["symbol"])
                alerts_html += (f'<div class="alert-row"><div><span class="alert-time">{a["time"]}</span> '
                                 f'<span class="alert-sym">{lbl}</span></div>'
                                 f'<div class="alert-pct">{a["pct"]:+.1f}%</div></div>')
        alerts_html += '</div>'
        st.markdown(alerts_html, unsafe_allow_html=True)
    with p2:
        active_sym = st.session_state.active_sym
        active_hist = st.session_state.history.get(active_sym, [])
        stats_html = ('<div class="panel"><div class="panel-title"><span>Session Stats</span>'
                      f'<span style="color:var(--text-dim);font-size:10px">'
                      f'{ALL_INSTRUMENTS[active_sym]["label"]}</span></div>')
        if active_hist:
            prems = [h["combined_premium"] for h in active_hist]
            sym_events = sum(1 for a in st.session_state.alerts if a["symbol"] == active_sym)
            for lbl, val in [
                ("Max Prem", f"\u20b9{max(prems):.2f}"),
                ("Min Prem", f"\u20b9{min(prems):.2f}"),
                ("Avg Prem", f"\u20b9{sum(prems)/len(prems):.2f}"),
                ("Vol Events", f"{sym_events}"),
            ]:
                stats_html += f'<div class="stat-row"><span class="stat-lbl">{lbl}</span><span class="stat-val">{val}</span></div>'
        else:
            stats_html += '<div class="empty-state">No ticks yet.</div>'
        stats_html += '</div>'
        st.markdown(stats_html, unsafe_allow_html=True)

    st.write("")

    # ---- watchlist ----
    rows = []
    for s, meta in ALL_INSTRUMENTS.items():
        last = current_records.get(s)
        if not last:
            continue
        if only_spikes and not last.get("is_spike"):
            continue
        rows.append({
            "Symbol": meta["label"], "Expiry": last.get("expiry", "-"), "Src": last.get("source", "-"),
            "Spot": round(last["spot"], 2), "ATM": round(last["atm_strike"], 0),
            "Comb.Prem": round(last["combined_premium"], 2), "% Chg": round(last.get("pct_chg", 0.0), 2),
            "CE": round(last["ce_ltp"], 2), "PE": round(last["pe_ltp"], 2),
            "ATM IV": last.get("atm_iv", "-"), "Vol": last.get("volume", "-"),
            "Status": "SPIKE \u25b2" if last.get("is_spike") and last.get("pct_chg", 0) >= 0
                      else ("SPIKE \u25bc" if last.get("is_spike") else
                            ("Rising" if last.get("pct_chg", 0) >= 0 else "Falling")),
        })

    filter_txt = f"[Showing ONLY \u2265{threshold:.1f}% Spikes]" if only_spikes else "[Showing All Symbols]"
    st.markdown(f'<div class="wl-header">F&amp;O Watchlist — Combined Premium Monitor '
                f'<span style="color:var(--alert);margin-left:10px;font-weight:700">{filter_txt}</span> '
                f'<span style="color:var(--text-dim);margin-left:10px">({len(rows)} symbols) '
                f'\u2014 click a row to open its chart</span></div>', unsafe_allow_html=True)

    if not rows:
        st.markdown(f'<div class="empty-state">No symbols currently exceeding {threshold:.1f}% threshold. '
                    f'Waiting for spikes\u2026</div>', unsafe_allow_html=True)
        return

    wdf = pd.DataFrame(rows).sort_values("% Chg", key=abs, ascending=False).reset_index(drop=True)

    def highlight_spike(row):
        if "SPIKE" in str(row["Status"]):
            return ["background-color: rgba(249,115,22,0.10)"] * len(row)
        return [""] * len(row)

    styled = wdf.style.apply(highlight_spike, axis=1) \
        .map(lambda v: "color:#10b981;font-weight:600" if isinstance(v, (int, float)) and v >= 0 else
                        ("color:#ef4444;font-weight:600" if isinstance(v, (int, float)) else ""),
             subset=["% Chg"]) \
        .format({"Spot": "{:,.2f}", "ATM": "{:,.0f}", "Comb.Prem": "\u20b9{:.2f}",
                 "% Chg": "{:+.2f}%", "CE": "{:.2f}", "PE": "{:.2f}"})

    event = st.dataframe(
        styled, width="stretch", hide_index=True,
        height=min(460, 45 + 38 * len(wdf)),
        on_select="rerun", selection_mode="single-row",
    )
    if event.selection and event.selection.get("rows"):
        idx = event.selection["rows"][0]
        chosen_label = wdf.iloc[idx]["Symbol"]
        chosen_sym = label_to_sym.get(chosen_label)
        if chosen_sym:
            st.session_state.active_sym = chosen_sym
            st.session_state.chart_open = True
            st.rerun()

    st.caption(
        "Combined Prem = ATM Call LTP + ATM Put LTP \u00b7 \u2265 threshold spike w/o a matching spot move "
        "usually signals IV expansion \u00b7 " + ("Live data via Dhan API" if LIVE else "Data simulated for demo")
    )


# ==========================================================================
# ROUTE
# ==========================================================================
if st.session_state.chart_open:
    render_chart_page()
else:
    render_dashboard()

# ==========================================================================
# AUTO-REFRESH
# ==========================================================================
if st.session_state.get("auto_refresh_toggle", True) and not st.session_state.paused:
    time.sleep(refresh_secs)
    st.rerun()
