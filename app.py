import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# --- 1. CONFIG & QUANT STYLING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    [data-testid="stMetricValue"] { font-size: 1.25rem !important; color: #00ffcc; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    .stMetric {
        background-color: #11141d; 
        padding: 12px !important; 
        border-radius: 4px; 
        border: 1px solid #2a2e39;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE DYNAMIC ENGINE ---
@st.cache_data(ttl=3600)
def fetch_terminal_data(symbol, api_key, horizon, is_demo=False):
    if is_demo or not api_key:
        # Mocking 2000 points to support "MAX" and "5Y" views
        dates = pd.date_range(end=datetime.now(), periods=2000)
        df = pd.DataFrame({
            'Date': dates,
            'open': np.random.uniform(1000, 1100, 2000),
            'high': np.random.uniform(1100, 1150, 2000),
            'low': np.random.uniform(950, 1000, 2000),
            'close': np.random.uniform(1000, 1100, 2000),
            'volume': np.random.randint(100000, 1000000, 2000)
        })
        return df, {'h52': 1254.7, 'l52': 900.0, 'mcap': 54500, 'pe': 25.4, 'pb': 3.2}

    try:
        clean_ticker = symbol.replace('.NS', '')
        # Determine if we need Intraday or Daily
        if horizon == "Last Day":
            url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=NSE:{clean_ticker}&interval=5min&apikey={api_key}'
            key = 'Time Series (5min)'
        else:
            url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=NSE:{clean_ticker}&outputsize=full&apikey={api_key}'
            key = 'Time Series (Daily)'
            
        r = requests.get(url)
        data = r.json()
        ts = data[key]
        df = pd.DataFrame.from_dict(ts, orient='index').astype(float)
        df = df.reset_index().rename(columns={'index': 'Date', '1. open': 'open', '2. high': 'high', '3. low': 'low', '4. close': 'close', '5. volume': 'volume'})
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        return df, {'h52': df['high'].tail(252).max(), 'l52': df['low'].tail(252).min(), 'mcap': 54500, 'pe': 22.1, 'pb': 2.8}
    except:
        return None, {}

# --- 3. TOP NAVIGATION ---
st.title("🚀 Quantum Intelligence Terminal")
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("API Key", type="password")
demo_mode = st.sidebar.checkbox("Enable Demo Mode", value=True)

t1, t2, _ = st.columns([1.5, 2, 6.5])
with t1:
    ticker = st.text_input("Ticker", value="SBIN.NS", label_visibility="collapsed").upper()
with t2:
    horizon = st.selectbox("Horizon", ["Last Day", "Last Week", "Last Month", "6 Months", "1 Year", "5 Years", "MAX"], index=4, label_visibility="collapsed")

# --- 4. DATA PROCESSING ---
full_data, meta = fetch_terminal_data(ticker, api_key, horizon, is_demo=demo_mode)

if full_data is not None:
    # Range Slicing
    range_map = {"Last Day": 78, "Last Week": 5, "Last Month": 22, "6 Months": 126, "1 Year": 252, "5 Years": 1260, "MAX": len(full_data)}
    data = full_data.tail(range_map[horizon])
    curr = data['close'].iloc[-1]

    # --- 5. EXECUTIVE RIBBON ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{curr:,.2f}")
    m2.metric("52W High", f"₹{meta['h52']:,.2f}")
    m3.metric("52W Low", f"₹{meta['l52']:,.2f}")
    m4.metric("Mkt Cap", f"₹{meta['mcap']:,} Cr")
    m5.metric("P/E Ratio", f"{meta['pe']}")

    st.divider()

    # --- 6. THE "COMFORTABLE" CHART ---
    fig = go.Figure()

    # CANDLESTICKS
    fig.add_trace(go.Candlestick(
        x=data['Date'], open=data['open'], high=data['high'], 
        low=data['low'], close=data['close'], name="Price"
    ))

    # TRENDLINE (CLOSE PATH)
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['close'], 
        line=dict(color='rgba(255, 255, 255, 0.4)', width=1.5), 
        name="Close Path", hoverinfo='skip'
    ))

    # BOTTOM-WEIGHTED VOLUME BARS
    fig.add_trace(go.Bar(
        x=data['Date'], y=data['volume'], 
        marker_color='rgba(0, 204, 255, 0.3)', 
        yaxis="y2", name="Volume", hoverinfo='skip'
    ))

    # Calculate "Comfortable" Vertical Scale (20% Headroom)
    p_min, p_max = data['low'].min(), data['high'].max()
    p_range = p_max - p_min
    
    fig.update_layout(
        template="plotly_dark", height=650, 
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        
        # PRIMARY Y-AXIS (Price with Padding)
        yaxis=dict(
            gridcolor="#2a2e39", title="Price (₹)",
            range=[p_min - (p_range * 0.2), p_max + (p_range * 0.2)] 
        ),
        
        # SECONDARY Y-AXIS (Volume locked to bottom 25%)
        yaxis2=dict(
            overlaying="y", side="right", showgrid=False, 
            range=[0, data['volume'].max() * 4] 
        ),
        xaxis=dict(gridcolor="#2a2e39", nticks=12)
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Terminal Connection Error.")
