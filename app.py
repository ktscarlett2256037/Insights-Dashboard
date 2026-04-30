import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# --- 1. CONFIG & GRID STYLING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide", initial_sidebar_state="collapsed")

# Professional High-Density CSS
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #11141d; padding: 12px; border-radius: 4px; border: 1px solid #2a2e39;}
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (The "Ninja" Bypass) ---
@st.cache_data(ttl=600)
def fetch_terminal_data(symbol, horizon):
    try:
        # Step A: Use a session to look like a standard browser
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'})
        
        t = Ticker(symbol, session=session, asynchronous=False)
        
        # Step B: Map horizons
        h_map = {"Last Day": ("1d", "1m"), "Last Month": ("1mo", "1d"), 
                 "1 Year": ("1y", "1d"), "5 Years": ("5y", "1d")}
        p, i = h_map.get(horizon, ("1y", "1d"))
        
        # Step C: Fetch Price History
        hist = t.history(period=p, interval=i)
        
        if isinstance(hist, str): return None, {} # API returned an error string
        if isinstance(hist, dict): hist = hist.get(symbol)
        if hist is None or (isinstance(hist, pd.DataFrame) and hist.empty): return None, {}

        # Step D: Cleanup
        df = hist.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # Step E: Defensive Fundamentals Fetch
        def get_safe_dict(prop):
            val = getattr(t, prop)
            return val.get(symbol, {}) if isinstance(val, dict) else {}

        summary = get_safe_dict('summary_detail')
        stats = get_safe_dict('key_stats')
        
        meta = {
            **summary, **stats,
            'c52h': df['high'].max(),
            'c52l': df['low'].min()
        }
            
        return df, meta
    except:
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. TOP NAVIGATION BAR ---
st.title("🚀 Quantum Intelligence Terminal")
ctrl1, ctrl2, _ = st.columns([2, 2, 8])
with ctrl1:
    ticker = st.text_input("Ticker", value="SBIN.NS", label_visibility="collapsed").upper()
with ctrl2:
    horizon = st.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2, label_visibility="collapsed")

# --- 4. EXECUTION ---
data, meta = fetch_terminal_data(ticker, horizon)

if data is not None:
    data['rsi'] = calculate_rsi(data['close'])
    curr = data['close'].iloc[-1]
    rsi_val = data['rsi'].iloc[-1]

    # --- 5. EXECUTIVE DATA RIBBONS ---
    # Row 1: Pulse Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{curr:,.2f}")
    m2.metric("52W High", f"₹{meta['c52h']:,.2f}")
    m3.metric("52W Low", f"₹{meta['c52l']:,.2f}")
    
    rsi_desc = "OVERBOUGHT" if rsi_val > 70 else "OVERSOLD" if rsi_val < 30 else "NEUTRAL"
    m4.metric("RSI (14)", f"{rsi_val:.1f}", rsi_desc, delta_color="off")
    m5.metric("Mkt Cap", f"₹{meta.get('marketCap', 0)/1e7:,.0f} Cr")

    # Row 2: Fundamental Ratios
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.write(f"**P/E:** {meta.get('trailingPE', 'N/A')}")
    f2.write(f"**P/B:** {meta.get('priceToBook', 'N/A')}")
    f3.write(f"**D/E:** {meta.get('debtToEquity', 'N/A')}")
    f4.write(f"**Beta:** {meta.get('beta', 'N/A')}")
    vol = data['volume'].iloc[-1]
    f5.write(f"**Vol:** {vol/1000:,.1f}K" if vol < 1e6 else f"**Vol:** {vol/1e6:,.2f}M")

    st.divider()

    # --- 6. CHARTS ---
    # Price + Translucent Volume Area
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['Date'], y=data['volume'], fill='tozeroy',
                             fillcolor='rgba(0, 204, 255, 0.25)', line=dict(width=0), yaxis="y2", name="Volume"))
    
    if horizon == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['close'], line=dict(color='#00ffcc', width=2.5), name="Price"))
    else:
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['open'], high=data['high'], 
                                     low=data['low'], close=data['close'], name="Price"))

    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                      margin=dict(l=0, r=0, t=10, b=0),
                      yaxis=dict(gridcolor="#2a2e39"),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['volume'].max()*4]))
    st.plotly_chart(fig, use_container_width=True)

    # Dedicated RSI Chart
    fig_rsi = go.Figure()
    fig_rsi.add_hrect(y0=30, y1=70, fillcolor="#2a2e39", opacity=0.3, line_width=0)
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['rsi'], line=dict(color='#AB63FA', width=1.5)))
    fig_rsi.update_layout(template="plotly_dark", height=180, margin=dict(l=0, r=0, t=0, b=0),
                          yaxis=dict(range=[0, 100], tickvals=[30, 70], gridcolor="#2a2e39"))
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.error("📡 Connection to Exchange Interrupted.")
    st.info("The cloud server's IP address is currently being blocked by Yahoo. Please wait 10 seconds and try again.")
    if st.button("🔄 Attempt Secure Reconnect"):
        st.cache_data.clear()
        st.rerun()
