import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD
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
    .metric-card {
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
        background-color: #1e2130;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .positive { color: #00ff00; }
    .negative { color: #ff0000; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 Crypto Price Action Tracker")

# Sidebar
with st.sidebar:
    st.header("Settings")
    date_range = st.selectbox(
        "Date Range",
        ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
        index=2
    )
    interval = st.selectbox(
        "Interval",
        ["1m", "5m", "15m", "30m", "1h", "1d"],
        index=5
    )
    
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

# Fixed data fetching function
def get_crypto_data(symbol, period, interval):
    try:
        if not symbol.upper().endswith('-USD'):
            symbol = f"{symbol.upper()}-USD"
        
        # Get data and ensure proper format
        data = yf.download(
            tickers=symbol,
            period=period,
            interval=interval,
            progress=False
        )
        
        if data.empty or len(data) < 14:
            return None
            
        # Convert to proper Series format for TA library
        close_prices = data['Close'].squeeze()
        volumes = data['Volume'].squeeze()
        
        # Calculate indicators with proper data format
        data['RSI'] = RSIIndicator(close=close_prices).rsi()
        macd = MACD(close=close_prices)
        data['MACD'] = macd.macd()
        data['Signal'] = macd.macd_signal()
        
        # Calculate momentum
        if len(data) > 1:
            price_change = (close_prices.iloc[-1] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100
            volume_change = (volumes.iloc[-1] - volumes.iloc[-2]) / volumes.iloc[-2] * 100 if volumes.iloc[-2] != 0 else 0
            momentum_score = (price_change * 0.7) + (volume_change * 0.3)
        else:
            momentum_score = 0
            
        return data, momentum_score
        
    except Exception as e:
        st.error(f"Error processing {symbol}: {str(e)}")
        return None

# Chart functions (unchanged)
def create_price_chart(data, symbol):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Price', line=dict(color='#00ff00')))
    fig.update_layout(title=f"{symbol} Price", template="plotly_dark")
    return fig

def create_rsi_chart(data, symbol):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name='RSI', line=dict(color='#ff9900')))
    fig.add_hline(y=70, line_dash="dot", line_color="red")
    fig.add_hline(y=30, line_dash="dot", line_color="green")
    fig.update_layout(title=f"{symbol} RSI", template="plotly_dark")
    return fig

def create_macd_chart(data, symbol):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD', line=dict(color='#00ff00')))
    fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], name='Signal', line=dict(color='#ff0000')))
    fig.update_layout(title=f"{symbol} MACD", template="plotly_dark")
    return fig

# Main app
uploaded_file = st.file_uploader("Upload Excel file with crypto symbols", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if 'Symbol' not in df.columns:
            st.error("File must contain 'Symbol' column")
            st.stop()
            
        symbols = df['Symbol'].unique()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        tabs = st.tabs([f"{symbol}" for symbol in symbols])
        results = []
        
        for i, (symbol, tab) in enumerate(zip(symbols, tabs)):
            status_text.text(f"Processing {symbol} ({i+1}/{len(symbols)})...")
            progress_bar.progress((i + 1) / len(symbols))
            
            data = get_crypto_data(symbol, date_range, interval)
            
            with tab:
                if not data:
                    st.error(f"No data for {symbol}")
                    continue
                    
                df_data, momentum_score = data
                current_price = df_data['Close'].iloc[-1]
                price_change = (df_data['Close'].iloc[-1] - df_data['Close'].iloc[-2]) / df_data['Close'].iloc[-2] * 100
                rsi = df_data['RSI'].iloc[-1]
                macd_signal = "Bullish" if df_data['MACD'].iloc[-1] > df_data['Signal'].iloc[-1] else "Bearish"
                
                results.append({
                    'Symbol': symbol,
                    'Price': current_price,
                    '24h Change': price_change,
                    'Momentum': momentum_score,
                    'RSI': rsi,
                    'MACD': macd_signal
                })
                
                # Display metrics
                cols = st.columns(3)
                with cols[0]:
                    st.markdown(f"<div class='metric-card'>Price<br>${current_price:,.2f}</div>", unsafe_allow_html=True)
                with cols[1]:
                    change_class = "positive" if price_change >= 0 else "negative"
                    st.markdown(f"<div class='metric-card'>24h Change<br><span class='{change_class}'>{price_change:.2f}%</span></div>", unsafe_allow_html=True)
                with cols[2]:
                    mom_class = "positive" if momentum_score >= 0 else "negative"
                    st.markdown(f"<div class='metric-card'>Momentum<br><span class='{mom_class}'>{momentum_score:.2f}</span></div>", unsafe_allow_html=True)
                
                # Display charts
                st.plotly_chart(create_price_chart(df_data, symbol), use_container_width=True)
                st.plotly_chart(create_rsi_chart(df_data, symbol), use_container_width=True)
                st.plotly_chart(create_macd_chart(df_data, symbol), use_container_width=True)
        
        # Show summary
        if results:
            results_df = pd.DataFrame(results)
            st.dataframe(results_df.style.apply(
                lambda x: ['color: green' if v >=0 else 'color: red' for v in x],
                subset=['24h Change', 'Momentum']
            ))
            
    except Exception as e:
        st.error(f"Application error: {str(e)}")

if st.button("Refresh Data"):
    st.experimental_rerun()
