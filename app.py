import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# --- 1. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 2. DATA ENGINE (The Tank) ---
@st.cache_data(ttl=3600) # Cache for 1 hour to stop hitting Yahoo
def fetch_robust_data(symbol):
    try:
        # We use a slight delay to be "polite" to the server
        time.sleep(1) 
        ticker_obj = yf.Ticker(symbol)
        # We try 'period' instead of 'history' first as it's more stable
        df = yf.download(symbol, period="1y", interval="1d", auto_adjust=True, progress=False)
        
        if df.empty:
            return None
            
        # Clean up columns for Python 3.14
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        return df
    except Exception as e:
        return None

# --- 3. UI ---
st.title("🚀 Quantum Intelligence Terminal")
ticker = st.sidebar.text_input("Ticker", value="SBIN.NS").upper()

data = fetch_robust_data(ticker)

if data is not None:
    # 4. KPI MATH
    curr = data['Close'].iloc[-1]
    prev = data['Close'].iloc[-2]
    change_pct = ((curr - prev) / prev) * 100
    
    m1, m2, m3 = st.columns(3)
    m1.metric("LTP", f"₹{curr:,.2f}", f"{change_pct:.2f}%")
    m2.metric("52W High", f"₹{data['High'].max():,.2f}")
    m3.metric("52W Low", f"₹{data['Low'].min():,.2f}")

    # 5. CHART
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], 
                               low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
    
    # Simple Volume Chart for Tab 1
    fig.add_trace(go.Bar(x=data['Date'], y=data['Volume'], name="Volume", marker_color='orange'), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    st.success(f"System Online: {ticker}")
else:
    st.error("📡 Yahoo Finance is still blocking the connection.")
    st.info("💡 **PRO TIP:** If this keeps happening, it's a 'Server IP' block. Go to your Streamlit dashboard and **delete the app entirely**, then 'New App' and reconnect the GitHub repo. This gives you a fresh IP address!")
