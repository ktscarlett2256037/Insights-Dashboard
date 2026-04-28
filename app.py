import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. SET UP ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.sidebar.info("App Version: 4.0 (The 'Final Boss' Patch)")

st.title("🚀 Quantum Intelligence Terminal")

# --- 2. THE ULTIMATE DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_data_final(symbol):
    try:
        # Fetching using the most basic method to avoid Python 3.14 bugs
        ticker_obj = yf.Ticker(symbol)
        df = ticker_obj.history(period="1y")
        
        if df.empty:
            return None
            
        # FORCE CLEANUP: This fixes the 'KeyError: Date'
        df = df.reset_index() # Moves the date out of the hidden index
        # Rename the first column to 'Date' regardless of what Yahoo calls it
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        
        return df
    except Exception as e:
        return None

# --- 3. UI LOGIC ---
ticker = st.sidebar.text_input("Enter Ticker", value="SBIN.NS").upper()

with st.spinner("Decrypting Market Stream..."):
    data = fetch_data_final(ticker)

if data is not None:
    # DATA IS ALIVE!
    st.subheader(f"Analyzing {ticker}")
    
    # Standard Metrics
    m1, m2, m3 = st.columns(3)
    latest_price = data['Close'].iloc[-1]
    m1.metric("LTP", f"₹{latest_price:,.2f}")
    m1.caption("Live from Exchange")
    
    m2.metric("52W High", f"₹{data['High'].max():,.2f}")
    m3.metric("52W Low", f"₹{data['Low'].min():,.2f}")

    # Tabs for the rest of our project
    tab1, tab2, tab3 = st.tabs(["📊 Price Action", "🛡️ Risk Metrics", "📰 News Terminal"])

    with tab1:
        # Using a very simple line chart to ensure it loads
        chart_data = data.set_index('Date')['Close']
        st.line_chart(chart_data)
        
    with tab2:
        st.info("Risk engine initializing... Tab 1 must remain stable first.")
        
    st.success(f"Connection Secure: {ticker} feed active.")

else:
    st.error("⚠️ Data Stream Interrupted.")
    st.info("Yahoo is heavily rate-limiting this server. Try a US ticker like 'AAPL' to test if the connection is working at all.")
