# NSE/MCX Combined-Premium Terminal

A Bloomberg-terminal-style dashboard that tracks **ATM combined option
premium** (ATM Call LTP + ATM Put LTP, i.e. the short-straddle value)
across NSE indices, NSE stocks, and MCX commodities — and flashes an
alert whenever premium jumps **≥5% (configurable)** in a session, which
usually signals a sudden IV / event-risk expansion.

**v3 highlights (rebuilt around the click-through chart UX):**
- No chart on the main dashboard page — the main page is ticker + controls
  + a 2-panel row (Spike Alerts / Session Stats) + the full watchlist,
  matching the standalone HTML mockup's layout.
- Click any watchlist row to open a dedicated **full-page chart** (Spot vs
  Combined Premium vs Volume), with a "Back to Dashboard" button and a
  best-effort **Esc key** handler. Switching views does NOT reset your
  session's tick history (it uses Streamlit's native row-selection +
  session state, not a real page navigation).
- Every instrument refreshes every cycle (not just the one you're
  focused on) — the ticker strip and watchlist are genuinely live.
- Scrolling ticker strip + a MARKET OPEN / CLOSED badge (IST, NSE hours).
- Volume column/series, with volume surging alongside big premium moves.
- Per-row LIVE/SIM source tag and real expiry date in the watchlist.
- PCR (chain-wide Put/Call OI ratio) and ATM delta shown on the chart page.
- "Show only ≥ threshold" watchlist filter, and a Pause/Reset control
  that freezes the feed without losing session history.

Two ways to use it:

| File | What it is |
|---|---|
| `app.py` | **Streamlit app** — pulls live data from the Dhan API (falls back to a realistic simulated feed if no/invalid credentials), full watchlist, spike alerts, click-through session chart, CSV export. This is the one you deploy. |
| `premium-terminal-static.html` | A **fully self-contained, offline** single-file HTML version with its own in-browser simulation engine and Chart.js full-page charts. Handy as a quick visual demo / GitHub Pages page — no Python, no server, no live data. |

## Project layout

```
├── app.py                        # Streamlit entry point
├── config.py                     # instrument universe (indices/stocks/commodities)
├── dhan_service.py                # Dhan API wrapper + simulated fallback feed
├── premium-terminal-static.html  # standalone offline HTML demo
├── requirements.txt
├── .env.example                  # copy -> .env and fill in your keys
├── .streamlit/
│   ├── config.toml               # dark theme matching the terminal palette
│   └── secrets.toml.example      # template for Streamlit Cloud secrets
└── .gitignore                    # keeps .env and secrets.toml out of git
```

## 1. Run locally

```bash
git clone <your-repo-url>
cd nse-mcx-premium-terminal
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste your DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN

streamlit run app.py
```

Get your credentials from **dhan.co → My Profile → DhanHQ Trading APIs**
(generate an Access Token there). Access tokens on Dhan's standard plan
expire periodically — if the app suddenly falls back to "SIMULATED" mode,
regenerate the token.

If you don't add credentials at all, the app still runs fine — it just
runs on a realistic simulated feed (clearly labeled with a SIMULATED
badge) so you can try the UI without a broker account.

## 2. Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (your real `.env` is git-ignored — it never
   gets committed).
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo,
   set the main file to `app.py`.
3. In **App settings → Secrets**, paste:
   ```toml
   DHAN_CLIENT_ID = "your_client_id"
   DHAN_ACCESS_TOKEN = "your_access_token"
   ```
   (see `.streamlit/secrets.toml.example`). Streamlit exposes these as
   normal environment variables, so `dhan_service.py` picks them up the
   same way it does locally via `.env`.
4. Deploy. Any time the token expires, update it in Secrets and reboot the app.

## How the data flows

- **Indices** (NIFTY, BANKNIFTY, FINNIFTY, SENSEX) use Dhan's well-known,
  stable index security IDs (`IDX_I` segment).
- **Stocks** (RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS) and **MCX
  commodities** (CRUDEOIL, GOLD, SILVER, NATURALGAS, COPPER) don't have
  fixed IDs worth hardcoding — commodity futures contracts roll monthly
  in particular — so their security IDs are resolved at runtime from
  Dhan's public scrip master (cached for 6 hours). You can also search
  any symbol manually from the sidebar's **"Look up a Security ID"** tool.
- For the resolved underlying, the app calls Dhan's **Option Chain API**
  (`expiry_list` + `option_chain`) to read the nearest-expiry ATM strike's
  CE/PE last price directly — no manual strike-chain construction needed.
- Any failure at any step (expired token, market closed, rate limit,
  symbol not resolvable, etc.) falls back per-instrument to the
  simulated feed rather than crashing the app.

## Notes

- Combined Premium = ATM Call LTP + ATM Put LTP (straddle value). A spike
  with a flat spot often signals rising IV / event risk; a drop with a
  flat spot suggests theta/IV crush.
- This tool is for monitoring/education — **not investment advice**.
- Dhan's Option Chain API is rate-limited to ~1 unique request per 3
  seconds per underlying/expiry — keep the auto-refresh interval at a
  sane value (10s+) if you add more instruments to the focus rotation.
