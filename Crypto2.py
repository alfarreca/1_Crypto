import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import time
import io

# App configuration
st.set_page_config(
    page_title="Crypto Price Tracker",
    page_icon="₿",
    layout="wide"
)

# API configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
DEFAULT_COINS = ["bitcoin", "ethereum", "solana", "cardano", "ripple"]
DEFAULT_CURRENCY = "usd"

# Cache data to prevent excessive API calls
@st.cache_data(ttl=60)
def get_coin_list():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/list")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching coin list: {e}")
        return []

@st.cache_data(ttl=60)
def get_market_data(coin_ids, currency):
    try:
        ids = ",".join(coin_ids)
        response = requests.get(
            f"{COINGECKO_API_URL}/coins/markets",
            params={
                "vs_currency": currency,
                "ids": ids,
                "order": "market_cap_desc",
                "price_change_percentage": "1h,24h,7d"
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching market data: {e}")
        return []

@st.cache_data(ttl=300)
def get_historical_data(coin_id, currency, days):
    try:
        response = requests.get(
            f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart",
            params={
                "vs_currency": currency,
                "days": days
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching historical data: {e}")
        return None

@st.cache_data(ttl=3600)
def get_top_gainers(currency="usd", limit=20):
    try:
        response = requests.get(
            f"{COINGECKO_API_URL}/coins/markets",
            params={
                "vs_currency": currency,
                "order": "price_change_percentage_24h_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h"
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching top gainers: {e}")
        return []

def create_template_file():
    top_gainers = get_top_gainers(st.session_state.currency)
    if not top_gainers:
        return None
    
    df = pd.DataFrame([{
        "coin_id": coin["id"],
        "name": coin["name"],
        "symbol": coin["symbol"],
        "24h_change": coin["price_change_percentage_24h"],
        "current_price": coin["current_price"],
        "market_cap": coin["market_cap"]
    } for coin in top_gainers])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Top Gainers')
        worksheet = writer.sheets['Top Gainers']
        
        header_format = writer.book.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1
        })
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    
    output.seek(0)
    return output

# Initialize session state
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = DEFAULT_COINS.copy()

if 'currency' not in st.session_state:
    st.session_state.currency = DEFAULT_CURRENCY

# App layout
st.title("📈 Crypto Price Tracker")
st.write("Real-time cryptocurrency price tracking using CoinGecko API")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    
    currencies = ["usd", "eur", "gbp", "jpy", "btc", "eth"]
    st.session_state.currency = st.selectbox(
        "Select Currency",
        currencies,
        index=currencies.index(st.session_state.currency)
    )
    
    st.subheader("Manage Watchlist")
    all_coins = get_coin_list()
    coin_names = {coin['id']: coin['name'] for coin in all_coins}
    
    st.subheader("Import Watchlist")
    uploaded_file = st.file_uploader("Upload XLSX file", type="xlsx")
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            if 'coin_id' in df.columns:
                new_coins = df['coin_id'].dropna

