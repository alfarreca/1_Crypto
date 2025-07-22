import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD
from datetime import datetime, timedelta
import time
from io import BytesIO

# App configuration
st.set_page_config(
    page_title="Crypto Price Action Tracker",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        max-width: 1200px;
    }
    .metric-card {
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
        background-color: #1e2130;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .positive {
        color: #00ff00;
    }
    .negative {
        color: #ff0000;
    }
    </style>
    """, unsafe_allow_html=True)

# App title
st.title("📈 Crypto Price Action Tracker")

# Sidebar
with st.sidebar:
    st.header("Settings")
    date_range = st.selectbox(
        "Date Range",
        ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=2
    )
    interval = st.selectbox(
        "Interval",
        ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"],
        index=5
    )
    
    # Sample file
    st.markdown("### Sample Crypto List")
    sample_data = pd.DataFrame({"Symbol": ["BTC-USD", "ETH-USD", "SOL-USD"]})
    excel_buffer = BytesIO()
    sample_data.to_excel(excel_buffer, index=False)
    st.download_button(
        label="Download Sample File",
        data=excel_buffer.getvalue(),
        file_name="crypto_sample.xlsx",
        mime="application/vnd.ms-excel"
    )

# File uploader
uploaded_file = st.file_uploader("Upload Excel file with crypto symbols", type=["xlsx"])

# Improved data fetching function
def get_crypto_data(symbol, period, interval):
    try:
        # Ensure proper symbol format
        if not symbol.endswith('-USD'):
            symbol += '-USD'
            
        # Get data with proper formatting
        data = yf.download(
            tickers=symbol,
            period=period,
            interval=interval,
            progress=False
        )
        
        if data.empty or len(data) < 14:  # Need at least 14 periods for RSI
            return None
            
        # Ensure we have a DataFrame with the right structure
        if isinstance(data, pd.DataFrame):
            # Calculate indicators with error handling
            try:
                data['RSI'] = RSIIndicator(close=data['Close']).rsi()
                macd = MACD(close=data['Close'])
                data['MACD'] = macd.macd()
                data['Signal'] = macd.macd_signal()
                
                # Calculate momentum
                if len(data) > 1:
                    price_change = (data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100
                    volume_change = (data['Volume'].iloc[-1] - data['Volume'].iloc[-2]) / data['Volume'].iloc[-2] * 100 if data['Volume'].iloc[-2] != 0 else 0
                    momentum_score = (price_change * 0.7) + (volume_change * 0.3)
                else:
                    momentum_score = 0
                
                return data, momentum_score
                
            except Exception as e:
                st.error(f"Indicator calculation error for {symbol}: {str(e)}")
                return None
                
    except Exception as e:
        st.error(f"Data fetch error for {symbol}: {str(e)}")
        return None

# Rest of the functions remain the same (create_price_chart, create_rsi_chart, create_macd_chart)

# Main app logic
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        if 'Symbol' not in df.columns:
            st.error("File must contain 'Symbol' column")
            st.stop()
            
        symbols = df['Symbol'].unique()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        tabs = st.tabs([f"{symbol}" for symbol in symbols])
        results = pd.DataFrame(columns=['Symbol', 'Current Price', '24h Change', 'Momentum Score', 'RSI', 'MACD Signal'])
        
        for i, (symbol, tab) in enumerate(zip(symbols, tabs)):
            status_text.text(f"Fetching {symbol} ({i+1}/{len(symbols)})...")
            progress_bar.progress((i + 1) / len(symbols))
            
            result = get_crypto_data(symbol, date_range, interval)
            
            if result is None:
                with tab:
                    st.error(f"No data for {symbol}")
                continue
                
            data, momentum_score = result
            
            # Display data in tab
            with tab:
                col1, col2, col3 = st.columns(3)
                
                current_price = data['Close'].iloc[-1]
                price_change = (data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100 if len(data) > 1 else 0
                rsi = data['RSI'].iloc[-1]
                macd_signal = "Bullish" if data['MACD'].iloc[-1] > data['Signal'].iloc[-1] else "Bearish"
                
                results.loc[i] = [symbol, current_price, price_change, momentum_score, rsi, macd_signal]
                
                # Display metrics and charts
                # ... (same as before)

        # Display results
        st.dataframe(results.style.apply(
            lambda x: ['color: green' if v >=0 else 'color: red' for v in x],
            subset=['24h Change', 'Momentum Score']
        ))
        
    except Exception as e:
        st.error(f"App error: {str(e)}")

# Refresh button
if st.button("Refresh Data"):
    st.experimental_rerun()
