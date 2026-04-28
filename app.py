import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")
st.title("🚀 Quantum Intelligence Terminal")

# --- 2. MATH ENGINE ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=600)
def fetch_market_data(symbol):
    try:
        ticker_obj = yf.Ticker(symbol)
        df = ticker_obj.history(period="1y")
        if df.empty: return None
        df = df.reset_index()
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        return df
    except:
        return None

# --- 3. SIDEBAR ---
ticker = st.sidebar.text_input("Ticker", value="SBIN.NS").upper()
time_period = st.sidebar.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1)

# --- 4. EXECUTION ---
data = fetch_market_data(ticker)

if data is not None:
    # Calculate RSI
    data['RSI'] = calculate_rsi(data['Close'])
    
    # 5. KPIS / METRICS
    m1, m2, m3, m4 = st.columns(4)
    curr = data['Close'].iloc[-1]
    prev = data['Close'].iloc[-2]
    change = curr - prev
    pct_change = (change / prev) * 100
    
    m1.metric("LTP", f"₹{curr:,.2f}", f"{pct_change:.2f}%")
    m2.metric("52W High", f"₹{data['High'].max():,.2f}")
    
    avg_vol = data['Volume'].tail(20).mean()
    vol_surge = data['Volume'].iloc[-1] / avg_vol
    m3.metric("Volume Surge", f"{vol_surge:.2f}x")
    
    curr_rsi = data['RSI'].iloc[-1]
    rsi_state = "Overbought" if curr_rsi > 70 else "Oversold" if curr_rsi < 30 else "Neutral"
    m4.metric("RSI (14)", f"{curr_rsi:.1f}", rsi_state)

    # 6. TABS
    tab1, tab2, tab3 = st.tabs(["📈 Pulse", "🛡️ Risk Vault", "🌐 Alpha Lab"])

    with tab1:
        # Professional Multi-Chart
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=data['Date'], open=data['Open'], high=data['High'], 
            low=data['Low'], close=data['Close'], name="Price"
        ), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(
            x=data['Date'], y=data['RSI'], name="RSI", 
            line=dict(color='#AB63FA', width=2)
        ), row=2, col=1)

        # Formatting
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(
            template="plotly_dark",
            height=700,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.header("Risk Assessment")
        # Placeholder for our next step
        st.write("Calculating Value at Risk (VaR) and Volatility clustering...")

    st.success(f"Quantum Feed: {ticker} fully operational.")

else:
    st.error("Connection lost. Please check ticker symbol.")
