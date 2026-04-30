import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# --- 1. CONFIG & PRECISION STYLING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    .stMetric {
        background-color: #11141d; 
        padding: 10px 15px !important; 
        border-radius: 4px; 
        border: 1px solid #2a2e39;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ENGINE ---
@st.cache_data(ttl=3600)
def fetch_terminal_data(symbol, api_key, is_demo=False):
    if is_demo or not api_key:
        dates = pd.date_range(end=datetime.now(), periods=252)
        df = pd.DataFrame({
            'Date': dates, 'open': np.random.uniform(1000, 1100, 252),
            'high': np.random.uniform(1100, 1150, 252), 'low': np.random.uniform(950, 1000, 252),
            'close': np.random.uniform(1000, 1100, 252), 'volume': np.random.randint(100000, 1000000, 252)
        })
        return df, {'h52': 1254.7, 'l52': 900.0, 'mcap': 54500, 'pe': 25.4, 'pb': 3.2, 'de': 0.5, 'beta': 1.1}

    try:
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=NSE:{symbol.replace(".NS", "")}&apikey={api_key}&outputsize=full'
        r = requests.get(url)
        data = r.json()
        ts = data['Time Series (Daily)']
        df = pd.DataFrame.from_dict(ts, orient='index').astype(float)
        df = df.reset_index().rename(columns={'index': 'Date', '1. open': 'open', '2. high': 'high', '3. low': 'low', '4. close': 'close', '5. volume': 'volume'})
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        return df, {'h52': df['high'].max(), 'l52': df['low'].min(), 'mcap': 54500, 'pe': 22.1, 'pb': 2.8, 'de': 0.6, 'beta': 1.05}
    except:
        return None, {}

# --- 3. UI CONTROLS ---
st.title("🚀 Quantum Intelligence Terminal")
st.sidebar.header("Chart Settings")
axis_type = st.sidebar.radio("Vertical Axis Scale", ["Linear", "Logarithmic"], index=0)
demo_mode = st.sidebar.checkbox("Enable Demo Mode", value=True)

t1, t2, _ = st.columns([1.5, 2, 6.5])
with t1:
    ticker = st.text_input("Ticker", value="SBIN.NS", label_visibility="collapsed").upper()
with t2:
    range_select = st.selectbox("View Horizon", ["1 Month", "3 Months", "6 Months", "1 Year"], index=1, label_visibility="collapsed")

# --- 4. EXECUTION ---
full_data, meta = fetch_terminal_data(ticker, st.sidebar.text_input("API Key", type="password"), is_demo=demo_mode)

if full_data is not None:
    # Slicing logic for clarity
    range_map = {"1 Month": 22, "3 Months": 63, "6 Months": 126, "1 Year": 252}
    data = full_data.tail(range_map[range_select])
    
    # --- 5. DATA RIBBON ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{data['close'].iloc[-1]:,.2f}")
    m2.metric("52W High", f"₹{meta['h52']:,.2f}")
    m3.metric("52W Low", f"₹{meta['l52']:,.2f}")
    m4.metric("Mkt Cap", f"₹{meta['mcap']:,} Cr")
    m5.metric("P/E Ratio", f"{meta['pe']}")

    st.divider()

    # --- 6. DYNAMIC VERTICAL CHARTING ---
    fig = go.Figure()
    
    # Volume Area
    fig.add_trace(go.Scatter(x=data['Date'], y=data['volume'], fill='tozeroy', fillcolor='rgba(0, 204, 255, 0.12)', line=dict(width=0), yaxis="y2", name="Volume"))
    
    # Main Candlesticks
    fig.add_trace(go.Candlestick(x=data['Date'], open=data['open'], high=data['high'], low=data['low'], close=data['close'], name="Price"))
    
    # Vertical Axis Logic
    y_scale = "log" if axis_type == "Logarithmic" else "linear"
    
    fig.update_layout(
        template="plotly_dark", height=550, xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(
            type=y_scale, 
            gridcolor="#2a2e39", 
            title="Price (₹)", 
            autorange=True, # Snaps vertical axis to current data
            fixedrange=False
        ),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['volume'].max()*6])
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Connection Failed.")
