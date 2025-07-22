import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO
from ta.momentum import RSIIndicator
from ta.trend import MACD

# CoinMarketCap API configuration
API_KEY = "f356e3d4-dd08-437d-bcc9-edbb0fc65b22"
BASE_URL = "https://pro-api.coinmarketcap.com/v1/"

# Configure Streamlit app
st.set_page_config(page_title="Crypto Price Tracker", layout="wide")
st.title("Cryptocurrency Price Action & Momentum Tracker")

# Sidebar for user inputs
with st.sidebar:
    st.header("Configuration")
    uploaded_file = st.file_uploader("Upload Excel file with crypto symbols", type=["xlsx"])
    days = st.slider("Number of days for analysis", min_value=1, max_value=90, value=30)
    update_button = st.button("Update Data")

# Function to fetch crypto data
def get_crypto_data(symbols, days):
    crypto_data = []
    
    for symbol in symbols:
        try:
            # Get latest quotes
            quote_url = f"{BASE_URL}cryptocurrency/quotes/latest"
            quote_params = {
                'symbol': symbol,
                'convert': 'USD'
            }
            quote_headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': API_KEY
            }
            
            quote_response = requests.get(quote_url, headers=quote_headers, params=quote_params)
            quote_data = quote_response.json()
            
            # Get historical data
            historical_url = f"{BASE_URL}cryptocurrency/quotes/historical"
            historical_params = {
                'symbol': symbol,
                'convert': 'USD',
                'count': days,
                'interval': 'daily'
            }
            historical_headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': API_KEY
            }
            
            historical_response = requests.get(historical_url, headers=historical_headers, params=historical_params)
            historical_data = historical_response.json()
            
            if 'data' in quote_data and 'data' in historical_data:
                # Process current data
                current_data = quote_data['data'][symbol][0]
                
                # Process historical data
                historical_prices = [item['quote']['USD']['price'] for item in historical_data['data']]
                historical_dates = [item['timestamp'] for item in historical_data['data']]
                
                # Calculate metrics
                if len(historical_prices) >= 14:  # Minimum for RSI
                    rsi_indicator = RSIIndicator(pd.Series(historical_prices), window=14)
                    rsi = rsi_indicator.rsi().iloc[-1]
                    
                    macd_indicator = MACD(pd.Series(historical_prices))
                    macd = macd_indicator.macd().iloc[-1]
                    macd_signal = macd_indicator.macd_signal().iloc[-1]
                    
                    # Momentum score (custom calculation)
                    price_change_1d = ((current_data['quote']['USD']['price'] - historical_prices[-1]) / historical_prices[-1]) * 100
                    price_change_7d = ((current_data['quote']['USD']['price'] - historical_prices[-7]) / historical_prices[-7]) * 100 if len(historical_prices) >= 7 else 0
                    price_change_30d = ((current_data['quote']['USD']['price'] - historical_prices[-min(30, len(historical_prices))]) / historical_prices[-min(30, len(historical_prices))]) * 100
                    
                    momentum_score = 0.4 * price_change_1d + 0.3 * price_change_7d + 0.3 * price_change_30d
                else:
                    rsi = None
                    macd = None
                    macd_signal = None
                    momentum_score = None
                
                crypto_data.append({
                    'Symbol': symbol,
                    'Name': current_data['name'],
                    'Price (USD)': current_data['quote']['USD']['price'],
                    'Market Cap': current_data['quote']['USD']['market_cap'],
                    '24h Change (%)': current_data['quote']['USD']['percent_change_24h'],
                    '7d Change (%)': current_data['quote']['USD']['percent_change_7d'],
                    'RSI (14)': rsi,
                    'MACD': macd,
                    'MACD Signal': macd_signal,
                    'Momentum Score': momentum_score,
                    'Historical Prices': historical_prices,
                    'Historical Dates': historical_dates
                })
                
        except Exception as e:
            st.warning(f"Error fetching data for {symbol}: {str(e)}")
            continue
    
    return crypto_data

# Main app logic
if uploaded_file is not None:
    try:
        # Read symbols from Excel file
        df = pd.read_excel(uploaded_file)
        symbols = df.iloc[:, 0].astype(str).unique().tolist()
        
        if update_button or not st.session_state.get('crypto_data'):
            with st.spinner("Fetching crypto data..."):
                crypto_data = get_crypto_data(symbols, days)
                st.session_state['crypto_data'] = crypto_data
        else:
            crypto_data = st.session_state.get('crypto_data', [])
        
        if crypto_data:
            # Display summary table
            st.subheader("Cryptocurrency Metrics Summary")
            summary_data = []
            
            for crypto in crypto_data:
                summary_data.append({
                    'Symbol': crypto['Symbol'],
                    'Price (USD)': f"${crypto['Price (USD)']:,.2f}",
                    '24h Change (%)': f"{crypto['24h Change (%)']:.2f}%",
                    '7d Change (%)': f"{crypto['7d Change (%)']:.2f}%",
                    'RSI (14)': f"{crypto['RSI (14)']:.2f}" if crypto['RSI (14)'] else "N/A",
                    'MACD': f"{crypto['MACD']:.4f}" if crypto['MACD'] else "N/A",
                    'MACD Signal': f"{crypto['MACD Signal']:.4f}" if crypto['MACD Signal'] else "N/A",
                    'Momentum Score': f"{crypto['Momentum Score']:.2f}" if crypto['Momentum Score'] else "N/A"
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
            # Display charts for each cryptocurrency
            for crypto in crypto_data:
                st.divider()
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.subheader(f"{crypto['Name']} ({crypto['Symbol']})")
                    st.metric("Current Price", f"${crypto['Price (USD)']:,.2f}")
                    
                    # Display key metrics
                    st.write(f"**24h Change:** {crypto['24h Change (%)']:.2f}%")
                    st.write(f"**7d Change:** {crypto['7d Change (%)']:.2f}%")
                    
                    if crypto['RSI (14)']:
                        st.write(f"**RSI (14):** {crypto['RSI (14)']:.2f}")
                        if crypto['RSI (14)'] > 70:
                            st.warning("Overbought (RSI > 70)")
                        elif crypto['RSI (14)'] < 30:
                            st.info("Oversold (RSI < 30)")
                    
                    if crypto['MACD'] and crypto['MACD Signal']:
                        st.write(f"**MACD:** {crypto['MACD']:.4f}")
                        st.write(f"**MACD Signal:** {crypto['MACD Signal']:.4f}")
                        if crypto['MACD'] > crypto['MACD Signal']:
                            st.success("Bullish (MACD > Signal)")
                        else:
                            st.error("Bearish (MACD < Signal)")
                    
                    if crypto['Momentum Score']:
                        st.write(f"**Momentum Score:** {crypto['Momentum Score']:.2f}")
                
                with col2:
                    # Create price chart with RSI
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                     vertical_spacing=0.05, 
                                     row_heights=[0.7, 0.3])
                    
                    # Price trace
                    fig.add_trace(
                        go.Scatter(
                            x=crypto['Historical Dates'],
                            y=crypto['Historical Prices'],
                            name='Price',
                            line=dict(color='#1f77b4')
                        ),
                        row=1, col=1
                    )
                    
                    # RSI trace if available
                    if crypto['RSI (14)']:
                        rsi_values = RSIIndicator(pd.Series(crypto['Historical Prices']), window=14).rsi()
                        fig.add_trace(
                            go.Scatter(
                                x=crypto['Historical Dates'],
                                y=rsi_values,
                                name='RSI (14)',
                                line=dict(color='#ff7f0e')
                            ),
                            row=2, col=1
                        )
                        # Add RSI reference lines
                        fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
                    
                    # Update layout
                    fig.update_layout(
                        height=600,
                        title_text=f"{crypto['Symbol']} Price and RSI",
                        hovermode="x unified"
                    )
                    
                    # Update y-axes titles
                    fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
                    if crypto['RSI (14)']:
                        fig.update_yaxes(title_text="RSI", row=2, col=1)
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # MACD chart if available
                    if crypto['MACD'] and crypto['MACD Signal']:
                        macd_values = MACD(pd.Series(crypto['Historical Prices'])).macd()
                        signal_values = MACD(pd.Series(crypto['Historical Prices'])).macd_signal()
                        
                        macd_fig = go.Figure()
                        macd_fig.add_trace(
                            go.Scatter(
                                x=crypto['Historical Dates'],
                                y=macd_values,
                                name='MACD',
                                line=dict(color='blue')
                            )
                        )
                        macd_fig.add_trace(
                            go.Scatter(
                                x=crypto['Historical Dates'],
                                y=signal_values,
                                name='Signal',
                                line=dict(color='orange')
                            )
                        )
                        macd_fig.add_hline(y=0, line_dash="dot", line_color="gray")
                        
                        macd_fig.update_layout(
                            height=300,
                            title_text="MACD Indicator",
                            hovermode="x unified"
                        )
                        
                        st.plotly_chart(macd_fig, use_container_width=True)
        
        else:
            st.warning("No valid cryptocurrency data found. Please check your symbols.")
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
else:
    st.info("Please upload an Excel file containing cryptocurrency symbols to get started.")

# Add some styling
st.markdown("""
<style>
    .stMetric {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stDataFrame {
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)
