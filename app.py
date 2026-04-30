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
        t = Ticker(symbol, asynchronous=False)
        
        # To calculate 52W metrics reliably, we fetch a full year if the preset is short
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
        
        # Calculate 52W High/Low manually from the fetched data
        # (This ensures the metrics are NEVER missing)
        calc_52w_high = df['High'].max()
        calc_52w_low = df['Low'].min()
        
        # If the user only wanted a shorter period, we crop the display data now
        # but keep the 52W stats we just calculated.
        display_df = df.copy()
        if period == "1d": display_df = df.tail(390) # Approx 1 day of 1m data
        elif period == "1mo": display_df = df.tail(22)
            
        summary = t.summary_detail.get(symbol, {})
        stats = t.key_stats.get(symbol, {})
        
        meta = {
            **summary, **stats, 
            'calc_52h': calc_52w_high, 
            'calc_52l': calc_52w_low
        }
            
        return display_df, meta
    except Exception as e:
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. UI CONTROLS ---
st.sidebar.title("🛠️ Terminal Controls")
ticker = st.sidebar.text_input("Symbol", value="SBIN.NS").upper()
mode = st.sidebar.radio("Range", ["Presets", "Custom Dates"])

if mode == "Presets":
    h = st.sidebar.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2)
    p_map = {"Last Day": "1d", "Last Month": "1mo", "1 Year": "1y", "5 Years": "5y"}
    selected_period = p_map[h]
    selected_interval = "1m" if h == "Last Day" else "1d"
    start_date, end_date = None, None
else:
    col_s, col_e = st.sidebar.columns(2)
    start_date = col_s.date_input("Start", datetime.now() - timedelta(days=365))
    end_date = col_e.date_input("End", datetime.now())
    selected_period, selected_interval = None, "1d"
    h = "Custom"

# --- 4. EXECUTION ---
data, meta = fetch_terminal_data(ticker, selected_period, start_date, end_date, selected_interval)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    
    # KPI SECTION
    m1, m2, m3, m4 = st.columns(4)
    curr = data['Close'].iloc[-1]
    m1.metric("LTP", f"₹{curr:,.2f}")
    # Using calculated metrics as fallback
    m2.metric("52W High", f"₹{meta.get('calc_52h', 0):,.2f}")
    m3.metric("52W Low", f"₹{meta.get('calc_52l', 0):,.2f}")
    m4.metric("Vol (K)", f"{data['Volume'].iloc[-1]/1000:,.1f}K")

    # --- 5. MAIN PRICE CHART ---
    st.subheader(f"Price Action & Liquidity Map: {ticker}")
    fig = go.Figure()

    # Enhanced Volume Area
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.2)', line=dict(color='rgba(0, 204, 255, 0.4)', width=1),
        yaxis="y2", name="Volume"
    ))

    if h == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2.5), name="Price"))
    else:
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"))

    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False,
                      yaxis=dict(title="Price (₹)", side="left", gridcolor="#333"),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 4]))
    st.plotly_chart(fig, use_container_width=True)

    # --- 6. PRO RSI CHART ---
    st.subheader("Momentum: RSI (14)")
    fig_rsi = go.Figure()
    
    # Shaded Neutral Zone (30-70)
    fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0)
    
    fig_rsi.add_trace(go.Scatter(
        x=data['Date'], y=data['RSI'], 
        line=dict(color='#AB63FA', width=2),
        name="RSI"
    ))
    
    # Threshold Lines
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
    
    fig_rsi.update_layout(
        template="plotly_dark", 
        height=350, # INCREASED HEIGHT
        yaxis=dict(range=[0, 100], title="RSI Value", gridcolor="#333"),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_rsi, use_container_width=True)

    with st.expander("📊 Fundamental Pulse", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        f1.write(f"**P/E Ratio:** {meta.get('trailingPE', 'N/A')}")
        f2.write(f"**Market Cap:** ₹{meta.get('marketCap', 0)/1e7:,.2f} Cr")
        f3.write(f"**P/B Ratio:** {meta.get('priceToBook', 'N/A')}")
        f4.write(f"**Avg Volume:** {meta.get('averageVolume', 0)/1000:,.0f}K")
else:
    st.error("📡 Data fetch failed. Check connection or symbol.")
