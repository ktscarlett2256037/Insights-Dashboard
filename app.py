import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# --- 1. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 2. DATA ENGINE (Fortified) ---
@st.cache_data(ttl=300)
def fetch_terminal_data(symbol, horizon):
    try:
        # Create a real browser session to avoid being blocked
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        t = Ticker(symbol, session=session, asynchronous=False)
        
        # Mapping Horizon
        p_map = {"Last Day": ("1d", "1m"), "Last Month": ("1mo", "1d"), 
                 "1 Year": ("1y", "1d"), "5 Years": ("5y", "1d")}
        period, interval = p_map.get(horizon, ("1y", "1d"))
        
        # 1. Fetch History with Type Check
        df = t.history(period=period, interval=interval)
        
        # Handle the 'str' object error by checking type immediately
        if isinstance(df, str):
            return None, {}
        if isinstance(df, dict):
            df = df.get(symbol)
            
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return None, {}

        # 2. Clean Data
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # 3. Safe Fundamentals Fetch (Prevents the 'str' Mapping Error)
        def get_safe_dict(prop):
            val = getattr(t, prop)
            if isinstance(val, dict):
                return val.get(symbol, {})
            return {}

        details = get_safe_dict('summary_detail')
        stats = get_safe_dict('key_stats')
        
        # Calculate 52W High/Low manually so they are never missing
        meta = {**details, **stats}
        meta['c52h'] = df['high'].max()
        meta['c52l'] = df['low'].min()
            
        return df, meta
    except Exception as e:
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. TOP NAVIGATION ---
st.title("🚀 Quantum Intelligence Terminal")
nav1, nav2, _ = st.columns([2, 2, 6])
with nav1:
    ticker = st.text_input("Symbol", value="SBIN.NS").upper()
with nav2:
    horizon = st.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2)

# --- 4. EXECUTION ---
data, meta = fetch_terminal_data(ticker, horizon)

if data is not None:
    data['rsi'] = calculate_rsi(data['close'])
    curr = data['close'].iloc[-1]
    rsi_val = data['rsi'].iloc[-1]
    
    # --- 5. EXECUTIVE DASHBOARD ---
    # Top Row: Pulse
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{curr:,.2f}")
    m2.metric("52W High", f"₹{meta['c52h']:,.2f}")
    m3.metric("52W Low", f"₹{meta['c52l']:,.2f}")
    
    rsi_status = "OVERBOUGHT" if rsi_val > 70 else "OVERSOLD" if rsi_val < 30 else "NEUTRAL"
    m4.metric("RSI (14)", f"{rsi_val:.1f}", rsi_status, delta_color="off")
    m5.metric("Mkt Cap", f"₹{meta.get('marketCap', 0)/1e7:,.0f} Cr")

    # Bottom Ribbon: Fundamentals
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.write(f"**P/E:** {meta.get('trailingPE', 'N/A')}")
    f2.write(f"**P/B:** {meta.get('priceToBook', 'N/A')}")
    f3.write(f"**D/E:** {meta.get('debtToEquity', 'N/A')}")
    f4.write(f"**Beta:** {meta.get('beta', 'N/A')}")
    f5.write(f"**Div:** {meta.get('dividendYield', 0)*100:.2f}%")

    st.divider()

    # --- 6. CHARTS ---
    # Price Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['date'], y=data['volume'], fill='tozeroy', 
                             fillcolor='rgba(0, 204, 255, 0.25)', line=dict(width=0), yaxis="y2"))
    
    if horizon == "Last Day":
        fig.add_trace(go.Scatter(x=data['date'], y=data['close'], line=dict(color='#00ffcc', width=2)))
    else:
        fig.add_trace(go.Candlestick(x=data['date'], open=data['open'], high=data['high'], 
                                     low=data['low'], close=data['close']))

    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['volume'].max()*4]),
                      margin=dict(l=0, r=0, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # RSI Chart
    fig_rsi = go.Figure()
    fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0)
    fig_rsi.add_trace(go.Scatter(x=data['date'], y=data['rsi'], line=dict(color='#AB63FA', width=1.5)))
    fig_rsi.update_layout(template="plotly_dark", height=250, yaxis=dict(range=[0, 100], tickvals=[30, 70]),
                          margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.warning("⚠️ Terminal is attempting to stabilize connection. Please ensure the ticker (SBIN.NS) is valid.")
    if st.button("Force Refresh Connection"):
        st.cache_data.clear()
        st.rerun()
