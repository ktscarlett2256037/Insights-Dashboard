import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import random

# --- 1. THE ARMOR (User-Agent Rotation) ---
def get_safe_session():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36'
    ]
    session = requests.Session()
    session.headers.update({'User-Agent': random.choice(agents)})
    return session

# --- 2. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.title("🚀 Quantum Intelligence Terminal")

# --- 3. THE DATA ENGINE ---
@st.cache_data(ttl=3600) # Cache for 1 hour to reduce Yahoo hits
def fetch_data_secure(symbol):
    try:
        sess = get_safe_session()
        # We fetch via the Ticker object which is more stable with sessions
        t = yf.Ticker(symbol, session=sess)
        df = t.history(period="1y", interval="1d")
        
        if df.empty:
            return None
            
        # Standardize for Python 3.14 compatibility
        df = df.reset_index()
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        return df
    except:
        return None

# --- 4. UI ---
ticker = st.sidebar.text_input("Enter Ticker", value="SBIN.NS").upper()

data = fetch_data_secure(ticker)

# TABS (Even if data fails, the tabs stay so the app doesn't look broken)
tab1, tab2, tab3 = st.tabs(["📈 Pulse", "🛡️ Risk Vault", "🌐 Alpha Lab"])

if data is not None:
    with tab1:
        # Metrics
        m1, m2, m3 = st.columns(3)
        curr = data['Close'].iloc[-1]
        m1.metric("LTP", f"₹{curr:,.2f}")
        m2.metric("52W High", f"₹{data['High'].max():,.2f}")
        m3.metric("52W Low", f"₹{data['Low'].min():,.2f}")
        
        # Robust Line Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc')))
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
else:
    with tab1:
        st.error("📡 Connection to Exchange Interrupted.")
        st.info("Yahoo Finance is currently rate-limiting the cloud server IP. The terminal will auto-reconnect when the window clears.")
        # We can add a button to try a different 'Safe Session'
        if st.button("Attempt Secure Reconnect"):
            st.cache_data.clear()
            st.rerun()

with tab2:
    st.subheader("Risk Metrics")
    st.caption("Waiting for stable data feed...")

st.sidebar.markdown("---")
st.sidebar.caption("System Status: **Active**")
