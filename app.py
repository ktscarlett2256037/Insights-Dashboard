import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# Custom CSS to reduce padding and make it look "Dense"
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #1e2130; padding: 10px; border-radius: 5px; border: 1px solid #333;}
    [data-testid="stExpander"] {border: none !important; box-shadow: none !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ENGINE ---
@st.cache_data(ttl=300)
def fetch_terminal_data(symbol, period=None, start=None, end=None, interval="1d"):
    try:
        t = Ticker(symbol, asynchronous=False)
        fetch_period = "1y" if period in ["1d", "1mo", "6mo"] else period
        
        if start and end:
            df = t.history(start=start, end=end, interval=interval)
        else:
            df = t.history(period=fetch_period, interval=interval)
            
        if isinstance(df, dict): df = df.get(symbol)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty) or isinstance(df, str):
            return None, {}

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        meta = {**t.summary_detail.get(symbol, {}), **t.key_stats.get(symbol, {})}
        meta['calc_52h'] = df['High'].max()
        meta['calc_52l'] = df['Low'].min()
            
        return df, meta
    except:
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. UI SIDEBAR ---
st.sidebar.title("🛠️ Controls")
ticker = st.sidebar.text_input("Symbol", value="SBIN.NS").upper()
h_select = st.sidebar.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2)
p_map = {"Last Day": "1d", "Last Month": "1mo", "1 Year": "1y", "5 Years": "5y"}
selected_period = p_map[h_select]
selected_interval = "1m" if h_select == "Last Day" else "1d"

# --- 4. EXECUTION ---
data, meta = fetch_terminal_data(ticker, selected_period, None, None, selected_interval)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    curr = data['Close'].iloc[-1]
    prev = data['Close'].iloc[-2]
    change = ((curr - prev) / prev) * 100
    curr_rsi = data['RSI'].iloc[-1]
    
    # --- 5. THE EXECUTIVE RIBBON (Top View) ---
    # This utilizes the top space for all key info
    st.markdown(f"### 🚀 {ticker} | Quantum Executive Summary")
    
    # Row 1: Market Pulse
    r1_col1, r1_col2, r1_col3, r1_col4, r1_col5 = st.columns(5)
    
    r1_col1.metric("LTP", f"₹{curr:,.2f}", f"{change:.2f}%")
    
    # 52W Stats
    r1_col2.metric("52W High", f"₹{meta.get('calc_52h', 0):,.2f}")
    r1_col3.metric("52W Low", f"₹{meta.get('calc_52l', 0):,.2f}")
    
    # RSI One-Shot
    rsi_signal = "OVERBOUGHT" if curr_rsi > 70 else "OVERSOLD" if curr_rsi < 30 else "NEUTRAL"
    r1_col4.metric("RSI (14)", f"{curr_rsi:.1f}", rsi_signal, delta_color="off")
    
    # Liquidity
    vol_display = f"{data['Volume'].iloc[-1]/1000:,.1f}K" if data['Volume'].iloc[-1] < 1000000 else f"{data['Volume'].iloc[-1]/1000000:,.2f}M"
    r1_col5.metric("Session Vol", vol_display)

    # Row 2: Fundamental Ratios (Now at the top!)
    r2_col1, r2_col2, r2_col3, r2_col4, r2_col5 = st.columns(5)
    
    mkt_cap = meta.get('marketCap', 0) / 1e7
    r2_col1.write(f"**Mkt Cap:** ₹{mkt_cap:,.0f} Cr")
    r2_col2.write(f"**P/E Ratio:** {meta.get('trailingPE', 'N/A')}")
    r2_col3.write(f"**P/B Ratio:** {meta.get('priceToBook', 'N/A')}")
    r2_col4.write(f"**D/E Ratio:** {meta.get('debtToEquity', 'N/A')}")
    r2_col5.write(f"**Dividend:** {meta.get('dividendYield', 0)*100:.2f}%")

    st.divider()

    # --- 6. THE CHARTING ENGINE ---
    # Create a 2-column layout for main charts and secondary info
    chart_main, chart_side = st.columns([4, 1])

    with chart_main:
        # MAIN PRICE CHART
        fig = go.Figure()
        # Cyber Blue Volume Map
        fig.add_trace(go.Scatter(
            x=data['Date'], y=data['Volume'], fill='tozeroy',
            fillcolor='rgba(0, 204, 255, 0.2)', line=dict(color='rgba(0, 204, 255, 0)'),
            yaxis="y2", name="Volume"
        ))
        # Candlestick or Line
        if h_select == "Last Day":
            fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2), name="Price"))
        else:
            fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"))

        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                          margin=dict(l=0, r=0, t=0, b=0),
                          yaxis=dict(gridcolor="#333"),
                          yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 4]))
        st.plotly_chart(fig, use_container_width=True)

        # RSI CHART (One-Shot view)
        fig_rsi = go.Figure()
        fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0)
        fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=1.5)))
        fig_rsi.update_layout(template="plotly_dark", height=180, yaxis=dict(range=[0, 100], tickvals=[30, 70]), margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_rsi, use_container_width=True)

    with chart_side:
        st.markdown("#### 🛡️ Risk Check")
        returns = data['Close'].pct_change().dropna()
        ann_vol = returns.std() * np.sqrt(252)
        st.write(f"**Annual Vol:** \n {ann_vol:.2%}")
        
        max_dd = ((data['Close'] - data['Close'].cummax()) / data['Close'].cummax()).min()
        st.write(f"**Max Drawdown:** \n {max_dd:.2%}")
        
        st.markdown("---")
        st.markdown("#### 🧪 Signal")
        if curr_rsi > 70: st.error("SELL SIGNAL")
        elif curr_rsi < 30: st.success("BUY SIGNAL")
        else: st.warning("WAIT")

else:
    st.error("📡 Terminal Offline. Check Ticker.")
