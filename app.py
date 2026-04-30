import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# --- 1. CONFIG & UI STYLING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# This CSS ensures the app is wide, dark, and scrollable
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    .stMetric {background-color: #161a25; padding: 15px; border-radius: 5px; border: 1px solid #2a2e39;}
    div[data-testid="stExpander"] {border: none !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE HARDENED ENGINE ---
@st.cache_data(ttl=300)
def fetch_quantum_data(symbol, horizon):
    try:
        # Step A: Mask the request to look like a real browser
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'})
        
        ticker_obj = yf.Ticker(symbol, session=session)
        
        # Step B: Map horizons
        h_map = {"Last Day": "1d", "Last Month": "1mo", "1 Year": "1y", "5 Years": "5y"}
        p = h_map.get(horizon, "1y")
        # Use 1m interval for day view, else 1d
        i = "1m" if horizon == "Last Day" else "1d"
        
        # Step C: Fetch Price History
        # We fetch 1y minimum to calculate 52W stats reliably
        df = ticker_obj.history(period="1y" if p in ["1d", "1mo"] else p, interval=i)
        
        if df.empty:
            return None, {}

        # Step D: Cleanup the 'Date' column
        df = df.reset_index()
        # Rename whichever column is the date (usually 'Date' or 'Datetime')
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        
        # Step E: Manual 52W Calc (prevents 'None' values)
        meta = {
            'c52h': df['High'].max(),
            'c52l': df['Low'].min(),
            'info': ticker_obj.info # Fundamental dictionary
        }
        
        # Slice for display if necessary
        if horizon == "Last Month": df = df.tail(22)
            
        return df, meta
    except Exception as e:
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. TOP NAVIGATION CONTROLS ---
st.title("🚀 Quantum Intelligence Terminal")
nav1, nav2, _ = st.columns([2, 2, 6])
with nav1:
    ticker = st.text_input("Enter Symbol", value="SBIN.NS").upper()
with nav2:
    horizon = st.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2)

# --- 4. EXECUTION ---
data, meta = fetch_quantum_data(ticker, horizon)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    curr = data['Close'].iloc[-1]
    rsi_val = data['RSI'].iloc[-1]
    info = meta.get('info', {})

    # --- 5. TOP RIBBON: PULSE & FUNDAMENTALS ---
    # We combine these into two clean rows at the top as requested
    r1_1, r1_2, r1_3, r1_4, r1_5 = st.columns(5)
    r1_1.metric("LTP", f"₹{curr:,.2f}")
    r1_2.metric("52W High", f"₹{meta['c52h']:,.2f}")
    r1_3.metric("52W Low", f"₹{meta['c52l']:,.2f}")
    
    rsi_desc = "OVERBOUGHT" if rsi_val > 70 else "OVERSOLD" if rsi_val < 30 else "NEUTRAL"
    r1_4.metric("RSI (14)", f"{rsi_val:.1f}", rsi_desc, delta_color="off")
    
    mkt_cap = info.get('marketCap', 0) / 1e7
    r1_5.metric("Mkt Cap", f"₹{mkt_cap:,.0f} Cr")

    r2_1, r2_2, r2_3, r2_4, r2_5 = st.columns(5)
    r2_1.write(f"**P/E Ratio:** {info.get('trailingPE', 'N/A')}")
    r2_2.write(f"**P/B Ratio:** {info.get('priceToBook', 'N/A')}")
    r2_3.write(f"**D/E Ratio:** {info.get('debtToEquity', 'N/A')}")
    r2_4.write(f"**Beta:** {info.get('beta', 'N/A')}")
    r2_5.write(f"**Dividend:** {info.get('dividendYield', 0)*100:.2f}%")

    st.divider()

    # --- 6. CHARTS ---
    # Price Chart + Volume Area
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.25)', line=dict(width=0), 
        yaxis="y2", name="Volume"
    ))
    
    if horizon == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2.5)))
    else:
        fig.add_trace(go.Candlestick(
            x=data['Date'], open=data['Open'], high=data['High'], 
            low=data['Low'], close=data['Close'], name="Price"
        ))

    fig.update_layout(
        template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(title="Price (₹)", side="left"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max()*4])
    )
    st.plotly_chart(fig, use_container_width=True)

    # RSI Chart (Dedicated View)
    fig_rsi = go.Figure()
    fig_rsi.add_hrect(y0=30, y1=70, fillcolor="white", opacity=0.05, line_width=0)
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=2)))
    
    fig_rsi.update_layout(
        template="plotly_dark", height=250, 
        yaxis=dict(range=[0, 100], tickvals=[30, 70], title="RSI"),
        margin=dict(l=0, r=0, t=0, b=0)
    )
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.error("📡 Connection to Exchange Interrupted.")
    st.info("Yahoo is rate-limiting the current server IP. Please wait 10 seconds and click the button below.")
    if st.button("🔄 Force Secure Reconnect"):
        st.cache_data.clear()
        st.rerun()
