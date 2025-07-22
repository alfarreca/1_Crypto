import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time
import random

# ─── Configuration ───────────────────────────────────────────────
st.set_page_config(page_title="Crypto Tracker", page_icon="₿", layout="wide")

CMC_API_URL = "https://pro-api.coinmarketcap.com/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "")

DEFAULT_COINS = ["BTC", "ETH", "SOL", "ADA", "XRP"]
DEFAULT_CURRENCY = "USD"

# ─── App State ───────────────────────────────────────────────────
if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_COINS.copy()
if "currency" not in st.session_state:
    st.session_state.currency = DEFAULT_CURRENCY

# ─── API Request Helper ──────────────────────────────────────────
def safe_request(url, headers=None, params=None, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code == 429:
                wait = 2 ** attempt + random.random()
                st.warning(f"Rate limit hit. Retrying in {wait:.1f}s...")
                time.sleep(wait)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == max_attempts - 1:
                st.error(f"API request failed: {e}")
                return None
            time.sleep(2)

# ─── CoinMarketCap: Batched Quote Retrieval ─────────────────────
@st.cache_data(ttl=180)
def get_market_data_cmc(symbols, convert="USD"):
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    results = []
    for i in range(0, len(symbols), 5):
        batch = symbols[i:i + 5]
        params = {"symbol": ",".join(batch), "convert": convert}
        res = safe_request(f"{CMC_API_URL}/cryptocurrency/quotes/latest", headers=headers, params=params)
        if not res:
            return None
        for symbol in batch:
            try:
                coin = res["data"][symbol]
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
            except KeyError:
                continue
    return results

# ─── CoinGecko Fallback ──────────────────────────────────────────
@st.cache_data(ttl=180)
def get_market_data_gecko(symbols, currency="usd"):
    coin_map = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano",
        "XRP": "ripple", "DOT": "polkadot", "LINK": "chainlink", "AVAX": "avalanche"
    }
    ids = [coin_map.get(s.upper(), "") for s in symbols if s.upper() in coin_map]
    results = []

    for i in range(0, len(ids), 5):
        params = {
            "vs_currency": currency,
            "ids": ",".join(ids[i:i + 5]),
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

# ─── Sidebar UI ──────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "JPY"], index=0)

    st.subheader("📥 Import Watchlist")
    file = st.file_uploader("Upload XLSX with 'symbol' column", type=["xlsx"])
    if file:
        try:
            df = pd.read_excel(file)
            if "symbol" in df.columns:
                symbols = df["symbol"].dropna().str.upper().unique().tolist()
                st.session_state.watchlist = list(set(st.session_state.watchlist + symbols))
                st.success(f"✅ Imported {len(symbols)} symbols.")
                st.rerun()
            else:
                st.error("❌ Must contain a 'symbol' column.")
        except Exception as e:
            st.error(f"File read error: {e}")

    st.subheader("➕ Add to Watchlist")
    new_coin = st.text_input("Symbol (e.g., BTC)").upper()
    if st.button("Add") and new_coin:
        st.session_state.watchlist.append(new_coin)
        st.rerun()

    for coin in st.session_state.watchlist.copy():
        col1, col2 = st.columns([4, 1])
        col1.write(f"- {coin}")
        if col2.button("🗑", key=f"rm_{coin}"):
            st.session_state.watchlist.remove(coin)
            st.rerun()

# ─── Data Retrieval ──────────────────────────────────────────────
symbols = st.session_state.watchlist
currency = st.session_state.currency.upper()

st.title("📊 Crypto Tracker (CMC + Fallback)")
st.markdown("Powered by [CoinMarketCap](https://coinmarketcap.com/api) with automatic fallback to CoinGecko.")

with st.spinner("🔄 Fetching prices..."):
    data = get_market_data_cmc(symbols, currency)
    if not data:
        st.warning("⚠️ CMC API failed. Falling back to CoinGecko...")
        data = get_market_data_gecko(symbols, currency.lower())

if not data:
    st.error("❌ No data available.")
else:
    df = pd.DataFrame(data)

    def color_change(val):
        try:
            return "color: green" if float(val.replace('%', '')) > 0 else "color: red"
        except:
            return ""

    styled = df.style.applymap(color_change, subset=["1h", "24h", "7d"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(
    f"📡 Data from [CoinMarketCap](https://coinmarketcap.com/api) and [CoinGecko](https://coingecko.com)  \n"
    f"⏱ Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
