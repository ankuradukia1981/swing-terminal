# 📈 Live ATM Premium Dashboard (DhanHQ API + Streamlit)

An interactive, single-panel live dashboard that tracks, calculates, and visualizes the combined **At-The-Money (ATM) Options Premium (Straddle Value)** across Equity Indices (NSE) and Commodities (MCX) in real-time. 

Built using the official **DhanHQ API v2** and **Streamlit**.

---

## ✨ Features
* **Multi-Segment Support:** Seamlessly switch between NSE Indices (`NIFTY`, `BANKNIFTY`) and MCX Commodities (`CRUDEOIL`, `NATURALGAS`).
* **Dynamic ATM Logic:** Automatically tracks the underlying asset spot price and mathematically shifts to the closest strike on every refresh loop.
* **Interactive Charting:** Powered by Plotly—view your combined premium cost, individual Call (CE), and Put (PE) lines on a single unified canvas.
* **Auto-Refresher Engine:** Adjustable slider to control data parsing intervals directly from the dashboard sidebar.

---

## 🛠️ Local Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com
   cd atm-premium-dashboard
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root directory and add your Dhan API credentials:
   ```env
   DHAN_CLIENT_ID="your_dhan_client_id"
   DHAN_ACCESS_TOKEN="your_dhan_access_token"
   ```

5. **Run the Dashboard**
   ```bash
   streamlit run app.py
   ```

---

## 🌐 Deployment to Streamlit Cloud

1. Push this project to your GitHub repository.
2. Log into [Streamlit Share](https://streamlit.io).
3. Connect your repo and map the main file path to `app.py`.
4. Go to **Advanced Settings -> Secrets** and paste your credentials securely:
   ```toml
   DHAN_CLIENT_ID = "your_actual_client_id"
   DHAN_ACCESS_TOKEN = "your_actual_access_token"
   ```
5. Click **Deploy**.

---

## 🔒 Disclaimer
*This project is for educational and dashboard visualization purposes only. Algorithmic trading involves substantial risk of loss. Always test system scripts thoroughly before running live executions.*
