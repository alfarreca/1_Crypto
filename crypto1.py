import pandas_ta as ta

# Assume df['price'] already exists and the index is datetime
# Calculate indicators with pandas-ta
df['rsi'] = ta.rsi(df['price'], length=14)
macd = ta.macd(df['price'], fast=12, slow=26, signal=9)
df['macd'] = macd['MACD_12_26_9']
df['macd_signal'] = macd['MACDs_12_26_9']
df['sma_20'] = ta.sma(df['price'], length=20)
df['ema_12'] = ta.ema(df['price'], length=12)
df['ema_26'] = ta.ema(df['price'], length=26)

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
))
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
