import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=300)
def get_data(ticker, period):
    try:
        # Fetching with specific modern parameters
        df = yf.download(ticker, period=period, auto_adjust=True, multi_level_download=False)
        return df
    except:
        return pd.DataFrame()

# --- 3. UI ---
st.title("🚀 Quantum Intelligence Terminal")

ticker = st.sidebar.text_input("Enter Ticker (e.g. SBIN.NS)", value="SBIN.NS").upper()
time_period = st.sidebar.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)

data = get_data(ticker, time_period)

if data.empty:
    st.warning("📡 Waiting for Market Data... If this persists, Yahoo is likely rate-limiting. Try again in 1 minute.")
else:
    # Fix potential column issues
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Pulse", "🛡️ Risk", "Σ Alpha", "🌐 Macro", "🧪 Portfolio"])

    with tab1:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            curr = data['Close'].iloc[-1]
            st.metric("Price", f"₹{curr:,.2f}")
            st.metric("High", f"₹{data['High'].max():,.2f}")
            st.metric("Low", f"₹{data['Low'].min():,.2f}")
        
        with col2:
            # Simple, robust Plotly Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Price", line=dict(color='#00ffcc')))
            fig.update_layout(
                template="plotly_dark",
                margin=dict(l=20, r=20, t=20, b=20),
                height=400,
                xaxis_rangeslider_visible=False
            )
            st.plotly_chart(fig, use_container_width=True)

    st.success("Tab 1 Live: Market connection established.")
