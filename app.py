import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & MAPPING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide")

# Mapping the user-friendly dropdown to YahooQuery codes
TIME_MAP = {
    "Last Day": ("1d", "1m"),
    "Last Month": ("1mo", "1d"),
    "Last 6 Months": ("6mo", "1d"),
    "Last 1 Year": ("1y", "1d"),
    "Last 2 Years": ("2y", "1d"),
    "Last 3 Years": ("3y", "1d"),
    "Last 4 Years": ("4y", "1d"),
    "Last 5 Years": ("5y", "1d")
}

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_terminal_data(symbol, period, interval):
    try:
        t = Ticker(symbol, asynchronous=True)
        df = t.history(period=period, interval=interval)
        if df.empty: return None
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return df
    except:
        return None

# --- 3. QUANT LOGIC ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def interpret_rsi(val):
    if val >= 70: return "🔴 Overbought (Possible Reversal)", "inverse"
    if val <= 30: return "🟢 Oversold (Possible Bounce)", "normal"
    return "⚪ Neutral Zone", "off"

# --- 4. UI SIDEBAR ---
st.title("🚀 Quantum Intelligence Terminal")
ticker = st.sidebar.text_input("Symbol", value="SBIN.NS").upper()
horizon = st.sidebar.selectbox("Time Horizon", list(TIME_MAP.keys()), index=3)

selected_period, selected_interval = TIME_MAP[horizon]

# --- 5. EXECUTION ---
data = fetch_terminal_data(ticker, selected_period, selected_interval)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    
    # KPIs
    curr_price = data['Close'].iloc[-1]
    curr_rsi = data['RSI'].iloc[-1]
    rsi_text, rsi_color = interpret_rsi(curr_rsi)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("LTP", f"₹{curr_price:,.2f}")
    col2.metric("Vol (Session)", f"{data['Volume'].iloc[-1]:,.0f}")
    col3.metric("RSI Value", f"{curr_rsi:.2f}")
    col4.write(f"**RSI Interpretation:** \n {rsi_text}")

    # --- 6. MULTI-STAGE CHARTING ---
    # Rows: 1. Price/Candlestick, 2. RSI
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.05, 
                       row_heights=[0.7, 0.3],
                       subplot_titles=(f"{ticker} Price Action", "Relative Strength Index (RSI)"))

    # A. Price Chart (Candlesticks)
    fig.add_trace(go.Candlestick(
        x=data['Date'], open=data['Open'], high=data['High'], 
        low=data['Low'], close=data['Close'], name="Price"
    ), row=1, col=1)

    # B. Volume (Overlaid on Price)
    fig.add_trace(go.Bar(
        x=data['Date'], y=data['Volume'], name="Volume",
        marker_color='rgba(100, 100, 100, 0.3)', yaxis="y2"
    ), row=1, col=1)

    # C. RSI Chart
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['RSI'], name="RSI", 
        line=dict(color='#AB63FA', width=2)
    ), row=2, col=1)

    # RSI Bounds
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0, row=2, col=1)

    # Layout Customization
    fig.update_layout(
        template="plotly_dark",
        height=800,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        yaxis=dict(title="Price (₹)"),
        yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
        yaxis3=dict(title="RSI", range=[0, 100])
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.success(f"Dashboard updated for {horizon}")

else:
    st.error("📡 Data fetch failed. YahooQuery might be resetting. Please wait 10 seconds.")
