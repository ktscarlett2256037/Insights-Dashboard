import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# --- 1. REINFORCED SESSION ---
# This is the "ID Card" that prevents Yahoo from blocking the app
@st.cache_resource
def get_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return s

# --- 2. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.title("🚀 Quantum Intelligence Terminal")

# --- 3. MATH ENGINE ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=600)
def fetch_market_data(symbol):
    try:
        session = get_session()
        ticker_obj = yf.Ticker(symbol, session=session) # Use the reinforced session
        df = ticker_obj.history(period="1y")
        if df.empty: return None
        df = df.reset_index()
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        return df
    except:
        return None

# --- 4. SIDEBAR ---
ticker = st.sidebar.text_input("Ticker", value="SBIN.NS").upper()
time_period = st.sidebar.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)

# --- 5. EXECUTION ---
data = fetch_market_data(ticker)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    
    # KPIS
    m1, m2, m3, m4 = st.columns(4)
    curr = data['Close'].iloc[-1]
    prev = data['Close'].iloc[-2]
    change = curr - prev
    pct_change = (change / prev) * 100
    
    m1.metric("LTP", f"₹{curr:,.2f}", f"{pct_change:.2f}%")
    m2.metric("52W High", f"₹{data['High'].max():,.2f}")
    
    avg_vol = data['Volume'].tail(20).mean()
    vol_surge = data['Volume'].iloc[-1] / avg_vol if avg_vol != 0 else 0
    m3.metric("Volume Surge", f"{vol_surge:.2f}x")
    
    curr_rsi = data['RSI'].iloc[-1]
    rsi_state = "Overbought" if curr_rsi > 70 else "Oversold" if curr_rsi < 30 else "Neutral"
    m4.metric("RSI (14)", f"{curr_rsi:.1f}", rsi_state)

    tab1, tab2, tab3 = st.tabs(["📈 Pulse", "🛡️ Risk Vault", "🌐 Alpha Lab"])

    with tab1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], 
                                   low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], name="RSI", line=dict(color='#AB63FA')), row=2, col=1)
        
        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    st.success(f"Quantum Feed: {ticker} fully operational.")
else:
    st.error("📡 Connection to Yahoo Finance timed out.")
    st.button("🔄 Force Reconnect") # Clicking any button re-runs the script
