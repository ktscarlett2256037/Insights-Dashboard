import streamlit as st
import numpy as np # DEFINED AT THE TOP
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# --- VERSION TRACKER ---
st.sidebar.info("App Version: 2.0 (Hard Reset)")

st.title("🚀 Quantum Intelligence Terminal")

ticker = st.sidebar.text_input("Ticker", value="SBIN.NS").upper()

# Testing if NP is working with a tiny calculation
test_val = np.nan 
st.write(f"Testing NumPy... (If you see this, np is working!)")

@st.cache_data(ttl=600)
def fetch_basic_data(t):
    return yf.download(t, period="1y", auto_adjust=True, multi_level_download=False)

data = fetch_basic_data(ticker)

if not data.empty:
    st.line_chart(data['Close'])
    st.success(f"Connected to {ticker}")
else:
    st.warning("No data found. Check your internet or ticker.")
