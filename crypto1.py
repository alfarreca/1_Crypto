import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import time
import io
import talib  # Technical Analysis Library

# ... [Keep all your existing code until the main content section] ...

# Main content with new Momentum Analysis tab
if not st.session_state.watchlist:
    st.warning("Your watchlist is empty. Add some cryptocurrencies from the sidebar.")
else:
    # Create tabs
    tab1, tab2 = st.tabs(["Price Tracking", "Momentum Analysis"])
    
    with tab1:
        # ... [Keep all your existing price tracking code here] ...
    
    with tab2:
        st.header("📊 Momentum Analysis")
        
        # Get market data for momentum analysis
        market_data = get_market_data(st.session_state.watchlist, st.session_state.currency)
        
        if market_data:
            # Coin selection
            selected_coin = st.selectbox(
                "Select Coin for Analysis",
                [coin['id'] for coin in market_data],
                format_func=lambda x: next(c['name'] for c in market_data if c['id'] == x),
                key="momentum_coin"
            )
            
            # Time period selection
            time_period = st.selectbox(
                "Analysis Period",
                ["7 Days", "14 Days", "30 Days"],
                index=0,
                key="momentum_period"
            )
            
            days_map = {"7 Days": 7, "14 Days": 14, "30 Days": 30}
            days = days_map[time_period]
            
            # Get historical data
            historical_data = get_historical_data(selected_coin, st.session_state.currency, days)
            
            if historical_data and 'prices' in historical_data:
                # Process data
                df = pd.DataFrame(historical_data['prices'], columns=['timestamp', 'price'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('date', inplace=True)
                df = df.resample('1D').mean().ffill()  # Daily resampling
                
                # Calculate technical indicators
                df['rsi'] = talib.RSI(df['price'], timeperiod=14)
                macd, macdsignal, macdhist = talib.MACD(df['price'])
                df['macd'] = macd
                df['macd_signal'] = macdsignal
                df['sma_20'] = talib.SMA(df['price'], timeperiod=20)
                df['ema_12'] = talib.EMA(df['price'], timeperiod=12)
                df['ema_26'] = talib.EMA(df['price'], timeperiod=26)
                
                # Display metrics
                current_rsi = df['rsi'].iloc[-1]
                last_rsi = df['rsi'].iloc[-2]
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Current RSI (14)", f"{current_rsi:.2f}", 
                           f"{(current_rsi - last_rsi):.2f} from yesterday")
                col2.metric("MACD Status", 
                           "Bullish" if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] else "Bearish",
                           f"{df['macd'].iloc[-1] - df['macd_signal'].iloc[-1]:.4f}")
                col3.metric("Price Trend", 
                           "Above SMA20" if df['price'].iloc[-1] > df['sma_20'].iloc[-1] else "Below SMA20",
                           f"{df['price'].iloc[-1] - df['sma_20'].iloc[-1]:.2f}")
                
                # RSI Chart
                st.subheader("Relative Strength Index (14-day)")
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(
                    x=df.index, y=df['rsi'],
                    name='RSI',
                    line=dict(color='blue', width=2)
                )
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", 
                                 annotation_text="Overbought", annotation_position="bottom right")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", 
                                 annotation_text="Oversold", annotation_position="top right")
                fig_rsi.update_layout(
                    yaxis_title="RSI Value",
                    xaxis_title="Date",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_rsi, use_container_width=True)
                
                # MACD Chart
                st.subheader("MACD (12/26/9)")
                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(
                    x=df.index, y=df['macd'],
                    name='MACD',
                    line=dict(color='blue', width=2)
                ))
                fig_macd.add_trace(go.Scatter(
                    x=df.index, y=df['macd_signal'],
                    name='Signal Line',
                    line=dict(color='orange', width=2)
                ))
                fig_macd.update_layout(
                    yaxis_title="MACD Value",
                    xaxis_title="Date",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_macd, use_container_width=True)
                
                # Moving Averages Chart
                st.subheader("Moving Averages")
                fig_ma = go.Figure()
                fig_ma.add_trace(go.Scatter(
                    x=df.index, y=df['price'],
                    name='Price',
                    line=dict(color='black', width=2)
                ))
                fig_ma.add_trace(go.Scatter(
                    x=df.index, y=df['sma_20'],
                    name='20-day SMA',
                    line=dict(color='green', width=1)
                ))
                fig_ma.add_trace(go.Scatter(
                    x=df.index, y=df['ema_12'],
                    name='12-day EMA',
                    line=dict(color='blue', width=1)
                ))
                fig_ma.add_trace(go.Scatter(
                    x=df.index, y=df['ema_26'],
                    name='26-day EMA',
                    line=dict(color='red', width=1)
                ))
                fig_ma.update_layout(
                    yaxis_title=f"Price ({st.session_state.currency.upper()})",
                    xaxis_title="Date",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_ma, use_container_width=True)
                
                # Interpretation guide
                with st.expander("How to interpret these indicators"):
                    st.markdown("""
                    **RSI (Relative Strength Index)**
                    - Above 70: Overbought (potential sell signal)
                    - Below 30: Oversold (potential buy signal)
                    
                    **MACD (Moving Average Convergence Divergence)**
                    - When MACD crosses above Signal Line: Bullish signal
                    - When MACD crosses below Signal Line: Bearish signal
                    
                    **Moving Averages**
                    - Price above SMA20: Uptrend likely continuing
                    - Price below SMA20: Downtrend possible
                    - EMA12 crossing above EMA26: Golden Cross (bullish)
                    - EMA12 crossing below EMA26: Death Cross (bearish)
                    """)
            else:
                st.warning("Could not load historical data for momentum analysis")
        else:
            st.warning("Could not load market data for analysis")

# ... [Keep your existing footer code] ...
