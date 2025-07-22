import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import pandas_ta as ta

st.set_page_config(page_title="Crypto TA Dashboard", layout="wide")

st.title("Crypto Technical Analysis Dashboard")

# --- DATA LOAD SECTION ---
# Replace this with your real data load!
# Example: Load from a CSV file
# df = pd.read_csv("your_price_data.csv", parse_dates=["date"], index_col="date")

# Demo data: generate a simple price series
import numpy as np
np.random.seed(42)
dates = pd.date_range(end=pd.Timestamp.today(), periods=120)
prices = np.cumsum(np.random.randn(120)) + 100
df = pd.DataFrame({"price": prices}, index=dates)

# --- TECHNICAL INDICATORS ---
df['rsi'] = ta.rsi(df['price'], length=14)
macd = ta.macd(df['price'], fast=12, slow=26, signal=9)
df['macd'] = macd['MACD_12_26_9']
df['macd_signal'] = macd['MACDs_12_26_9']
df['sma_20'] = ta.sma(df['price'], length=20)
df['ema_12'] = ta.ema(df['price'], length=12)
df['ema_26'] = ta.ema(df['price'], length=26)

# --- DISPLAY METRICS ---
current_rsi = df['rsi'].iloc[-1]
last_rsi = df['rsi'].iloc[-2]
current_macd = df['macd'].iloc[-1]
current_macd_signal = df['macd_signal'].iloc[-1]
current_price = df['price'].iloc[-1]
current_sma20 = df['sma_20'].iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Current RSI (14)", f"{current_rsi:.2f}", f"{current_rsi - last_rsi:.2f} vs prev")
col2.metric("MACD Status", 
            "Bullish" if current_macd > current_macd_signal else "Bearish",
            f"{current_macd - current_macd_signal:.4f}")
col3.metric("Price vs SMA20", 
            "Above SMA20" if current_price > current_sma20 else "Below SMA20",
            f"{current_price - current_sma20:.2f}")

# --- RSI CHART ---
st.subheader("RSI (14-day)")
fig_rsi = go.Figure()
fig_rsi.add_trace(go.Scatter(x=df.index, y=df['rsi'], name='RSI', line=dict(color='blue')))
fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought", annotation_position="bottom right")
fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold", annotation_position="top right")
fig_rsi.update_layout(yaxis_title="RSI Value", xaxis_title="Date", hovermode="x unified")
st.plotly_chart(fig_rsi, use_container_width=True)

# --- MACD CHART ---
st.subheader("MACD (12/26/9)")
fig_macd = go.Figure()
fig_macd.add_trace(go.Scatter(x=df.index, y=df['macd'], name='MACD', line=dict(color='blue')))
fig_macd.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], name='Signal Line', line=dict(color='orange')))
fig_macd.update_layout(yaxis_title="MACD Value", xaxis_title="Date", hovermode="x unified")
st.plotly_chart(fig_macd, use_container_width=True)

# --- MOVING AVERAGES CHART ---
st.subheader("Moving Averages")
fig_ma = go.Figure()
fig_ma.add_trace(go.Scatter(x=df.index, y=df['price'], name='Price', line=dict(color='black')))
fig_ma.add_trace(go.Scatter(x=df.index, y=df['sma_20'], name='20-day SMA', line=dict(color='green')))
fig_ma.add_trace(go.Scatter(x=df.index, y=df['ema_12'], name='12-day EMA', line=dict(color='blue')))
fig_ma.add_trace(go.Scatter(x=df.index, y=df['ema_26'], name='26-day EMA', line=dict(color='red')))
fig_ma.update_layout(yaxis_title="Price", xaxis_title="Date", hovermode="x unified")
st.plotly_chart(fig_ma, use_container_width=True)

# --- INTERPRETATION GUIDE ---
with st.expander("How to interpret these indicators"):
    st.markdown("""
**RSI (Relative Strength Index)**
- Above 70: Overbought (potential sell signal)
- Below 30: Oversold (potential buy signal)

**MACD (Moving Average Convergence Divergence)**
- MACD above Signal Line: Bullish signal
- MACD below Signal Line: Bearish signal

**Moving Averages**
- Price above SMA20: Uptrend likely continuing
- Price below SMA20: Downtrend possible
- EMA12 crossing above EMA26: Golden Cross (bullish)
- EMA12 crossing below EMA26: Death Cross (bearish)
""")
