import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.momentum import RSIIndicator
from ta.trend import MACD
import time

# CoinMarketCap API configuration
API_KEY = "f356e3d4-dd08-437d-bcc9-edbb0fc65b22"
BASE_URL = "https://pro-api.coinmarketcap.com/v1/"

# Configure Streamlit app
st.set_page_config(page_title="Crypto Price Tracker", layout="wide")
st.title("📊 Cryptocurrency Price Action & Momentum Tracker")

# Sidebar for user inputs
with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("Upload Excel file with crypto symbols", type=["xlsx"])
    days = st.slider("Number of days for analysis", min_value=1, max_value=90, value=30)
    max_coins = st.slider("Max coins to analyze", min_value=1, max_value=50, value=20)
    update_button = st.button("🔄 Update Data")

# Function to fetch crypto data with rate limiting
def get_crypto_data(symbols, days):
    crypto_data = []
    invalid_symbols = []
    
    for i, symbol in enumerate(symbols[:max_coins]):  # Respect max_coins limit
        try:
            # Rate limiting
            if i > 0 and i % 5 == 0:
                time.sleep(1)  # Pause to avoid API rate limits
            
            # Get latest quotes
            quote_url = f"{BASE_URL}cryptocurrency/quotes/latest"
            quote_params = {'symbol': symbol, 'convert': 'USD'}
            quote_headers = {'X-CMC_PRO_API_KEY': API_KEY}
            
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
            
            historical_response = requests.get(historical_url, headers=quote_headers, params=historical_params)
            historical_data = historical_response.json()
            
            if 'data' not in quote_data or 'data' not in historical_data:
                invalid_symbols.append(symbol)
                continue
                
            # Process data
            current_data = quote_data['data'][symbol][0]
            historical_prices = [item['quote']['USD']['price'] for item in historical_data['data']]
            historical_dates = [item['timestamp'] for item in historical_data['data']]
            
            # Calculate indicators
            rsi, macd, macd_signal, momentum_score = None, None, None, None
            
            if len(historical_prices) >= 14:
                # RSI Calculation
                rsi_indicator = RSIIndicator(pd.Series(historical_prices), window=14)
                rsi = rsi_indicator.rsi().iloc[-1]
                
                # MACD Calculation
                macd_indicator = MACD(pd.Series(historical_prices))
                macd = macd_indicator.macd().iloc[-1]
                macd_signal = macd_indicator.macd_signal().iloc[-1]
                
                # Momentum Score (weighted average)
                changes = [
                    ((historical_prices[-1] - historical_prices[-2]) / historical_prices[-2]) * 100 if len(historical_prices) >= 2 else 0,
                    ((historical_prices[-1] - historical_prices[-7]) / historical_prices[-7]) * 100 if len(historical_prices) >= 7 else 0,
                    ((historical_prices[-1] - historical_prices[-min(30, len(historical_prices))]) / 
                     historical_prices[-min(30, len(historical_prices))]) * 100
                ]
                momentum_score = sum(w * c for w, c in zip([0.5, 0.3, 0.2], changes))
            
            crypto_data.append({
                'Symbol': symbol,
                'Name': current_data.get('name', symbol),
                'Price (USD)': current_data['quote']['USD']['price'],
                'Market Cap': current_data['quote']['USD'].get('market_cap'),
                '24h Change (%)': current_data['quote']['USD'].get('percent_change_24h', 0),
                '7d Change (%)': current_data['quote']['USD'].get('percent_change_7d', 0),
                'RSI (14)': rsi,
                'MACD': macd,
                'MACD Signal': macd_signal,
                'Momentum Score': momentum_score,
                'Historical Prices': historical_prices,
                'Historical Dates': historical_dates
            })
            
        except Exception as e:
            invalid_symbols.append(symbol)
            continue
    
    if invalid_symbols:
        st.warning(f"⚠️ Could not fetch data for: {', '.join(invalid_symbols)}")
    return crypto_data

# Main app logic
if uploaded_file is not None:
    try:
        # Read and validate Excel file
        df = pd.read_excel(uploaded_file)
        
        # Flexible column detection
        symbol_col = None
        for col in df.columns:
            if 'symbol' in str(col).lower():
                symbol_col = col
                break
                
        if symbol_col:
            symbols = df[symbol_col].astype(str).str.strip().str.upper().unique().tolist()
        else:
            symbols = df.iloc[:, 0].astype(str).str.strip().str.upper().unique().tolist()
        
        # Filter valid symbols
        symbols = [s for s in symbols if s.isalpha() and len(s) <= 10]
        
        if not symbols:
            st.error("❌ No valid cryptocurrency symbols found in the file.")
        else:
            st.success(f"✅ Found {len(symbols)} valid symbols")
            st.write(f"Analyzing first {min(max_coins, len(symbols))} coins...")
            
            if update_button or not st.session_state.get('crypto_data'):
                with st.spinner("🔍 Fetching crypto data (this may take a minute)..."):
                    crypto_data = get_crypto_data(symbols, days)
                    st.session_state['crypto_data'] = crypto_data
            else:
                crypto_data = st.session_state.get('crypto_data', [])
            
            if crypto_data:
                # Display summary table
                st.subheader("📋 Cryptocurrency Metrics")
                summary_df = pd.DataFrame([{
                    'Symbol': x['Symbol'],
                    'Price': f"${x['Price (USD)']:,.2f}",
                    '24h %': f"{x['24h Change (%)']:.2f}%",
                    '7d %': f"{x['7d Change (%)']:.2f}%",
                    'RSI': f"{x['RSI (14)']:.1f}" if x['RSI (14)'] else "-",
                    'MACD': f"{x['MACD']:.3f}" if x['MACD'] else "-",
                    'Momentum': f"{x['Momentum Score']:.1f}" if x['Momentum Score'] else "-"
                } for x in crypto_data])
                
                st.dataframe(summary_df.style.applymap(
                    lambda x: 'color: green' if isinstance(x, str) and '-' not in x and float(x.replace('%','').replace('$','').replace(',','')) > 0 
                    else 'color: red' if isinstance(x, str) and '-' not in x and float(x.replace('%','').replace('$','').replace(',','')) < 0 
                    else '', subset=['24h %', '7d %', 'Momentum']),
                    use_container_width=True, height=(len(crypto_data) + 1) * 35 + 3)
                
                # Display detailed charts
                for crypto in crypto_data:
                    st.divider()
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.subheader(f"{crypto['Name']} ({crypto['Symbol']})")
                        
                        # Price metrics
                        delta_color = "inverse" if crypto['24h Change (%)'] < 0 else "normal"
                        st.metric("Current Price", 
                                 f"${crypto['Price (USD)']:,.2f}", 
                                 f"{crypto['24h Change (%)']:.2f}%",
                                 delta_color=delta_color)
                        
                        # Indicator cards
                        cols = st.columns(2)
                        with cols[0]:
                            st.metric("7d Change", f"{crypto['7d Change (%)']:.2f}%")
                        with cols[1]:
                            st.metric("Momentum", 
                                     f"{crypto['Momentum Score']:.1f}" if crypto['Momentum Score'] else "N/A",
                                     help="Weighted score of 1d/7d/30d performance")
                        
                        # RSI indicator
                        if crypto['RSI (14)']:
                            rsi_status = ""
                            if crypto['RSI (14)'] > 70:
                                rsi_status = "🔴 Overbought"
                            elif crypto['RSI (14)'] < 30:
                                rsi_status = "🟢 Oversold"
                            st.metric("RSI (14)", f"{crypto['RSI (14)']:.1f}", rsi_status)
                        
                        # MACD indicator
                        if crypto['MACD'] and crypto['MACD Signal']:
                            macd_status = "🟢 Bullish" if crypto['MACD'] > crypto['MACD Signal'] else "🔴 Bearish"
                            st.metric("MACD", 
                                     f"{crypto['MACD']:.3f}", 
                                     f"Signal: {crypto['MACD Signal']:.3f} ({macd_status})")
                    
                    with col2:
                        # Price + RSI chart
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                           vertical_spacing=0.05, row_heights=[0.7, 0.3])
                        
                        # Price trace
                        fig.add_trace(
                            go.Scatter(
                                x=crypto['Historical Dates'],
                                y=crypto['Historical Prices'],
                                name='Price',
                                line=dict(color='#636EFA'),
                                hovertemplate="%{y:$,.2f}<extra></extra>"
                            ),
                            row=1, col=1
                        )
                        
                        # RSI trace
                        if crypto['RSI (14)']:
                            rsi_values = RSIIndicator(pd.Series(crypto['Historical Prices']), window=14).rsi()
                            fig.add_trace(
                                go.Scatter(
                                    x=crypto['Historical Dates'],
                                    y=rsi_values,
                                    name='RSI (14)',
                                    line=dict(color='#FFA15A')
                                ),
                                row=2, col=1
                            )
                            fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
                            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
                        
                        fig.update_layout(
                            height=500,
                            title=f"{crypto['Symbol']} Price and RSI",
                            hovermode="x unified",
                            showlegend=False,
                            margin=dict(t=50, b=50)
                        
                        fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
                        if crypto['RSI (14)']:
                            fig.update_yaxes(title_text="RSI", row=2, col=1)
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # MACD chart
                        if crypto['MACD']:
                            macd_values = MACD(pd.Series(crypto['Historical Prices'])).macd()
                            signal_values = MACD(pd.Series(crypto['Historical Prices'])).macd_signal()
                            
                            macd_fig = go.Figure()
                            macd_fig.add_trace(go.Scatter(
                                x=crypto['Historical Dates'],
                                y=macd_values,
                                name='MACD',
                                line=dict(color='blue')
                            ))
                            macd_fig.add_trace(go.Scatter(
                                x=crypto['Historical Dates'],
                                y=signal_values,
                                name='Signal',
                                line=dict(color='orange')
                            ))
                            macd_fig.add_hline(y=0, line_dash="dot", line_color="gray")
                            macd_fig.update_layout(
                                height=300,
                                title="MACD Indicator",
                                hovermode="x unified",
                                margin=dict(t=50, b=50)
                            )
                            st.plotly_chart(macd_fig, use_container_width=True)
            
            else:
                st.warning("No valid cryptocurrency data could be fetched.")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("ℹ️ Please upload an Excel file with cryptocurrency symbols to begin analysis.")

# Add some styling
st.markdown("""
<style>
    .stMetric {
        border-radius: 8px;
        padding: 12px;
        background-color: #f0f2f6;
    }
    .stDataFrame {
        font-size: 0.9em;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }
</style>
""", unsafe_allow_html=True)
