import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np  # <--- THIS WAS THE MISSING PIECE
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 2. THE DATA ENGINE ---
@st.cache_data(ttl=300)
def get_data(ticker, period):
    try:
        # Use 'multi_level_download=False' to keep the data structure simple
        df = yf.download(ticker, period=period, auto_adjust=True, multi_level_download=False)
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 3. THE MATH ---
def calculate_rsi(series, window=14):
    # This now safely uses 'np' because we imported numpy as np
    if series is None or series.empty or len(series) < window: 
        return pd.Series(np.nan, index=getattr(series, 'index', []))
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 4. THE UI ---
st.title("🚀 Quantum Intelligence Terminal")

# Ticker Input in Sidebar
ticker_input = st.sidebar.text_input("Enter Ticker (e.g. SBIN.NS)", value="SBIN.NS").upper()
time_period = st.sidebar.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)

with st.spinner(f"Fetching {ticker_input}..."):
    data = get_data(ticker_input, time_period)

if data is None or data.empty:
    st.warning(f"⚠️ Yahoo Finance is rate-limiting the server. Wait 30 seconds and refresh.")
    st.info("Try a different ticker like 'RELIANCE.NS' to force a fresh connection.")
else:
    # Cleanup MultiIndex if it exists
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # UI Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Pulse", "🛡️ Risk", "Σ Alpha", "🌐 Macro", "🧪 Portfolio"])

    with tab1:
        # Check if 'Close' exists before metrics
        if 'Close' in data.columns:
            curr = data['Close'].iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Price", f"₹{curr:,.2f}")
            m2.metric("Period High", f"₹{data['High'].max():,.2f}")
            m3.metric("Period Low", f"₹{data['Low'].min():,.2f}")

            # Calculate RSI
            rsi_data = calculate_rsi(data['Close'])

            # Charting
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
            
            # Row 1: Candlesticks
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'], 
                low=data['Low'], close=data['Close'], name="Price"
            ), row=1, col=1)
            
            # Row 2: RSI
            fig.add_trace(go.Scatter(x=data.index, y=rsi_data, name="RSI", line=dict(color='purple')), row=2, col=1)
            
            fig.update_layout(height=600, showlegend=False, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Data received but format is incorrect. Try refreshing.")
