import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. CORE FUNCTIONS (The Math behind the scenes) ---

def calculate_rsi(data, window=14):
    """Calculates the Relative Strength Index (RSI)"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_vwap(df):
    """Calculates Volume Weighted Average Price"""
    v = df['Volume']
    p = df['Close']
    return (p * v).cumsum() / v.cumsum()

# --- 2. DATA ENGINE ---

@st.cache_data
def get_stock_data(ticker, period):
    # Fetch data including OHLCV (Open, High, Low, Close, Volume)
    df = yf.download(ticker, period=period)
    return df

# --- 3. UI LAYOUT ---

st.title("Insights Dashboard")

# Sidebar for Ticker Input
ticker = st.sidebar.text_input("Enter Ticker (NSE Stocks end in .NS)", value="HDFCBANK.NS").upper()
time_period = st.sidebar.selectbox("Select History", ["1mo", "6mo", "1y", "2y", "5y"], index=2)

try:
    data = get_stock_data(ticker, time_period)
    
    if data.empty:
        st.error("No data found. Please check the ticker symbol (e.g., RELIANCE.NS).")
    else:
        # Calculate our indicators
        data['RSI'] = calculate_rsi(data['Close'])
        data['VWAP'] = calculate_vwap(data)
        
        # Tabs Initialization
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Pulse", "🛡️ Risk", "Σ Alpha", "🌐 Macro", "🧪 Portfolio"])

        with tab1:
            # --- KPI ROW ---
            c1, c2, c3, c4 = st.columns(4)
            
            curr_price = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2]
            change = curr_price - prev_close
            pct_change = (change / prev_close) * 100
            
            c1.metric("LTP", f"₹{curr_price:,.2f}", f"{pct_change:.2f}%")
            
            # 52-Week High/Low logic
            year_data = data.tail(252) # Roughly 1 year of trading days
            c2.metric("52W High", f"₹{year_data['High'].max():,.2f}")
            c3.metric("52W Low", f"₹{year_data['Low'].min():,.2f}")
            
            # Volume Surge (Current vs 20-Day Average)
            avg_vol = data['Volume'].tail(20).mean()
            curr_vol = data['Volume'].iloc[-1]
            surge = curr_vol / avg_vol
            c4.metric("Volume Surge", f"{surge:.2x}", help="Current Volume relative to 20-day average")

            st.divider()

            # --- DUAL-CHART (Price + Volume + RSI) ---
            # We use subplots to keep them stacked and professional
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, 
                               row_heights=[0.6, 0.2, 0.2])

            # Row 1: Candlestick & VWAP
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], 
                                        low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name="VWAP", line=dict(color='orange', width=1)), row=1, col=1)

            # Row 2: Volume
            # Color code volume bars (Green if close > open, else Red)
            colors = ['green' if row['Close'] >= row['Open'] else 'red' for _, row in data.iterrows()]
            fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume", marker_color=colors), row=2, col=1)

            # Row 3: RSI
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple')), row=3, col=1)
            # Add the 70/30 lines for RSI
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

            fig.update_layout(height=800, showlegend=False, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # --- RESEARCH & NEWS ---
            st.subheader("Market Intelligence")
            n_col1, n_col2 = st.columns([1, 2])
            
            with n_col1:
                st.write("**Event Discovery**")
                target_date = st.date_input("Select date to research news", value=datetime.now() - timedelta(days=1))
                # Generate Google News link
                clean_ticker = ticker.replace(".NS", "")
                search_url = f"https://www.google.com/search?q={clean_ticker}+stock+news+after:{target_date - timedelta(days=1)}+before:{target_date + timedelta(days=1)}"
                st.link_button(f"🔍 Search News for {target_date}", search_url)
                
            with n_col2:
                st.write("**Top Headlines**")
                ticker_obj = yf.Ticker(ticker)
                for item in ticker_obj.news[:5]:
                    st.markdown(f"- **[{item['title']}]({item['link']})**")
                    st.caption(f"Source: {item['publisher']}")

except Exception as e:
    st.info("Please enter a valid NSE ticker symbol (e.g., SBIN.NS) to begin analysis.")
