# Crypto Tracker: CoinMarketCap API with CoinGecko fallback

import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime

# --- API Settings ---
CMC_API_URL = "https://pro-api.coinmarketcap.com/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
CMC_API_KEY = st.secrets["CMC_API_KEY"]
MAX_SYMBOLS_PER_BATCH = 10

# --- Helper: Retryable Request ---
def safe_request(url, headers=None, params=None, max_attempts=3, timeout=10):
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code == 429:
                wait = 2 ** attempt + random.random()
                st.warning(f"Rate limit hit. Retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            st.warning(f"Request failed: {e}")
            time.sleep(2)
    return None

# --- Fetch CMC Data ---
def get_market_data_cmc(symbols, convert="USD"):
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    all_data = []
    for i in range(0, len(symbols), MAX_SYMBOLS_PER_BATCH):
        batch = symbols[i:i + MAX_SYMBOLS_PER_BATCH]
        params = {"symbol": ",".join(batch), "convert": convert}
        response = safe_request(f"{CMC_API_URL}/cryptocurrency/quotes/latest", headers, params)
        if not response or "data" not in response:
            continue
        for symbol in batch:
            try:
                coin_data = response["data"].get(symbol, {})
                quote = coin_data.get("quote", {}).get(convert, {})
                all_data.append({
                    "Coin": f"{coin_data.get('name', '')} ({symbol})",
                    "Price": f"{quote['price']:,.2f} {convert}" if quote.get("price") is not None else "-",
                    "1h": f"{quote.get('percent_change_1h', 0):.2f}%",
                    "24h": f"{quote.get('percent_change_24h', 0):.2f}%",
                    "7d": f"{quote.get('percent_change_7d', 0):.2f}%",
                    "Market Cap": f"{quote.get('market_cap', 0):,.0f}",
                    "24h Volume": f"{quote.get('volume_24h', 0):,.0f}"
                })
            except Exception as e:
                st.warning(f"⚠️ Failed to parse CMC data for {symbol}: {e}")
    return all_data

# --- Fetch CoinGecko Fallback ---
def get_market_data_gecko(symbols, vs_currency="usd"):
    mapping = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano",
        "XRP": "ripple", "DOT": "polkadot", "LINK": "chainlink", "SUI": "sui",
        "ARB": "arbitrum", "AVAX": "avalanche-2", "ATOM": "cosmos", "FET": "fetch-ai",
        "MATIC": "polygon", "GRT": "the-graph", "NEAR": "near", "PEPE": "pepe",
        "DOGE": "dogecoin", "UNI": "uniswap", "AR": "arweave"
    }
    ids = [mapping.get(sym.upper(), sym.lower()) for sym in symbols]
    all_data = []
    for i in range(0, len(ids), MAX_SYMBOLS_PER_BATCH):
        batch = ids[i:i + MAX_SYMBOLS_PER_BATCH]
        params = {
            "vs_currency": vs_currency,
            "ids": ",".join(batch),
            "price_change_percentage": "1h,24h,7d"
        }
        response = safe_request(f"{COINGECKO_API_URL}/coins/markets", params=params)
        if not response:
            continue
        for coin in response:
            all_data.append({
                "Coin": f"{coin['name']} ({coin['symbol'].upper()})",
                "Price": f"{coin['current_price']:,.2f} {vs_currency.upper()}",
                "1h": f"{coin.get('price_change_percentage_1h_in_currency', 0):.2f}%",
                "24h": f"{coin.get('price_change_percentage_24h_in_currency', 0):.2f}%",
                "7d": f"{coin.get('price_change_percentage_7d_in_currency', 0):.2f}%",
                "Market Cap": f"{coin.get('market_cap', 0):,.0f}",
                "24h Volume": f"{coin.get('total_volume', 0):,.0f}"
            })
    return all_data

# --- Streamlit UI ---
st.set_page_config("Crypto Tracker (CMC + Fallback)")
st.title("📈 Crypto Tracker (CMC + Fallback)")
st.markdown("Powered by [CoinMarketCap](https://coinmarketcap.com) with automatic fallback to CoinGecko.")

currency = st.selectbox("Currency", ["USD", "EUR", "GBP"], index=0)
uploaded_file = st.file_uploader("📤 Import XLSX with 'symbol' column", type=["xlsx"])
default_watchlist = ["BTC", "ETH", "SOL", "ADA", "XRP"]

if "watchlist" not in st.session_state:
    st.session_state.watchlist = default_watchlist.copy()

# Upload XLSX
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if "symbol" in df.columns:
            st.session_state.watchlist = df["symbol"].dropna().str.upper().unique().tolist()
            st.success("✅ Watchlist updated.")
        else:
            st.error("❌ No 'symbol' column found.")
    except Exception as e:
        st.error(f"❌ File error: {e}")

# Add Symbol
new_symbol = st.text_input("Add to Watchlist", placeholder="e.g., BTC, ETH")
if st.button("Add") and new_symbol:
    st.session_state.watchlist.append(new_symbol.upper())

# Show Watchlist
st.sidebar.write("### Watchlist")
for s in st.session_state.watchlist:
    st.sidebar.markdown(f"- {s}")

# Fetch Data
with st.spinner("Fetching data..."):
    data = get_market_data_cmc(st.session_state.watchlist, currency.upper())
    if not data:
        st.warning("⚠️ CMC API failed. Using CoinGecko fallback.")
        data = get_market_data_gecko(st.session_state.watchlist, currency.lower())

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.error("❌ Could not fetch data from either source.")
