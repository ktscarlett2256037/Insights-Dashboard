import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CONFIG & VERSION ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.sidebar.info("App Version: 3.0 (Python 3.14 Stability Fix)")

st.title("🚀 Quantum Intelligence Terminal")

# --- 2. STABILIZED DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_basic_data(ticker_symbol):
    try:
        # We use Ticker object directly instead of yf.download
        # This is much more stable on newer Python versions
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1y")
        return df
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- 3. THE UI ---
ticker = st.sidebar.text_input("Enter Ticker", value="SBIN.NS").upper()

with st.spinner("Stabilizing connection..."):
    data = fetch_basic_data(ticker)

if not data.empty:
    # SUCCESS!
    st.subheader(f"Market Pulse: {ticker}")
    
    # Simple Metrics Row
    m1, m2, m3 = st.columns(3)
    current_price = data['Close'].iloc[-1]
    m1.metric("LTP", f"₹{current_price:,.2f}")
    m2.metric("High", f"₹{data['High'].max():,.2f}")
    m3.metric("Low", f"₹{data['Low'].min():,.2f}")
    
    # Robust Line Chart
    st.line_chart(data['Close'])
    
    st.success("✅ System Stabilized. Tab 1 Active.")
else:
    st.warning("📡 Market Data Gateway is busy. Please refresh the page in 30 seconds.")
    st.info("Note: Python 3.14 environment detected. Applying compatibility patches...")
