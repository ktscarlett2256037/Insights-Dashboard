import streamlit as st
from yahooquery import Ticker
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIG & ULTRA-WIDE STYLING ---
st.set_page_config(page_title="Quantum Terminal", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container {padding-top: 0.5rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem;}
    .stMetric {background-color: #161a25; padding: 10px; border-radius: 4px; border: 1px solid #2a2e39;}
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. ENGINE ---
@st.cache_data(ttl=300)
def fetch_terminal_data(symbol, period="1y", interval="1d"):
    try:
        t = Ticker(symbol, asynchronous=False)
        # Fetch 1y for 52w high/low calculations regardless of view
        df = t.history(period="1y" if period in ["1d", "1mo"] else period, interval=interval)
        
        if isinstance(df, dict): df = df.get(symbol)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty) or isinstance(df, str):
            return None, {}

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 
                           'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # Metadata & Manual 52W
        meta = {**t.summary_detail.get(symbol, {}), **t.key_stats.get(symbol, {})}
        meta['c52h'], meta['c52l'] = df['High'].max(), df['Low'].min()
        
        # Slice for display
        if period == "1d": display_df = df.tail(390)
        elif period == "1mo": display_df = df.tail(22)
        else: display_df = df
            
        return display_df, meta
    except:
        return None, {}

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# --- 3. TOP CONTROL BAR (Replaces Sidebar) ---
ctrl_col1, ctrl_col2, ctrl_col3, _ = st.columns([1.5, 1.5, 2, 5])
with ctrl_col1:
    ticker = st.text_input("Symbol", value="SBIN.NS", label_visibility="collapsed").upper()
with ctrl_col2:
    h_select = st.selectbox("Horizon", ["Last Day", "Last Month", "1 Year", "5 Years"], index=2, label_visibility="collapsed")

p_map = {"Last Day": "1d", "Last Month": "1mo", "1 Year": "1y", "5 Years": "5y"}
selected_period = p_map[h_select]
selected_interval = "1m" if h_select == "Last Day" else "1d"

# --- 4. DATA EXECUTION ---
data, meta = fetch_terminal_data(ticker, selected_period, selected_interval)

if data is not None:
    data['RSI'] = calculate_rsi(data['Close'])
    curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
    change = ((curr - prev) / prev) * 100
    curr_rsi = data['RSI'].iloc[-1]

    # --- 5. DATA RIBBON (Metrics & Fundamentals Combined) ---
    # Metric Row
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    m_col1.metric("Price", f"₹{curr:,.2f}", f"{change:.2f}%")
    m_col2.metric("52W High", f"₹{meta['c52h']:,.2f}")
    m_col3.metric("52W Low", f"₹{meta['c52l']:,.2f}")
    
    # RSI Logic
    rsi_desc = "OVERBOUGHT" if curr_rsi > 70 else "OVERSOLD" if curr_rsi < 30 else "NEUTRAL"
    m_col4.metric("RSI (14)", f"{curr_rsi:.1f}", rsi_desc, delta_color="off")
    
    m_col5.metric("Mkt Cap", f"₹{meta.get('marketCap', 0)/1e7:,.0f}Cr")
    m_col6.metric("P/E Ratio", f"{meta.get('trailingPE', 'N/A')}")

    # Fundamental Sub-Ribbon
    f_col1, f_col2, f_col3, f4_col4, f_col5 = st.columns(5)
    f_col1.caption(f"**P/B:** {meta.get('priceToBook', 'N/A')}")
    f_col2.caption(f"**D/E:** {meta.get('debtToEquity', 'N/A')}")
    f_col3.caption(f"**Div Yield:** {meta.get('dividendYield', 0)*100:.2f}%")
    f4_col4.caption(f"**Beta:** {meta.get('beta', 'N/A')}")
    f_col5.caption(f"**Avg Vol:** {meta.get('averageVolume', 0)/1000:,.0f}K")

    # --- 6. CHARTS ---
    # Price Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['Date'], y=data['Volume'], fill='tozeroy',
        fillcolor='rgba(0, 204, 255, 0.15)', line=dict(color='rgba(0,0,0,0)'),
        yaxis="y2", name="Volume"
    ))
    
    if h_select == "Last Day":
        fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], line=dict(color='#00ffcc', width=2), name="Price"))
    else:
        fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"))

    fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False,
                      margin=dict(l=0, r=0, t=10, b=0),
                      yaxis=dict(gridcolor="#2a2e39", side="left"),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, range=[0, data['Volume'].max() * 5]))
    st.plotly_chart(fig, use_container_width=True)

    # RSI Chart
    fig_rsi = go.Figure()
    fig_rsi.add_hrect(y0=30, y1=70, fillcolor="#2a2e39", opacity=0.3, line_width=0)
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='#AB63FA', width=1.5)))
    fig_rsi.add_hline(y=70, line_color="#ff4b4b", line_dash="dot", opacity=0.5)
    fig_rsi.add_hline(y=30, line_color="#00ffcc", line_dash="dot", opacity=0.5)
    fig_rsi.update_layout(template="plotly_dark", height=150, margin=dict(l=0, r=0, t=0, b=0),
                          yaxis=dict(range=[0, 100], tickvals=[30, 70], gridcolor="#2a2e39"))
    st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.error("System offline or invalid ticker.")
