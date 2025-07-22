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
                new_coins = df['coin_id'].dropna().unique().tolist()
                st.session_state.watchlist = list(set(st.session_state.watchlist + new_coins))
                st.success(f"Added {len(new_coins)} coins from file")
                time.sleep(1)
                st.rerun()
            else:
                st.error("File must contain a 'coin_id' column")
        except Exception as e:
            st.error(f"Error reading file: {e}")
    
    st.subheader("Get Top Gainers Template")
    if st.button("Download Top 20 Gainers Template"):
        template_file = create_template_file()
        if template_file:
            st.download_button(
                label="Download XLSX Template",
                data=template_file,
                file_name=f"top_20_gainers_{datetime.now().date()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Could not generate template file")
    
    st.subheader("Manual Watchlist Editing")
    new_coin = st.selectbox(
        "Add Cryptocurrency",
        [""] + sorted([coin['id'] for coin in all_coins], key=lambda x: coin_names[x].lower())
    )
    
    if st.button("Add to Watchlist") and new_coin:
        if new_coin not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_coin)
            st.success(f"Added {coin_names.get(new_coin, new_coin)} to watchlist")
            time.sleep(1)
            st.rerun()
    
    if st.session_state.watchlist:
        st.write("Current Watchlist:")
        for coin in st.session_state.watchlist.copy():
            cols = st.columns([4, 1])
            cols[0].write(f"- {coin_names.get(coin, coin)}")
            if cols[1].button("×", key=f"remove_{coin}"):
                st.session_state.watchlist.remove(coin)
                st.success(f"Removed {coin_names.get(coin, coin)} from watchlist")
                time.sleep(1)
                st.rerun()

# Main content
if not st.session_state.watchlist:
    st.warning("Your watchlist is empty. Add some cryptocurrencies from the sidebar.")
else:
    market_data = get_market_data(st.session_state.watchlist, st.session_state.currency)
    
    if market_data:
        st.subheader("Current Prices")
        
        display_data = []
        for coin in market_data:
            display_data.append({
                "Coin": f"{coin['name']} ({coin['symbol'].upper()})",
                "Price": f"{coin['current_price']:,.2f} {st.session_state.currency.upper()}",
                "1h": f"{coin['price_change_percentage_1h_in_currency'] or 0:.2f}%",
                "24h": f"{coin['price_change_percentage_24h_in_currency'] or 0:.2f}%",
                "7d": f"{coin['price_change_percentage_7d_in_currency'] or 0:.2f}%",
                "Market Cap": f"{coin['market_cap']:,.0f}",
                "24h Volume": f"{coin['total_volume']:,.0f}"
            })
        
        df = pd.DataFrame(display_data)
        
        def color_change(val):
            color = 'red' if float(val.replace('%', '')) < 0 else 'green'
            return f'color: {color}'
        
        styled_df = df.style.applymap(color_change, subset=['1h', '24h', '7d'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        st.subheader("Price History")
        
        col1, col2 = st.columns(2)
        selected_coin = col1.selectbox(
            "Select Coin",
            [coin['id'] for coin in market_data],
            format_func=lambda x: next(c['name'] for c in market_data if c['id'] == x)
        )
        time_period = col2.selectbox(
            "Time Period",
            ["1 Day", "7 Days", "30 Days"],
            index=1
        )
        
        days_map = {"1 Day": 1, "7 Days": 7, "30 Days": 30}
        days = days_map[time_period]
        
        historical_data = get_historical_data(selected_coin, st.session_state.currency, days)
        
        if historical_data and 'prices' in historical_data:
            df_history = pd.DataFrame(historical_data['prices'], columns=['timestamp', 'price'])
            df_history['date'] = pd.to_datetime(df_history['timestamp'], unit='ms')
            
            fig = px.line(
                df_history,
                x='date',
                y='price',
                title=f"{next(c['name'] for c in market_data if c['id'] == selected_coin)} Price History ({time_period})",
                labels={'price': f'Price ({st.session_state.currency.upper()})', 'date': 'Date'}
            )
            
            fig.update_layout(
                hovermode="x unified",
                showlegend=False,
                xaxis_title=None,
                yaxis_title=f"Price ({st.session_state.currency.upper()})",
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            fig.update_traces(
                hovertemplate="%{y:,.2f} " + st.session_state.currency.upper(),
                line=dict(width=2)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Could not load historical price data.")
    else:
        st.warning("Could not load current market data. Please try again later.")

# Footer
st.markdown("---")
st.markdown(
    """
    **Data Source:** [CoinGecko API](https://www.coingecko.com/en/api)  
    **Last Updated:** {}
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
)
