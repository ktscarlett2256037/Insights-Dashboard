import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIG & LAYOUT ---
st.set_page_config(page_title="Quantum Terminal", layout="wide", initial_sidebar_state="collapsed")

# Professional Terminal Styling
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #11141d; padding: 10px; border-radius: 4px; border: 1px solid #2a2e39;}
    [data-testid="stHeader"] {background: rgba(0,0,0,0);}
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ENGINE (The most stable version possible) ---
@st.cache_data(ttl=600)
def fetch_terminal_data(ticker_str, horizon):
    try:
        # Standardize inputs
        h_map = {"Last Day": ("1d", "1m"), "Last Month": ("1mo", "1d"), 
                 "1 Year": ("1y", "1d"), "5 Years": ("5y", "1d")}
        p, i = h_map.get(horizon, ("1y", "1d"))
        
        # Use yfinance with a clean fetch
        t = yf.Ticker(ticker_str)
        # We fetch 1y even for shorter views to calculate 52W stats manually
        hist = t.history(period="1y" if p in ["1d", "1mo"] else p, interval=i)
        
        if hist.empty:
            return None, {}

        # Manual Metadata (Calculated from history to avoid API blocks)
        df = hist.reset_index()
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        
        meta = {
            'c52h': df['High'].max(),
            'c52l': df['Low'].min(),
            'info': t.info if isinstance(t.info, dict) else {}
        }
        
        # Final slice for the chart view
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

# --- 3. TOP NAVIGATION (Minimalist) ---
st.title("🚀 Quantum Intelligence Terminal")
c1, c2, _ = st.columns([2, 2, 8])
with c1:
    ticker = st.text_input("Ticker", value="SBIN.NS", label_visibility="collapsed").upper()
with c2:
    horizon = st.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2, label_visibility="collapsed")

# --- 4. EXECUTION ---
data, meta = fetch_terminal_data(ticker, horizon)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    curr = data['Close'].iloc[-1]
    rsi_val = data['RSI'].iloc[-1]
    info = meta.get('info', {})

    # --- 5. TOP DATA RIBBONS ---
    # Row 1: The "Pulse"
    st.markdown("### Pulse & Momentum")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{curr:,.2f}")
    m2.metric("52W High", f"₹{meta['c52h']:,.2f}")
    m3.metric("52W Low", f"₹{meta['c52l']:,.2f}")
    
    rsi_desc = "OVERBOUGHT" if rsi_val > 70 else "OVERSOLD" if rsi_val < 30 else "NEUTRAL"
    m4.metric("RSI (14)", f"{rsi_val:.1f}", rsi_desc, delta_color="off")
    m5.metric("Mkt Cap", f"₹{info.get('marketCap', 0)/1e7:,.0f} Cr")

    # Row 2: Fundamentals
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.write(f"**P/E Ratio:** {info.get('trailingPE', 'N/A')}")
    f2.write(f"**P/B Ratio:** {info.get('priceToBook', 'N/A')}")
    f3.write(f"**D/E Ratio:** {info.get('debtToEquity', 'N/A')}")
    f4.write(f"**Beta:** {info.get('beta', 'N/A')}")
    
    vol = data['Volume'].iloc[-1]
    vol_txt = f"{vol/1000:,.1f}K" if vol < 1000000 else f"{vol/1000000:,.2f}M"
    f5.write(f"**Volume:** {vol_txt}")

    st.divider()

    # --- 6. CHARTS ---
    # Price Chart + Translucent Volume Area
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.25)', line=dict(width=0), 
        yaxis="y2", name="Volume"
    ))
    
    if horizon == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2.5)))
    else:
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], 
                                     low=data['Low'], close=data['Close'], name="Price"))

    fig.update_layout(
        template="plotly_dark", height=400, xaxis_rangeslider_visible=False,
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
    st.info("The cloud server's IP address is currently being blocked by Yahoo. Please wait 30 seconds and try again.")
    if st.button("🔄 Attempt Secure Reconnect"):
        st.cache_data.clear()
        st.rerun()
