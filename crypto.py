import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.graph_objects as go
import time
import random

# --- Config ---
CMC_API_KEY = st.secrets["CMC_API_KEY"]
CMC_API_URL = "https://pro-api.coinmarketcap.com/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
MAX_SYMBOLS_PER_BATCH = 10

# --- Safe API request ---
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

# --- Get real-time prices from CMC ---
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
                    "symbol": symbol,
                    "name": coin_data.get("name", symbol),
                    "Coin": f"{coin_data.get('name', '')} ({symbol})",
                    "Price": f"{quote['price']:,.2f} {convert}" if quote.get("price") else "-",
                    "1h": f"{quote.get('percent_change_1h', 0):.2f}%",
                    "24h": f"{quote.get('percent_change_24h', 0):.2f}%",
                    "7d": f"{quote.get('percent_change_7d', 0):.2f}%",
                    "Market Cap": f"{quote.get('market_cap', 0):,.0f}",
                    "24h Volume": f"{quote.get('volume_24h', 0):,.0f}"
                })
            except Exception as e:
                st.warning(f"⚠️ Failed to parse CMC data for {symbol}: {e}")
    return all_data

# --- Fallback to CoinGecko ---
def get_market_data_gecko(symbols, vs_currency="usd"):
    ids = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano",
        "XRP": "ripple", "DOT": "polkadot", "LINK": "chainlink", "SUI": "sui",
        "ARB": "arbitrum", "AVAX": "avalanche-2", "ATOM": "cosmos", "FET": "fetch-ai",
        "MATIC": "polygon", "GRT": "the-graph", "NEAR": "near", "PEPE": "pepe",
        "DOGE": "dogecoin", "UNI": "uniswap", "AR": "arweave"
    }
    all_data = []
    mapped_ids = [ids.get(sym.upper(), sym.lower()) for sym in symbols]
    for i in range(0, len(mapped_ids), MAX_SYMBOLS_PER_BATCH):
        batch = mapped_ids[i:i + MAX_SYMBOLS_PER_BATCH]
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
                "symbol": coin['symbol'].upper(),
                "name": coin['name'],
                "Coin": f"{coin['name']} ({coin['symbol'].upper()})",
                "Price": f"{coin['current_price']:,.2f} {vs_currency.upper()}",
                "1h": f"{coin.get('price_change_percentage_1h_in_currency', 0):.2f}%",
                "24h": f"{coin.get('price_change_percentage_24h_in_currency', 0):.2f}%",
                "7d": f"{coin.get('price_change_percentage_7d_in_currency', 0):.2f}%",
                "Market Cap": f"{coin.get('market_cap', 0):,.0f}",
                "24h Volume": f"{coin.get('total_volume', 0):,.0f}"
            })
    return all_data

# --- Historical chart from CoinGecko ---
def get_price_history(symbol, vs_currency="usd"):
    cg_ids = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano",
        "XRP": "ripple", "DOT": "polkadot", "LINK": "chainlink", "SUI": "sui",
        "ARB": "arbitrum", "AVAX": "avalanche-2", "ATOM": "cosmos", "FET": "fetch-ai",
        "MATIC": "polygon", "GRT": "the-graph", "NEAR": "near", "PEPE": "pepe",
        "DOGE": "dogecoin", "UNI": "uniswap", "AR": "arweave"
    }
    coin_id = cg_ids.get(symbol.upper())
    if not coin_id:
        return None

    url = f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": 30}
    data = safe_request(url, params=params)
    if not data or "prices" not in data:
        return None

    df = pd.DataFrame(data["prices"], columns=["Timestamp", "Price"])
    df["Date"] = pd.to_datetime(df["Timestamp"], unit="ms")
    return df

# --- Streamlit UI ---
st.set_page_config("Crypto Tracker", layout="wide")
st.title("📊 Crypto Tracker (CMC + Charts + Fallback)")
currency = st.selectbox("Currency", ["USD", "EUR", "GBP"], index=0)

uploaded_file = st.file_uploader("Upload XLSX with 'symbol' column", type=["xlsx"])
DEFAULT_COINS = [
    "bitcoin", "ethereum", "solana", "pepe", "dogwifhat", "fetch-ai", "arweave",
    "fantom", "the-graph", "sui", "sei-network", "arbitrum", "optimism", "near",
    "avalanche", "polygon", "chainlink", "cosmos", "polkadot", "uniswap"
]


if "watchlist" not in st.session_state:
    st.session_state.watchlist = default_watchlist.copy()

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

new_symbol = st.text_input("Add Symbol to Watchlist", placeholder="e.g., BTC, ETH")
if st.button("Add") and new_symbol:
    st.session_state.watchlist.append(new_symbol.upper())

# --- Live Prices ---
with st.spinner("Fetching real-time prices..."):
    data = get_market_data_cmc(st.session_state.watchlist, currency.upper())
    if not data:
        st.warning("⚠️ Falling back to CoinGecko...")
        data = get_market_data_gecko(st.session_state.watchlist, currency.lower())

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df[["Coin", "Price", "1h", "24h", "7d", "Market Cap", "24h Volume"]], use_container_width=True)
    else:
        st.error("❌ No data available.")
        st.stop()

# --- Price Charts ---
st.subheader("📈 30-Day Price Action")
for entry in data:
    symbol = entry["symbol"]
    with st.expander(f"📉 {entry['name']} ({symbol})"):
        hist_df = get_price_history(symbol, vs_currency=currency.lower())
        if hist_df is not None:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_df["Date"], y=hist_df["Price"], mode="lines", name=symbol))
            fig.update_layout(title=f"{entry['name']} - 30 Day Price Chart", xaxis_title="Date", yaxis_title=f"Price ({currency})")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chart data available.")
