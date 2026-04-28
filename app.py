import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np  # This defines 'np' so the error goes away
import plotly.graph_objects as go
import requests

# --- 1. SET UP THE BROWSER DISGUISE ---
# This helps prevent the "Too Many Requests" error
headers = {'User-Agent': 'Mozilla/5.0'}
session = requests.Session()
session.headers.update(headers)

# --- 2. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.title("🚀 Quantum Intelligence Terminal")

# --- 3. THE DATA ENGINE ---
@st.cache_data(ttl=600)
def get_data(ticker, period):
    try:
        # We use the session here to look like a real person
        df = yf.download(ticker, period=period, session=session, auto_adjust=True, multi_level_download=False)
        return df
    except:
        return pd.DataFrame()

# --- 4. SIDEBAR ---
ticker = st.sidebar.text_input("Enter Ticker (e.g. SBIN.NS)", value="SBIN.NS").upper()
time_period = st.sidebar.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)

# --- 5. THE MAIN SHOW ---
data = get_data(ticker, time_period)

if data is None or data.empty:
    st.warning("📡 Market Data is currently blocked by Yahoo. Please wait 60 seconds and refresh.")
else:
    # Check if we have the right columns
    if 'Close' in data.columns:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Pulse", "🛡️ Risk", "Σ Alpha", "🌐 Macro", "🧪 Portfolio"])
        
        with tab1:
            col1, col2 = st.columns([1, 3])
            
            with col1:
                curr_price = data['Close'].iloc[-1]
                st.metric("Price", f"₹{curr_price:,.2f}")
                st.metric("High", f"₹{data['High'].max():,.2f}")
                st.metric("Low", f"₹{data['Low'].min():,.2f}")
            
            with col2:
                # Basic, reliable Line Chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Close', line=dict(color='#00CC96')))
                fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
                
        st.success(f"✅ Successfully connected to {ticker} data.")
    else:
        st.error("Data received, but it's in a format I don't recognize. Try refreshing.")
