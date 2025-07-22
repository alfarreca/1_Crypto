import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.graph_objects as go
import time
import random

# --- Config ---
CMC_API_KEY = st.secrets.get("CMC_API_KEY", None)
CMC_API_URL = "https://pro-api.coinmarketcap.com/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
MAX_SYMBOLS_PER_BATCH = 10

DEFAULT_COINS = [
    "bitcoin", "ethereum", "solana", "pepe", "dogwifhat", "fetch-ai", "arweave",
    "fantom", "the-graph", "sui", "sei-network", "arbitrum", "optimism", "near",
    "avalanche", "polygon", "chainlink", "cosmos", "polkadot", "uniswap"
]

# --- Request wrapper ---
def safe_request(url, headers=None, params=None, max_attempts=3, timeout=10):
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code == 429:
                wait = 2 ** attempt + random.random()
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            time.sleep(2)
    return None

# --- Market data from CoinGecko ---
def get_market_data_gecko(ids, vs_currency="usd"):
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
        all_data.extend(response)
    return all_data

# --- Historical prices from CoinGecko ---
def get_price_history(coin_id, vs_currency="usd"):
    url = f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": 30}
    data = safe_request(url, params=params)
    if not data or "prices" not in data:
        return None
    df = pd.DataFrame(data["prices"], columns=["Timestamp", "Price"])
    df["Date"] = pd.to_datetime(df["Timestamp"], unit="ms")
    return df

# --- UI ---
st.set_page_config("Crypto Dashboard", layout="wide")
st.title("📊 Crypto Market Dashboard")

currency = st.selectbox("Quote Currency", ["usd", "eur", "gbp"], index=0)
coin_ids = DEFAULT_COINS

# --- Real-time Price Table ---
st.subheader("💰 Current Prices")
market_data = get_market_data_gecko(coin_ids, currency.lower())

if market_data:
    price_rows = []
    for coin in market_data:
        price_rows.append({
            "Coin": f"{coin['name']} ({coin['symbol'].upper()})",
            "Price": f"{coin['current_price']:,.2f} {currency.upper()}",
            "1h %": f"{coin.get('price_change_percentage_1h_in_currency', 0):.2f}%",
            "24h %": f"{coin.get('price_change_percentage_24h_in_currency', 0):.2f}%",
            "7d %": f"{coin.get('price_change_percentage_7d_in_currency', 0):.2f}%",
            "Market Cap": f"{coin.get('market_cap', 0):,.0f}",
            "24h Volume": f"{coin.get('total_volume', 0):,.0f}"
        })
    df_prices = pd.DataFrame(price_rows)
    st.dataframe(df_prices, use_container_width=True)

# --- Momentum Score Table ---
st.subheader("📊 Momentum Score")

momentum_data = []
for coin in market_data:
    try:
        one_h = coin.get('price_change_percentage_1h_in_currency') or 0
        twenty_four_h = coin.get('price_change_percentage_24h_in_currency') or 0
        seven_d = coin.get('price_change_percentage_7d_in_currency') or 0
        score = 0.1 * one_h + 0.3 * twenty_four_h + 0.6 * seven_d

        momentum_data.append({
            "Coin": f"{coin['name']} ({coin['symbol'].upper()})",
            "1h %": round(one_h, 2),
            "24h %": round(twenty_four_h, 2),
            "7d %": round(seven_d, 2),
            "Momentum Score": round(score, 2)
        })
    except Exception:
        continue

if momentum_data:
    df_momentum = pd.DataFrame(momentum_data).sort_values("Momentum Score", ascending=False).reset_index(drop=True)
    st.dataframe(df_momentum, use_container_width=True)

# --- Charts ---
st.subheader("📈 30-Day Price Action")
for coin in market_data:
    coin_id = coin["id"]
    with st.expander(f"{coin['name']} ({coin['symbol'].upper()})"):
        df_hist = get_price_history(coin_id, vs_currency=currency.lower())
        if df_hist is not None:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_hist["Date"], y=df_hist["Price"], mode="lines", name=coin["symbol"].upper()))
            fig.update_layout(title=f"{coin['name']} - 30 Day Chart", xaxis_title="Date", yaxis_title=f"Price ({currency.upper()})")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data available.")
