import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# --- 1. SESSION HELPER (The Secret Sauce) ---
def get_safe_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

# --- 2. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=300)
def fetch_data(symbol, horizon):
    try:
        session = get_safe_session()
        t = Ticker(symbol, session=session, asynchronous=False)
        
        # Mapping Horizon to Period/Interval
        p_map = {"Last Day": ("1d", "1m"), "Last Month": ("1mo", "1d"), 
                 "1 Year": ("1y", "1d"), "5 Years": ("5y", "1d")}
        period, interval = p_map.get(horizon, ("1y", "1d"))
        
        # Fetch History
        df = t.history(period=period, interval=interval)
        
        # Fix for YahooQuery Dictionary Output
        if isinstance(df, dict):
            df = df.get(symbol)
        
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return None, {}

        # Data Cleaning
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # Fetching Fundamentals safely
        summary = t.summary_detail.get(symbol, {})
        stats = t.key_stats.get(symbol, {})
        
        return df, {**summary, **stats}
    except Exception as e:
        st.error(f"API Error: {e}")
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 4. TOP CONTROL BAR ---
st.title("🚀 Quantum Intelligence Terminal")
c1, c2, _ = st.columns([2, 2, 6])
with c1:
    ticker = st.text_input("Enter Symbol", value="SBIN.NS").upper()
with c2:
    horizon = st.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2)

# --- 5. EXECUTION ---
data, meta = fetch_data(ticker, horizon)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    curr = data['Close'].iloc[-1]
    curr_rsi = data['RSI'].iloc[-1]
    
    # --- TOP ROW: KPI STRIP ---
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("LTP", f"₹{curr:,.2f}")
    k2.metric("52W High", f"₹{data['High'].max():,.2f}")
    k3.metric("52W Low", f"₹{data['Low'].min():,.2f}")
    
    rsi_type = "OVERBOUGHT" if curr_rsi > 70 else "OVERSOLD" if curr_rsi < 30 else "NEUTRAL"
    k4.metric("RSI (14)", f"{curr_rsi:.1f}", rsi_type, delta_color="off")
    k5.metric("Mkt Cap", f"₹{meta.get('marketCap', 0)/1e7:,.0f} Cr")

    # --- SECOND ROW: RATIO RIBBON ---
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.write(f"**P/E Ratio:** {meta.get('trailingPE', 'N/A')}")
    f2.write(f"**P/B Ratio:** {meta.get('priceToBook', 'N/A')}")
    f3.write(f"**D/E Ratio:** {meta.get('debtToEquity', 'N/A')}")
    f4.write(f"**Dividend:** {meta.get('dividendYield', 0)*100:.2f}%")
    f5.write(f"**Beta:** {meta.get('beta', 'N/A')}")

    st.divider()

    # --- MAIN CHART (Full Width) ---
    fig = go.Figure()
    # Liquidity Map
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.2)', line=dict(color='rgba(0,0,0,0)'),
        yaxis="y2", name="Volume"
    ))
    # Price
    if horizon == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2), name="Price"))
    else:
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"))

    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                      yaxis=dict(title="Price (₹)", side="left"),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 5]),
                      margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- RSI CHART (Dedicated) ---
    fig_rsi = go.Figure()
    fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0)
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=1.5)))
    fig_rsi.update_layout(template="plotly_dark", height=200, yaxis=dict(range=[0, 100], tickvals=[30, 70]), margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.warning("📡 Connecting to Exchange... If this stays, check if your ticker (e.g. SBIN.NS) is correct.")
    if st.button("Force Reconnect"):
        st.cache_data.clear()
        st.rerun()
