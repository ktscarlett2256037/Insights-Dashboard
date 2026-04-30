import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & MAPPING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

TIME_MAP = {
    "Last Day": ("1d", "1m"),
    "Last Month": ("1mo", "1d"),
    "Last 6 Months": ("6mo", "1d"),
    "Last 1 Year": ("1y", "1d"),
    "Last 5 Years": ("5y", "1d")
}

# --- 2. THE STEALTH ENGINE ---
@st.cache_data(ttl=300)
def fetch_terminal_data(symbol, period, interval):
    try:
        t = Ticker(symbol, asynchronous=True)
        df = t.history(period=period, interval=interval)
        if df.empty: return None
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()
        
        # Robust Column Renaming (Fixing the Volume Zero issue)
        df.columns = [c.lower() for c in df.columns]
        rename_map = {'date': 'Date', 'open': 'Open', 'high': 'High', 
                      'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
        df.rename(columns=rename_map, inplace=True)
        
        # Filter out 0 volume if it's just a single glitchy data point at the end
        if df['Volume'].iloc[-1] == 0 and len(df) > 1:
            df.loc[df.index[-1], 'Volume'] = df['Volume'].iloc[-2]
            
        return df
    except:
        return None

# --- 3. MATH ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 4. UI SIDEBAR ---
st.title("🚀 Quantum Intelligence Terminal")
ticker = st.sidebar.text_input("Symbol", value="SBIN.NS").upper()
horizon = st.sidebar.selectbox("Time Horizon", list(TIME_MAP.keys()), index=3)
selected_period, selected_interval = TIME_MAP[horizon]

# --- 5. EXECUTION ---
data = fetch_terminal_data(ticker, selected_period, selected_interval)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    curr_rsi = data['RSI'].iloc[-1]
    
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("LTP", f"₹{data['Close'].iloc[-1]:,.2f}")
    c2.metric("Volume", f"{data['Volume'].iloc[-1]:,.0f}")
    
    rsi_state = "🔴 Overbought" if curr_rsi > 70 else "🟢 Oversold" if curr_rsi < 30 else "⚪ Neutral"
    c3.metric("RSI Status", f"{curr_rsi:.1f}", rsi_state)

    # --- 6. CHART 1: PRICE & VOLUME AREA ---
    st.subheader("Price Action & Liquidity Map")
    
    fig_price = go.Figure()

    # Translucent Volume Area Map (Secondary Axis)
    fig_price.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'],
        name="Volume Area",
        fill='tozeroy',
        fillcolor='rgba(127, 127, 127, 0.15)', # Translucent grey
        line=dict(color='rgba(127, 127, 127, 0.2)'),
        yaxis="y2"
    ))

    # Candlestick Chart (Primary Axis)
    fig_price.add_trace(go.Candlestick(
        x=data['Date'], open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'], name="Candlestick"
    ))

    fig_price.update_layout(
        template="plotly_dark",
        height=500,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        yaxis=dict(title="Price (₹)", side="left"),
        yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 3]), # Pushes volume to background
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_price, use_container_width=True)

    # --- 7. CHART 2: SEPARATE RSI ---
    st.subheader("Momentum: RSI (14)")
    
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(
        x=data['Date'], y=data['RSI'],
        line=dict(color='#AB63FA', width=2),
        name="RSI"
    ))

    # Clean RSI Bands
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.3)
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.3)
    
    fig_rsi.update_layout(
        template="plotly_dark",
        height=250,
        yaxis=dict(range=[0, 100], tickvals=[30, 70]),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.error("📡 Market Data Stream currently unavailable.")
