import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 2. THE DATA ENGINE (Modernized) ---
@st.cache_data(ttl=300) # Cache for 5 mins
def get_data(ticker, period):
    try:
        # We use 'auto_adjust=True' and 'multi_level_download=False' 
        # to ensure the data comes back in a simple, easy-to-read format.
        df = yf.download(ticker, period=period, auto_adjust=True, multi_level_download=False)
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- 3. THE MATH ---
def calculate_rsi(series, window=14):
    if series.empty or len(series) < window: return pd.Series(np.nan, index=series.index)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 4. THE UI ---
st.title("🚀 Quantum Intelligence Terminal")

ticker = st.sidebar.text_input("Enter Ticker (e.g. SBIN.NS)", value="SBIN.NS").upper()
time_period = st.sidebar.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)

# Fetching the data
with st.spinner(f"Connecting to Market Data for {ticker}..."):
    data = get_data(ticker, time_period)

if data.empty:
    st.warning(f"⚠️ No data received for {ticker}.")
    st.info("💡 **Why this happens:** Yahoo Finance occasionally blocks shared servers (like Streamlit). \n\n **Try these fixes:** \n 1. Wait 60 seconds and refresh. \n 2. Try a different ticker (e.g., AAPL or RELIANCE.NS).")
else:
    # SUCCESS: Data is here!
    # Cleanup: Sometimes yfinance adds a level to columns we don't need
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Calculate indicators
    data['RSI'] = calculate_rsi(data['Close'])
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Pulse", "🛡️ Risk", "Σ Alpha", "🌐 Macro", "🧪 Portfolio"])

    with tab1:
        # Metrics
        m1, m2, m3 = st.columns(3)
        curr = data['Close'].iloc[-1]
        m1.metric("Current Price", f"₹{curr:,.2f}")
        m2.metric("Period High", f"₹{data['High'].max():,.2f}")
        m3.metric("Period Low", f"₹{data['Low'].min():,.2f}")

        # Chart
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
        fig.update_layout(height=600, showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
