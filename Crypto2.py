import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
import time
import random
import io

# App configuration
st.set_page_config(
    page_title="Crypto Price Tracker",
    page_icon="₿",
    layout="wide"
)

# API constants
CMC_API_URL = "https://pro-api.coinmarketcap.com/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
DEFAULT_COINS = ["BTC", "ETH", "SOL", "ADA", "XRP"]
DEFAULT_CURRENCY = "USD"

# Load API key from secrets
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "")

# Utility to retry and handle rate limits
def safe_request(url, headers=None, params=None, max_attempts=3, delay=1.5):
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                wait = 2 ** attempt + random.random()
                st.warning(f"Rate limit hit. Retrying in {wait:.1f}s...")
                time.sleep(wait)
            else:
                st.error(f"HTTP Error {response.status_code}: {response.text}")
                raise e
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return None
    return None

# Market Data - CoinMarketCap
@st.cache_data(ttl=180)
def get_market_data_cmc(symbols, convert="USD"):
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": ",".join(symbols), "convert": convert}
    data = safe_request(f"{CMC_API_URL}/cryptocurrency/quotes/latest", headers, params)
    results = []
    try:
        for symbol in symbols:
            coin = data["data"][symbol]
            quote = coin["quote"][convert]
            results.append({
                "Coin": f"{coin['name']} ({symbol})",
                "Price": f"{quote['price']:,.2f} {convert}",
                "1h": f"{quote.get('percent_change_1h', 0):.2f}%",
                "24h": f"{quote.get('percent_change_24h', 0):.2f}%",
                "7d": f"{quote.get('percent_change_7d', 0):.2f}%",
                "Market Cap": f"{quote['market_cap']:,.0f}",
                "24h Volume": f"{quote['volume_24h']:,.0f}"
            })
    except:
        return None
    return results

# Fallback to CoinGecko
@st.cache_data(ttl=180)
def get_market_data_gecko(symbols, currency="usd"):
    coin_map = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano",
        "XRP": "ripple", "DOT": "polkadot", "LINK": "chainlink", "AVAX": "avalanche"
    }
    ids = [coin_map.get(s.upper(), "") for s in symbols if s.upper() in coin_map]
    results = []

    for i in range(0, len(ids), 5):
        batch = ",".join(ids[i:i+5])
        params = {
            "vs_currency": currency.lower(),
            "ids": batch,
            "order": "market_cap_desc",
            "price_change_percentage": "1h,24h,7d"
        }
        r = safe_request(f"{COINGECKO_API_URL}/coins/markets", params=params)
        if r:
            for c in r:
                results.append({
                    "Coin": f"{c['name']} ({c['symbol'].upper()})",
                    "Price": f"{c['current_price']:,.2f} {currency}",
                    "1h": f"{c.get('price_change_percentage_1h_in_currency', 0):.2f}%",
                    "24h": f"{c.get('price_change_percentage_24h_in_currency', 0):.2f}%",
                    "7d": f"{c.get('price_change_percentage_7d_in_currency', 0):.2f}%",
                    "Market Cap": f"{c['market_cap']:,.0f}",
                    "24h Volume": f"{c['total_volume']:,.0f}"
                })
    return results

# App state
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = DEFAULT_COINS.copy()
if 'currency' not in st.session_state:
    st.session_state.currency = DEFAULT_CURRENCY

# Header
st.title("📊 Crypto Price Tracker (CMC + Fallback)")
st.markdown("Real-time prices from [CoinMarketCap](https://coinmarketcap.com/api) with automatic fallback to CoinGecko.")

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "JPY"], index=0)

    st.subheader("📥 Import Watchlist")
    uploaded_file = st.file_uploader("Upload XLSX file", type=["xlsx"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            if "symbol" in df.columns:
                symbols = df["symbol"].dropna().str.upper().unique().tolist()
                st.session_state.watchlist = list(set(st.session_state.watchlist + symbols))
                st.success(f"✅ Imported {len(symbols)} symbols.")
                st.rerun()
            else:
                st.error("❌ File must contain a 'symbol' column.")
        except Exception as e:
            st.error(f"Failed to read file: {e}")

    st.subheader("🔧 Manage Watchlist")
    new_coin = st.text_input("Add Symbol (e.g., BTC, ETH)").upper()
    if st.button("Add") and new_coin and new_coin not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_coin)
        st.rerun()

    for coin in st.session_state.watchlist.copy():
        col1, col2 = st.columns([4, 1])
        col1.write(f"- {coin}")
        if col2.button("🗑", key=f"rm_{coin}"):
            st.session_state.watchlist.remove(coin)
            st.rerun()

# Load market data
symbols = st.session_state.watchlist
currency = st.session_state.currency.upper()

with st.spinner("🔄 Loading market data..."):
    data = get_market_data_cmc(symbols, currency)
    if not data:
        st.warning("⚠️ CoinMarketCap API failed. Falling back to CoinGecko.")
        data = get_market_data_gecko(symbols, currency.lower())

if not data:
    st.error("❌ Failed to load market data from both APIs.")
else:
    df = pd.DataFrame(data)

    def color_change(val):
        try:
            color = 'red' if float(val.replace('%', '')) < 0 else 'green'
            return f'color: {color}'
        except:
            return ""

    styled_df = df.style.applymap(color_change, subset=['1h', '24h', '7d'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown(
    f"📡 Data from [CoinMarketCap](https://coinmarketcap.com/api) & [CoinGecko](https://coingecko.com)  \n"
    f"🕒 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
