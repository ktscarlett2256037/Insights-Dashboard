import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.sidebar.info("App Version: 5.0 (YahooQuery Stealth)")

# --- 2. DATA ENGINE (The Ninja) ---
@st.cache_data(ttl=3600)
def fetch_data_stealth(symbol):
    try:
        # yahooquery handles the connection differently than yfinance
        t = Ticker(symbol, asynchronous=True)
        df = t.history(period='1y', interval='1d')
        
        if df.empty:
            return None
            
        # yahooquery returns a multi-index, we need to flatten it
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()
            
        # Standardize column names
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return df
    except Exception as e:
        return None

# --- 3. MATH ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 4. UI ---
st.title("🚀 Quantum Intelligence Terminal")
ticker = st.sidebar.text_input("Enter Ticker", value="SBIN.NS").upper()

data = fetch_data_stealth(ticker)

if data is not None:
    # Calculations
    data['RSI'] = calculate_rsi(data['Close'])
    
    # KPI Row
    m1, m2, m3 = st.columns(3)
    curr = data['Close'].iloc[-1]
    change = ((curr - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100
    m1.metric("LTP", f"₹{curr:,.2f}", f"{change:.2f}%")
    m2.metric("52W High", f"₹{data['High'].max():,.2f}")
    m3.metric("RSI (14)", f"{data['RSI'].iloc[-1]:.1f}")

    tab1, tab2 = st.tabs(["📈 Pulse", "🛡️ Risk Vault"])

    with tab1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], 
                                   low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], name="RSI", line=dict(color='#AB63FA')), row=2, col=1)
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        returns = data['Close'].pct_change().dropna()
        st.subheader("Returns Distribution")
        fig_dist = go.Figure(data=[go.Histogram(x=returns, nbinsx=50, marker_color='#00CC96')])
        fig_dist.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_dist, use_container_width=True)

    st.success(f"System Operational: Using Stealth Bridge for {ticker}")

else:
    st.error("📡 Connection to Exchange still blocked.")
    st.info("💡 **FINAL MOVE:** If this fails, the IP is fully burned. Go to Streamlit Cloud, delete the app, and re-create it. This will force it onto a new server with a clean IP address.")
