import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. CONFIG ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# --- 2. THE HARDENED ENGINE ---
@st.cache_data(ttl=300)
def fetch_terminal_data(symbol, period=None, start=None, end=None, interval="1d"):
    try:
        # Switching to synchronous (asynchronous=False) for better stability on cloud
        t = Ticker(symbol, asynchronous=False)
        
        # 1. Fetch Price Data
        if start and end:
            df = t.history(start=start, end=end, interval=interval)
        else:
            df = t.history(period=period, interval=interval)
            
        # CRITICAL CHECK: Yahooquery returns a dict of dataframes OR a string on failure
        if isinstance(df, dict):
            # If it's a dict, the actual data is under the symbol key
            df = df.get(symbol)
            
        if df is None or (isinstance(df, pd.DataFrame) and df.empty) or isinstance(df, str):
            return None, {}

        # Reset index if necessary
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()
        elif not isinstance(df.index, pd.RangeIndex):
            df = df.reset_index()

        # Rename columns to standard format
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # 2. Fetch Fundamentals
        summary = t.summary_detail.get(symbol, {})
        stats = t.key_stats.get(symbol, {})
        
        # Ensure we return dictionaries, not strings
        summary = summary if isinstance(summary, dict) else {}
        stats = stats if isinstance(stats, dict) else {}
            
        return df, {**summary, **stats}
    except Exception as e:
        st.sidebar.error(f"Engine Error: {str(e)}")
        return None, {}

def calculate_rsi(series, window=14):
    if len(series) < window: return pd.Series([np.nan] * len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. UI CONTROLS ---
st.sidebar.title("🛠️ Terminal Controls")
ticker = st.sidebar.text_input("Symbol (e.g., SBIN.NS)", value="SBIN.NS").upper()
mode = st.sidebar.radio("Range Selection", ["Presets", "Custom Dates"])

if mode == "Presets":
    horizon = st.sidebar.selectbox("Horizon", ["Last Day", "Last Month", "6 Months", "1 Year", "5 Years"], index=3)
    p_map = {"Last Day": "1d", "Last Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "5 Years": "5y"}
    selected_period = p_map[horizon]
    selected_interval = "1m" if horizon == "Last Day" else "1d"
    start_date, end_date = None, None
else:
    col_s, col_e = st.sidebar.columns(2)
    start_date = col_s.date_input("Start", datetime.now() - timedelta(days=365))
    end_date = col_e.date_input("End", datetime.now())
    selected_period, selected_interval = None, "1d"
    horizon = "Custom"

# --- 4. EXECUTION ---
data, fundamentals = fetch_terminal_data(ticker, selected_period, start_date, end_date, selected_interval)

if data is not None and not data.empty:
    data['RSI'] = calculate_rsi(data['Close'])
    
    # KPI SECTION
    m1, m2, m3, m4 = st.columns(4)
    curr = data['Close'].iloc[-1]
    m1.metric("LTP", f"₹{curr:,.2f}")
    m2.metric("52W High", f"₹{fundamentals.get('fiftyTwoWeekHigh', 0):,.2f}")
    m3.metric("52W Low", f"₹{fundamentals.get('fiftyTwoWeekLow', 0):,.2f}")
    m4.metric("Vol (K)", f"{data['Volume'].iloc[-1]/1000:,.1f}K")

    # MAIN CHART
    st.subheader(f"Price Action: {ticker}")
    fig = go.Figure()

    # Brighter Volume Area
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.3)', line=dict(color='rgba(0, 0, 0, 0)'),
        yaxis="y2", name="Volume"
    ))

    if horizon == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=3), name="Price"))
    else:
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"))

    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False,
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 4]))
    st.plotly_chart(fig, use_container_width=True)

    # RSI CHART
    st.subheader("Momentum: RSI (14)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=2)))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
    fig_rsi.update_layout(template="plotly_dark", height=200, yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.error(f"❌ Could not retrieve price data for '{ticker}'.")
    st.info("Check if the ticker includes the suffix (e.g., .NS for NSE) or try a different time range.")
