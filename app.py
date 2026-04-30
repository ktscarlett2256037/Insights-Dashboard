import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 2. THE SMART ENGINE ---
@st.cache_data(ttl=300)
def fetch_terminal_data(symbol, period=None, start=None, end=None, interval="1d"):
    try:
        t = Ticker(symbol, asynchronous=True)
        # Handle Custom Dates vs Presets
        if start and end:
            df = t.history(start=start, end=end, interval=interval)
        else:
            df = t.history(period=period, interval=interval)
            
        if df.empty: return None, None
        
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()
        
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # Fundamentals
        details = t.summary_detail.get(symbol, {})
        stats = t.key_stats.get(symbol, {})
        return df, {**details, **stats}
    except:
        return None, None

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. UI SIDEBAR: NAVIGATION ---
st.sidebar.title("🛠️ Terminal Controls")
ticker = st.sidebar.text_input("Symbol", value="SBIN.NS").upper()

mode = st.sidebar.radio("Time Input Method", ["Presets", "Custom Dates"])

if mode == "Presets":
    horizon = st.sidebar.selectbox("Horizon", 
                                  ["Last Day", "Last Month", "6 Months", "1 Year", "2 Years", "5 Years"], 
                                  index=3)
    # Map selection to API codes
    p_map = {"Last Day": "1d", "Last Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y"}
    selected_period = p_map[horizon]
    # For 'Last Day', we use 1-minute interval. For others, daily.
    selected_interval = "1m" if horizon == "Last Day" else "1d"
    start_date, end_date = None, None
else:
    col_s, col_e = st.sidebar.columns(2)
    start_date = col_s.date_input("Start", datetime.now() - timedelta(days=365))
    end_date = col_e.date_input("End", datetime.now())
    selected_period = None
    selected_interval = "1d"
    horizon = "Custom"

# --- 4. EXECUTION ---
data, fundamentals = fetch_terminal_data(ticker, selected_period, start_date, end_date, selected_interval)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    
    # KPIs
    m1, m2, m3, m4 = st.columns(4)
    curr = data['Close'].iloc[-1]
    m1.metric("LTP", f"₹{curr:,.2f}")
    m2.metric("52W High", f"₹{fundamentals.get('fiftyTwoWeekHigh', 0):,.2f}")
    m3.metric("52W Low", f"₹{fundamentals.get('fiftyTwoWeekLow', 0):,.2f}")
    m4.metric("Vol (K)", f"{data['Volume'].iloc[-1]/1000:,.1f}K")

    # --- 5. CHART 1: DYNAMIC PRICE CHART ---
    st.subheader(f"Price Action: {ticker}")
    fig_price = go.Figure()

    # AREA MAP VOLUME
    fig_price.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.2)', line=dict(color='rgba(0, 204, 255, 0)'),
        yaxis="y2", name="Volume"
    ))

    # TOGGLE: Line for 1-Day, Candlestick for Others
    if horizon == "Last Day":
        fig_price.add_trace(go.Scatter(
            x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2),
            fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.1)', name="Price"
        ))
    else:
        fig_price.add_trace(go.Candlestick(
            x=data['Date'], open=data['Open'], high=data['High'],
            low=data['Low'], close=data['Close'], name="Price"
        ))

    fig_price.update_layout(
        template="plotly_dark", height=500, xaxis_rangeslider_visible=False,
        yaxis=dict(title="Price (₹)", side="left"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 4]),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_price, use_container_width=True)

    # --- 6. CHART 2: CLEAN RSI ---
    st.subheader("Momentum: RSI (14)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=1.5)))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.3)
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.3)
    fig_rsi.update_layout(template="plotly_dark", height=200, yaxis=dict(range=[0, 100]), margin=dict(l=10, r=10, t=0, b=0))
    st.plotly_chart(fig_rsi, use_container_width=True)

    # --- 7. RATIO VAULT ---
    with st.expander("📊 Fundamental Ratios", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        f1.write(f"**P/E:** {fundamentals.get('trailingPE', 'N/A')}")
        f2.write(f"**Market Cap:** ₹{fundamentals.get('marketCap', 0)/1e7:,.2f} Cr")
        f3.write(f"**P/B Ratio:** {fundamentals.get('priceToBook', 'N/A')}")
        f4.write(f"**Debt/Equity:** {fundamentals.get('debtToEquity', 'N/A')}")

else:
    st.error(f"No data available for {ticker} in this range. Try a different period.")
