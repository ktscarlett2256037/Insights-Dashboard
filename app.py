import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIG ---
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
def fetch_full_data(symbol, period, interval):
    try:
        t = Ticker(symbol, asynchronous=True)
        
        # Historical Data
        hist = t.history(period=period, interval=interval)
        if hist.empty: return None, None
        
        if isinstance(hist.index, pd.MultiIndex):
            hist = hist.reset_index()
        
        hist.columns = [c.lower() for c in hist.columns]
        hist.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                             'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # Fundamental Data
        details = t.summary_detail.get(symbol, {})
        stats = t.key_stats.get(symbol, {})
        
        return hist, {**details, **stats}
    except:
        return None, None

# --- 3. MATH ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 4. UI SIDEBAR & HEADER ---
st.title("🚀 Quantum Intelligence Terminal")
ticker = st.sidebar.text_input("Symbol", value="SBIN.NS").upper()
horizon = st.sidebar.selectbox("Time Horizon", list(TIME_MAP.keys()), index=3)
selected_period, selected_interval = TIME_MAP[horizon]

data, fundamentals = fetch_full_data(ticker, selected_period, selected_interval)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    
    # --- 5. TOP METRICS ROW (The Important Numbers) ---
    m1, m2, m3, m4 = st.columns(4)
    
    # Price & Change
    curr = data['Close'].iloc[-1]
    prev = data['Close'].iloc[-2]
    change = ((curr - prev) / prev) * 100
    m1.metric("LTP", f"₹{curr:,.2f}", f"{change:.2f}%")
    
    # 52 Week High/Low (From Fundamentals)
    hi_52 = fundamentals.get('fiftyTwoWeekHigh', 0)
    lo_52 = fundamentals.get('fiftyTwoWeekLow', 0)
    m2.metric("52W High", f"₹{hi_52:,.2f}")
    m3.metric("52W Low", f"₹{lo_52:,.2f}")
    
    # Volume in Thousands (K)
    vol_k = data['Volume'].iloc[-1] / 1000
    m4.metric("Vol (K)", f"{vol_k:,.1f}K")

    # --- 6. CHART 1: PRICE & BRIGHTER VOLUME AREA ---
    st.subheader("Price Action & Liquidity Map")
    
    fig_price = go.Figure()

    # Brighter Translucent Volume Area Map
    fig_price.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'],
        name="Volume",
        fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.25)', # Brighter Cyber Blue
        line=dict(color='rgba(0, 204, 255, 0.4)', width=1),
        yaxis="y2"
    ))

    # Candlestick Chart
    fig_price.add_trace(go.Candlestick(
        x=data['Date'], open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'], name="Price"
    ))

    fig_price.update_layout(
        template="plotly_dark",
        height=550,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        yaxis=dict(title="Price (₹)", side="left", gridcolor="#333"),
        # Adjust range to keep volume at bottom 30% of chart
        yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 3.5]),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_price, use_container_width=True)

    # --- 7. CHART 2: SEPARATE RSI ---
    st.subheader("Momentum: RSI (14)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=2)))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5)
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5)
    fig_rsi.update_layout(template="plotly_dark", height=200, yaxis=dict(range=[0, 100]), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_rsi, use_container_width=True)

    # --- 8. THE RATIO VAULT (Fundamental Details) ---
    with st.expander("📊 Fundamental Pulse & Ratios", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        
        pe_ratio = fundamentals.get('trailingPE', 'N/A')
        mkt_cap = fundamentals.get('marketCap', 0) / 1e7 # Convert to Crores
        avg_vol = fundamentals.get('averageVolume', 0) / 1000
        
        f1.write(f"**P/E Ratio:** {pe_ratio}")
        f2.write(f"**Market Cap:** ₹{mkt_cap:,.2f} Cr")
        f3.write(f"**Avg Vol (10D):** {avg_vol:,.1f}K")
        f4.write(f"**Ex-Dividend:** {fundamentals.get('exDividendDate', 'N/A')}")

else:
    st.error("📡 Connection to Exchange Interrupted.")
