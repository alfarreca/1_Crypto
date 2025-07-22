import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime

st.set_page_config("Crypto Tracker", layout="wide")

CMC_API_URL = "https://pro-api.coinmarketcap.com/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "")

DEFAULT_COINS = ["BTC", "ETH", "SOL", "ADA", "XRP"]
DEFAULT_CURRENCY = "USD"

if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_COINS.copy()
if "currency" not in st.session_state:
    st.session_state.currency = DEFAULT_CURRENCY

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
            time.sleep(2)
    return None

@st.cache_data(ttl=180)
def get_market_data_cmc(symbols, convert="USD"):
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    results = []
    for i in range(0, len(symbols), 5):
        batch = symbols[i:i + 5]
        params = {"symbol": ",".join(batch), "convert": convert}
        res = safe_request(f"{CMC_API_URL}/cryptocurrency/quotes/latest", headers=headers, params=params)
        if not res or "data" not in res:
            return None
        for symbol in batch:
            try:
                coin = res["data"][symbol]
                quote = coin["quote"][convert]
                results.append({
                    "Coin": f"{coin.get('name', 'Unknown')} ({symbol})",
                    "Price": format_number(quote.get("price"), convert),
                    "1h": format_percent(quote.get("percent_change_1h")),
                    "24h": format_percent(quote.get("percent_change_24h")),
                    "7d": format_percent(quote.get("percent_change_7d")),
                    "Market Cap": format_number(quote.get("market_cap")),
                    "24h Volume": format_number(quote.get("volume_24h")),
                })
            except Exception as e:
                st.warning(f"⚠️ Failed to parse CMC data for {symbol}: {e}")
    return results

@st.cache_data(ttl=180)
def get_market_data_gecko(symbols, currency="usd"):
    coin_map = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano",
        "XRP": "ripple", "DOT": "polkadot", "LINK": "chainlink", "AVAX": "avalanche",
        "FTM": "fantom", "NEAR": "near", "GRT": "the-graph", "ARB": "arbitrum",
        "MATIC": "polygon", "SUI": "sui", "PEPE": "pepe", "ATOM": "cosmos",
        "FET": "fetch-ai", "UNI": "uniswap", "DOGE": "dogecoin"
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
                    "Price": format_number(c.get("current_price"), currency),
                    "1h": format_percent(c.get("price_change_percentage_1h_in_currency")),
                    "24h": format_percent(c.get("price_change_percentage_24h_in_currency")),
                    "7d": format_percent(c.get("price_change_percentage_7d_in_currency")),
                    "Market Cap": format_number(c.get("market_cap")),
                    "24h Volume": format_number(c.get("total_volume")),
                })
    return results

def format_number(value, suffix=""):
    try:
        return f"{value:,.2f} {suffix}" if value is not None else "N/A"
    except:
        return "N/A"

def format_percent(value):
    try:
        return f"{value:.2f}%" if value is not None else "N/A"
    except:
        return "N/A"

with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "JPY"], index=0)

    st.subheader("📥 Import Watchlist")
    file = st.file_uploader("Upload XLSX with 'symbol' column", type=["xlsx"])
    if file:
        try:
            df = pd.read_excel(file)
            if "symbol" in df.columns:
                imported = df["symbol"].dropna().str.upper().unique().tolist()
                st.session_state.watchlist = list(set(st.session_state.watchlist + imported))
                st.success(f"✅ Imported {len(imported)} symbols.")
                st.rerun()
            else:
                st.error("❌ Excel must contain a column named 'symbol'.")
        except Exception as e:
            st.error(f"Failed to read Excel: {e}")

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

symbols = st.session_state.watchlist
currency = st.session_state.currency.upper()

st.title("📊 Crypto Tracker (CMC + Fallback)")
st.markdown("Powered by [CoinMarketCap](https://coinmarketcap.com/api) with automatic fallback to CoinGecko.")

with st.spinner("Fetching live prices..."):
    data = get_market_data_cmc(symbols, currency)
    if not data:
        st.warning("⚠️ CMC failed. Trying CoinGecko...")
        data = get_market_data_gecko(symbols, currency.lower())

if not data:
    st.error("❌ No data returned from either API.")
else:
    df = pd.DataFrame(data)

    def color_pct(val):
        try:
            return "color: green" if float(val.replace('%', '')) > 0 else "color: red"
        except:
            return ""

    st.dataframe(df.style.applymap(color_pct, subset=["1h", "24h", "7d"]), use_container_width=True)

    st.markdown(f"🕒 Last updated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
