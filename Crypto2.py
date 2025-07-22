import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random
import numpy as np
from io import BytesIO
import base64

# Simulated historical data generator for price chart demo
def generate_price_history(symbol, days=30):
    base_price = random.uniform(1, 1000)
    dates = [datetime.now() - timedelta(days=i) for i in range(days)][::-1]
    prices = [base_price + random.gauss(0, base_price * 0.01) for _ in dates]
    return pd.DataFrame({"Date": dates, "Price": prices, "Symbol": symbol})

# Simulate a few charts
symbols = ["BTC", "ETH", "SOL"]
dfs = [generate_price_history(symbol) for symbol in symbols]

# Plot and collect images
chart_imgs = {}
for df in dfs:
    fig, ax = plt.subplots()
    ax.plot(df["Date"], df["Price"], label=df["Symbol"], linewidth=2)
    ax.set_title(f"{df['Symbol'].iloc[0]} - 30 Day Price")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (USD)")
    ax.legend()
    fig.autofmt_xdate()

    # Convert to base64 image for embedding
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    chart_imgs[df["Symbol"].iloc[0]] = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()

import ace_tools as tools; tools.display_dataframe_to_user(name="30-Day Simulated Price Data", dataframe=pd.concat(dfs, ignore_index=True))
