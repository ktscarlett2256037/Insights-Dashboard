import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import random

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide", initial_sidebar_state="collapsed")

# Professional CSS for high-density "Bloomberg" feel
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #161a25; padding: 12px; border-radius: 4px; border: 1px solid #2a2e39;}
    div[data-testid="stExpander"] {border: none !important;}
    p {margin-bottom: 0.2rem;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. STEALTH DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_quantum_data(symbol, horizon):
    try:
        # Rotate User-Agents to mimic different browsers
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) Chrome/121.0.0.0 Safari/537.36'
        ]
        session = requests.Session()
        session.headers.update({'User-Agent': random.choice(agents)})
        
        ticker_obj = yf.Ticker(symbol, session=session)
        
        # Map horizons
        h_map = {"Last Day": "1d", "Last Month": "1mo", "1 Year": "1y", "5 Years": "5y"}
        p = h_map.get(horizon, "1y")
        i = "1m" if horizon == "Last Day" else "1d"
        
        # Fetch 1y minimum to ensure 52W calcs work
        df = ticker_obj.history(period="1y" if p in ["1d", "1mo"] else p, interval=i)
        
        if df.empty: return None, {}

        df = df.reset_index()
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        
        # Metadata Safety Net
        info = ticker_obj.info if isinstance(ticker_obj.info, dict) else {}
        meta = {
            'c52h': df['High'].max(),
            'c52l': df['Low'].min(),
            'pe': info.get('trailingPE', 'N/A'),
            'mkt_cap': info.get('marketCap', 0) / 1e7,
            'pb': info.get('priceToBook', 'N/A'),
            'de': info.get('debtToEquity', 'N/A'),
            'beta': info.get('beta', 'N/A')
        }
        
        if horizon == "Last Month": df = df.tail(22)
        return df, meta
    except:
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. TOP NAVIGATION (Zero Clutter) ---
t1, t2, _ = st.columns([2, 2, 8])
with t1:
    ticker = st.text_input("Symbol", value="SBIN.NS", label_visibility="collapsed").upper()
with t2:
    horizon = st.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2, label_visibility="collapsed")

# --- 4. EXECUTION ---
data, meta = fetch_quantum_data(ticker, horizon)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    curr = data['Close'].iloc[-1]
    rsi_val = data['RSI'].iloc[-1]
    
    # --- 5. EXECUTIVE DASHBOARD (Everything at the top) ---
    st.markdown(f"**{ticker} EXECUTIVE SUMMARY**")
    
    # Row 1: Price Pulse
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{curr:,.2f}")
    m2.metric("52W High", f"₹{meta['c52h']:,.2f}")
    m3.metric("52W Low", f"₹{meta['c52l']:,.2f}")
    
    status = "OVERBOUGHT" if rsi_val > 70 else "OVERSOLD" if rsi_val < 30 else "NEUTRAL"
    m4.metric("RSI (14)", f"{rsi_val:.1f}", status, delta_color="off")
    m5.metric("Mkt Cap", f"₹{meta['mkt_cap']:,.0f} Cr")

    # Row 2: Ratio Ribbon
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.write(f"**P/E Ratio:** {meta['pe']}")
    f2.write(f"**P/B Ratio:** {meta['pb']}")
    f3.write(f"**D/E Ratio:** {meta['de']}")
    f4.write(f"**Beta:** {meta['beta']}")
    
    vol = data['Volume'].iloc[-1]
    vol_fmt = f"{vol/1000:,.1f}K" if vol < 1000000 else f"{vol/1000000:,.2f}M"
    f5.write(f"**Vol:** {vol_fmt}")

    st.divider()

    # --- 6. CHARTS (Full Space Utilization) ---
    # Price Chart + Translucent Volume Area
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.25)', line=dict(color='rgba(0, 204, 255, 0.4)', width=1), 
        yaxis="y2", name="Volume"
    ))
    
    if horizon == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2.5)))
    else:
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], 
                                     low=data['Low'], close=data['Close'], name="Price"))

    fig.update_layout(
        template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(side="left", gridcolor="#2a2e39"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max()*4])
    )
    st.plotly_chart(fig, use_container_width=True)

    # RSI Chart (Dedicated)
    fig_rsi = go.Figure()
    fig_rsi.add_hrect(y0=30, y1=70, fillcolor="#2a2e39", opacity=0.3, line_width=0)
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=2)))
    fig_rsi.update_layout(
        template="plotly_dark", height=180, 
        yaxis=dict(range=[0, 100], tickvals=[30, 70], gridcolor="#2a2e39"),
        margin=dict(l=0, r=0, t=0, b=0)
    )
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.error("📡 Connection to Exchange Interrupted.")
    st.info("Yahoo is currently rate-limiting the cloud server IP. Please wait 10 seconds and click below.")
    if st.button("🔄 Force Secure Reconnect"):
        st.cache_data.clear()
        st.rerun()
