import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests

# --- 1. BYPASS RATE LIMITS ---
# This makes your app look like a real browser to Yahoo Finance
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
session = requests.Session()
session.headers.update(headers)

# --- 2. CORE FUNCTIONS ---

def calculate_rsi(series, window=14):
    """Calculates RSI safely even with empty data"""
    if series.empty or len(series) < window:
        return pd.Series(np.nan, index=series.index)
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    # Avoid division by zero
    rs = gain / loss.replace(0, np.nan) 
    return 100 - (100 / (1 + rs))

def calculate_vwap(df):
    """Calculates VWAP safely"""
    if df.empty: return pd.Series(np.nan, index=df.index)
    v = df['Volume']
    p = df['Close']
    return (p * v).cumsum() / v.cumsum().replace(0, np.nan)

# --- 3. DATA ENGINE ---

@st.cache_data(ttl=600) # Cache data for 10 minutes
def get_stock_data(ticker, period):
    try:
        # Use the session to bypass rate limits
        df = yf.download(ticker, period=period, session=session, progress=False)
        return df
    except Exception:
        return pd.DataFrame()

# --- 4. UI LAYOUT ---

st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.title("🚀 Quantum Intelligence Terminal")

ticker = st.sidebar.text_input("Enter Ticker", value="SBIN.NS").upper()
time_period = st.sidebar.selectbox("Select History", ["6mo", "1y", "2y", "5y"], index=1)

data = get_stock_data(ticker, time_period)

# CRITICAL FIX: Robust check for empty data
if data is None or data.empty or 'Close' not in data.columns:
    st.warning(f"⚠️ Yahoo Finance is temporarily blocking requests for {ticker}. Please wait 2-3 minutes and refresh, or try a different ticker like 'RELIANCE.NS'.")
else:
    # Ensure data is a simple Series (fixing the MultiIndex bug)
    if isinstance(data['Close'], pd.DataFrame):
        close_prices = data['Close'][ticker]
        volumes = data['Volume'][ticker]
        opens = data['Open'][ticker]
        highs = data['High'][ticker]
        lows = data['Low'][ticker]
    else:
        close_prices = data['Close']
        volumes = data['Volume']
        opens = data['Open']
        highs = data['High']
        lows = data['Low']

    # Calculate indicators
    rsi_vals = calculate_rsi(close_prices)
    vwap_vals = calculate_vwap(data)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Pulse", "🛡️ Risk", "Σ Alpha", "🌐 Macro", "🧪 Portfolio"])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LTP", f"₹{close_prices.iloc[-1]:,.2f}")
        c2.metric("52W High", f"₹{highs.max():,.2f}")
        c3.metric("52W Low", f"₹{lows.min():,.2f}")
        
        avg_vol = volumes.tail(20).mean()
        surge = volumes.iloc[-1] / avg_vol if avg_vol != 0 else 0
        c4.metric("Volume Surge", f"{surge:.2f}x")

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])
        fig.add_trace(go.Candlestick(x=data.index, open=opens, high=highs, low=lows, close=close_prices, name="Price"), row=1, col=1)
        fig.add_trace(go.Bar(x=data.index, y=volumes, name="Volume", marker_color='gray', opacity=0.5), row=2, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=rsi_vals, name="RSI", line=dict(color='purple')), row=3, col=1)
        
        fig.update_layout(height=700, showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
