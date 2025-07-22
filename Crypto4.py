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

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        max-width: 1200px;
    }
    .stDownloadButton, .stFileUploader {
        width: 100%;
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
    .header {
        color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

# App title
st.title("📈 Crypto Price Action Tracker")
st.markdown("Track cryptocurrency prices, momentum scores, and technical indicators (RSI & MACD)")

# Sidebar for user inputs
with st.sidebar:
    st.header("Settings")
    
    # Date range selection
    date_range = st.selectbox(
        "Date Range",
        ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=2
    )
    
    # Interval selection
    interval = st.selectbox(
        "Interval",
        ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"],
        index=5
    )
    
    # Sample file download
    st.markdown("### Sample Crypto List")
    sample_data = pd.DataFrame({"Symbol": ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "DOT-USD"]})
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

# Function to calculate momentum score
def calculate_momentum_score(data):
    if len(data) < 2:
        return 0
    
    # Simple momentum calculation (can be enhanced)
    price_change = (data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100
    volume_change = (data['Volume'].iloc[-1] - data['Volume'].iloc[-2]) / data['Volume'].iloc[-2] * 100 if data['Volume'].iloc[-2] != 0 else 0
    
    # Weighted score
    momentum_score = (price_change * 0.7) + (volume_change * 0.3)
    return momentum_score

# Function to fetch data and calculate indicators
def get_crypto_data(symbol, period, interval):
    try:
        # Add '-USD' if not present (assuming USD pairs)
        if not symbol.endswith('-USD'):
            symbol += '-USD'
            
        # Get data from Yahoo Finance
        data = yf.download(
            tickers=symbol,
            period=period,
            interval=interval,
            progress=False
        )
        
        if data.empty:
            return None
            
        # Calculate RSI
        rsi_indicator = RSIIndicator(close=data['Close'], window=14)
        data['RSI'] = rsi_indicator.rsi()
        
        # Calculate MACD
        macd_indicator = MACD(close=data['Close'])
        data['MACD'] = macd_indicator.macd()
        data['Signal'] = macd_indicator.macd_signal()
        
        # Calculate Momentum Score
        momentum_score = calculate_momentum_score(data)
        
        return data, momentum_score
        
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

# Function to create price chart with indicators
def create_price_chart(data, symbol):
    fig = go.Figure()
    
    # Price line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Close'],
        name='Price',
        line=dict(color='#00ff00', width=2)
    ))
    
    # Layout
    fig.update_layout(
        title=f"{symbol} Price Chart",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# Function to create RSI chart
def create_rsi_chart(data, symbol):
    fig = go.Figure()
    
    # RSI line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['RSI'],
        name='RSI',
        line=dict(color='#ff9900', width=2)
    ))
    
    # Overbought line
    fig.add_hline(y=70, line_dash="dot", line_color="red", annotation_text="Overbought (70)")
    
    # Oversold line
    fig.add_hline(y=30, line_dash="dot", line_color="green", annotation_text="Oversold (30)")
    
    # Layout
    fig.update_layout(
        title=f"{symbol} RSI (14)",
        xaxis_title="Date",
        yaxis_title="RSI Value",
        template="plotly_dark",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# Function to create MACD chart
def create_macd_chart(data, symbol):
    fig = go.Figure()
    
    # MACD line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['MACD'],
        name='MACD',
        line=dict(color='#00ff00', width=2)
    ))
    
    # Signal line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Signal'],
        name='Signal',
        line=dict(color='#ff0000', width=2)
    ))
    
    # Layout
    fig.update_layout(
        title=f"{symbol} MACD",
        xaxis_title="Date",
        yaxis_title="MACD Value",
        template="plotly_dark",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# Main app logic
if uploaded_file is not None:
    try:
        # Read the uploaded file
        df = pd.read_excel(uploaded_file)
        
        # Check if 'Symbol' column exists
        if 'Symbol' not in df.columns:
            st.error("The uploaded file must contain a 'Symbol' column with cryptocurrency symbols.")
            st.stop()
            
        # Get unique symbols
        symbols = df['Symbol'].unique()
        
        # Display progress and status
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create tabs for each crypto
        tabs = st.tabs([f"{symbol}" for symbol in symbols])
        
        # Initialize results dataframe
        results = pd.DataFrame(columns=['Symbol', 'Current Price', '24h Change', 'Momentum Score', 'RSI', 'MACD Signal'])
        
        # Process each symbol
        for i, (symbol, tab) in enumerate(zip(symbols, tabs)):
            status_text.text(f"Fetching data for {symbol} ({i+1}/{len(symbols)})...")
            progress_bar.progress((i + 1) / len(symbols))
            
            # Get data
            result = get_crypto_data(symbol, date_range, interval)
            
            if result is None:
                with tab:
                    st.error(f"Could not fetch data for {symbol}")
                continue
                
            data, momentum_score = result
            
            # Calculate metrics
            current_price = data['Close'].iloc[-1]
            prev_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
            price_change = (current_price - prev_price) / prev_price * 100
            rsi = data['RSI'].iloc[-1]
            macd_signal = "Bullish" if data['MACD'].iloc[-1] > data['Signal'].iloc[-1] else "Bearish"
            
            # Add to results
            results.loc[i] = [
                symbol,
                current_price,
                price_change,
                momentum_score,
                rsi,
                macd_signal
            ]
            
            # Display in tab
            with tab:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"<div class='metric-card'><h3 class='header'>Price</h3><h2>${current_price:,.2f}</h2></div>", unsafe_allow_html=True)
                    
                with col2:
                    change_class = "positive" if price_change >= 0 else "negative"
                    st.markdown(f"<div class='metric-card'><h3 class='header'>24h Change</h3><h2 class='{change_class}'>{price_change:.2f}%</h2></div>", unsafe_allow_html=True)
                    
                with col3:
                    mom_class = "positive" if momentum_score >= 0 else "negative"
                    st.markdown(f"<div class='metric-card'><h3 class='header'>Momentum Score</h3><h2 class='{mom_class}'>{momentum_score:.2f}</h2></div>", unsafe_allow_html=True)
                
                # Charts
                st.plotly_chart(create_price_chart(data, symbol), use_container_width=True)
                
                col4, col5 = st.columns(2)
                with col4:
                    st.plotly_chart(create_rsi_chart(data, symbol), use_container_width=True)
                
                with col5:
                    st.plotly_chart(create_macd_chart(data, symbol), use_container_width=True)
                
                # Raw data
                with st.expander("Show Raw Data"):
                    st.dataframe(data.tail(10))
        
        # Display summary table
        st.header("Cryptocurrency Summary")
        
        # Style the dataframe
        def color_positive_negative(val):
            color = 'green' if val >= 0 else 'red'
            return f'color: {color}'
        
        styled_results = results.style.applymap(color_positive_negative, subset=['24h Change', 'Momentum Score'])
        st.dataframe(styled_results)
        
        # Download results
        excel_buffer = BytesIO()
        results.to_excel(excel_buffer, index=False)
        st.download_button(
            label="Download Results as Excel",
            data=excel_buffer.getvalue(),
            file_name="crypto_results.xlsx",
            mime="application/vnd.ms-excel"
        )
        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
else:
    st.info("Please upload an Excel file with cryptocurrency symbols to get started.")

# Add a refresh button
if st.button("Refresh Data"):
    st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("Built with Streamlit • Data from Yahoo Finance")
