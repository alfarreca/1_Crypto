import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from io import BytesIO

# --- CoinGecko API endpoints ---
API_URL = "https://api.coingecko.com/api/v3/simple/price"

# --- Token Mapping ---
TOKEN_IDS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Tron": "tron"
    # Hype is not available on CoinGecko
}

# --- Company Crypto Treasury Data ---
data = [
    {"Name": "Bitmine Immersion Technologies", "Symbol": "BITM", "Token": "Ethereum", "Holdings ($M)": 250, "Market Cap ($M)": 2000},
    {"Name": "SRM Entertainment / Tron Inc.", "Symbol": "SRM", "Token": "Tron", "Holdings ($M)": 100, "Market Cap ($M)": 800},
    {"Name": "Volcon Inc.", "Symbol": "VCNX", "Token": "Bitcoin", "Holdings ($M)": 500, "Market Cap ($M)": 700},
    {"Name": "Sequans Communications", "Symbol": "SQNS", "Token": "Bitcoin", "Holdings ($M)": 384, "Market Cap ($M)": 250},
    {"Name": "Trump Media & Technology Group", "Symbol": "TMGT", "Token": "Bitcoin", "Holdings ($M)": 2000, "Market Cap ($M)": 5000},
    {"Name": "Hype Treasury Co.", "Symbol": "HYPECO", "Token": "Hype", "Holdings ($M)": 305, "Market Cap ($M)": 1000}
]

df = pd.DataFrame(data)

# --- Fetch Live Prices ---
def fetch_live_prices():
    ids = ','.join(TOKEN_IDS.values())
    response = requests.get(API_URL, params={"ids": ids, "vs_currencies": "usd"})
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch live crypto prices.")
        return {}

# --- Main App ---
st.set_page_config(page_title="Crypto Treasury Valuation Tracker", layout="wide")
st.title("📊 Crypto Treasury Valuation Tracker")
st.caption("Compare company crypto holdings vs market caps with live price feed")

prices = fetch_live_prices()

# Manual Hype price input
hype_price = st.sidebar.number_input("Manual Price Input: HYPE (USD)", value=3.25, step=0.01)

# Display live prices
st.subheader("🔁 Live Token Prices")
for name, cg_id in TOKEN_IDS.items():
    price = prices.get(cg_id, {}).get("usd", "N/A")
    st.markdown(f"**{name}**: ${price:,}")
st.markdown(f"**Hype**: ${hype_price:,} (manual input)")

# Calculate Implied Premium
premiums = []
for idx, row in df.iterrows():
    token = row["Token"]
    token_price = hype_price if token == "Hype" else prices.get(TOKEN_IDS.get(token, ""), {}).get("usd", 0)
    nav = row["Holdings ($M)"]
    market_cap = row["Market Cap ($M)"]
    premium = market_cap / nav if nav else None
    premiums.append(premium)

df["Implied Premium (x NAV)"] = premiums

st.subheader("🏢 Company Valuation vs Holdings")
st.dataframe(df, use_container_width=True)

# --- Charts ---
st.subheader("📊 Market Cap vs Holdings")
fig_bar = px.bar(
    df,
    x="Symbol",
    y=["Market Cap ($M)", "Holdings ($M)"],
    barmode="group",
    title="Market Cap vs Token Holdings"
)
st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("🥧 Token Exposure by Holdings")
token_group = df.groupby("Token")["Holdings ($M)"].sum().reset_index()
fig_pie = px.pie(
    token_group,
    names="Token",
    values="Holdings ($M)",
    title="Total Treasury Exposure by Token"
)
st.plotly_chart(fig_pie, use_container_width=True)

# --- Excel Export ---
excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False, engine='openpyxl')
excel_buffer.seek(0)

st.download_button(
    label="📥 Download Excel",
    data=excel_buffer,
    file_name="Crypto_Treasury_Valuation_Tracker.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
