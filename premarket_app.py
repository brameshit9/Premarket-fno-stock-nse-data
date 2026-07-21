"""
NSE F&O Universe Premarket Tracker - Streamlit App
-----------------------------------------------------
Source     : https://www.nseindia.com/market-data/pre-open-market-cotation
API used   : https://www.nseindia.com/api/market-data-pre-open?key=FNO

NSE's pre-open session runs ~9:00-9:15 AM IST on trading days. Outside
that window, the API still responds but with a STALE snapshot from the
previous session -- this app clearly flags that so you don't mistake
old data for live data.

Run locally:
    pip install -r requirements.txt
    streamlit run premarket_app.py

DISCLAIMER: This app surfaces public premarket order-book data
(indicative price, buy/sell quantities, historical range). The
"WatchScore" and "NearCircuitFlag" are simple descriptive heuristics
based on that data -- not predictions, not recommendations. Always
verify live price/quantity before placing any order.
"""

import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime
import pytz

BASE_URL = "https://www.nseindia.com"
PREOPEN_PAGE = f"{BASE_URL}/market-data/pre-open-market-cotation"
PREOPEN_API = f"{BASE_URL}/api/market-data-pre-open"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "Referer": PREOPEN_PAGE,
}

SECURITIES_FO = [
    '360ONE', 'ABB', 'ABCAPITAL', 'ADANIENSOL', 'ADANIENT',
    'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER', 'ALKEM', 'AMBER',
    'AMBUJACEM', 'ANGELONE', 'APLAPOLLO', 'APOLLOHOSP', 'ASHOKLEY',
    'ASIANPAINT', 'ASTRAL', 'AUBANK', 'AUROPHARMA', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHLDNG', 'BAJFINANCE', 'BANDHANBNK',
    'BANKBARODA', 'BANKINDIA', 'BDL', 'BEL', 'BHARATFORG',
    'BHARTIARTL', 'BHEL', 'BIOCON', 'BLUESTARCO', 'BOSCHLTD',
    'BPCL', 'BRITANNIA', 'BSE', 'CAMS', 'CANBK',
    'CDSL', 'CGPOWER', 'CHOLAFIN', 'CIPLA', 'COALINDIA',
    'COCHINSHIP', 'COFORGE', 'COLPAL', 'CONCOR', 'CROMPTON',
    'CUMMINSIND', 'DABUR', 'DALBHARAT', 'DELHIVERY', 'DIVISLAB',
    'DIXON', 'DLF', 'DMART', 'DRREDDY', 'EICHERMOT',
    'ETERNAL', 'EXIDEIND', 'FEDERALBNK', 'FORCEMOT', 'FORTIS',
    'GAIL', 'GLENMARK', 'GMRAIRPORT', 'GODFRYPHLP', 'GODREJCP',
    'GODREJPROP', 'GRASIM', 'GVT&D', 'HAL', 'HAVELLS',
    'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO',
    'HINDALCO', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HYUNDAI',
    'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDEA', 'IDFCFIRSTB',
    'IEX', 'INDHOTEL', 'INDIANB', 'INDIGO', 'INDUSINDBK',
    'INDUSTOWER', 'INFY', 'INOXWIND', 'IOC', 'IREDA',
    'IRFC', 'ITC', 'JINDALSTEL', 'JIOFIN', 'JSWENERGY',
    'JSWSTEEL', 'JUBLFOOD', 'KALYANKJIL', 'KAYNES', 'KEI',
    'KFINTECH', 'KOTAKBANK', 'KPITTECH', 'LAURUSLABS', 'LICHSGFIN',
    'LICI', 'LODHA', 'LT', 'LTF', 'LTM',
    'LUPIN', 'M&M', 'MANAPPURAM', 'MANKIND', 'MARICO',
    'MARUTI', 'MAXHEALTH', 'MAZDOCK', 'MCX', 'MFSL',
    'MOTHERSON', 'MOTILALOFS', 'MPHASIS', 'MUTHOOTFIN', 'NAM-INDIA',
    'NATIONALUM', 'NAUKRI', 'NBCC', 'NESTLEIND', 'NHPC',
    'NMDC', 'NTPC', 'NUVAMA', 'NYKAA', 'OBEROIRLTY',
    'OFSS', 'OIL', 'ONGC', 'PAGEIND', 'PATANJALI',
    'PAYTM', 'PERSISTENT', 'PETRONET', 'PFC', 'PGEL',
    'PHOENIXLTD', 'PIDILITIND', 'PIIND', 'PNB', 'PNBHOUSING',
    'POLICYBZR', 'POLYCAB', 'POWERGRID', 'POWERINDIA', 'PREMIERENE',
    'PRESTIGE', 'RADICO', 'RBLBANK', 'RECLTD', 'RELIANCE',
    'RVNL', 'SAIL', 'SBICARD', 'SBILIFE', 'SBIN',
    'SHREECEM', 'SHRIRAMFIN', 'SIEMENS', 'SOLARINDS', 'SONACOMS',
    'SRF', 'SUNPHARMA', 'SUPREMEIND', 'SUZLON', 'SWIGGY',
    'TATACONSUM', 'TATAELXSI', 'TATAPOWER', 'TATASTEEL', 'TCS',
    'TECHM', 'TIINDIA', 'TITAN', 'TMPV', 'TORNTPHARM',
    'TRENT', 'TVSMOTOR', 'ULTRACEMCO', 'UNIONBANK', 'UNITDSPR',
    'UNOMINDA', 'UPL', 'VBL', 'VEDL', 'VMM',
    'VOLTAS', 'WAAREEENER', 'WIPRO', 'YESBANK', 'ZYDUSLIFE',
]


def _get_proxies():
    proxy_url = st.secrets.get("PROXY_URL") if hasattr(st, "secrets") else None
    if proxy_url:
        return {"http": proxy_url, "https": proxy_url}
    return None


def get_nse_session(timeout: int = 15) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    proxies = _get_proxies()
    if proxies:
        session.proxies.update(proxies)
    session.get(BASE_URL, timeout=timeout)
    time.sleep(1)
    return session


@st.cache_data(ttl=30, show_spinner=False)
def fetch_preopen_data(key: str = "FNO", retries: int = 3, timeout: int = 15) -> dict:
    last_error = None
    for attempt in range(retries):
        try:
            session = get_nse_session(timeout)
            resp = session.get(f"{PREOPEN_API}?key={key}", timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            last_error = f"HTTP {resp.status_code}"
        except Exception as exc:
            last_error = exc
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch premarket data after {retries} attempts: {last_error}")


def parse_preopen(data: dict) -> pd.DataFrame:
    rows = []
    for item in data.get("data", []):
        meta = item.get("metadata", {})
        pre = item.get("detail", {}).get("preOpenMarket", {})
        rows.append({
            "Symbol": meta.get("symbol"),
            "PrevClose": meta.get("previousClose"),
            "IEP": pre.get("IEP", meta.get("iep")),
            "Change": meta.get("change"),
            "PctChange": meta.get("pChange"),
            "YearHigh": meta.get("yearHigh"),
            "YearLow": meta.get("yearLow"),
            "FinalQuantity": pre.get("finalQuantity"),
            "TotalTradedVolume": pre.get("totalTradedVolume"),
            "TotalTurnover": meta.get("totalTurnover"),
            "MarketCap": meta.get("marketCap"),
            "TotalBuyQuantity": pre.get("totalBuyQuantity"),
            "TotalSellQuantity": pre.get("totalSellQuantity"),
        })
    return pd.DataFrame(rows)


def add_trade_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    buy = df["TotalBuyQuantity"].fillna(0)
    sell = df["TotalSellQuantity"].fillna(0)
    total_qty = buy + sell

    df["OrderImbalance"] = np.where(total_qty > 0, (buy - sell) / total_qty, np.nan)
    df["BuySellRatio"] = np.where(sell > 0, buy / sell, np.nan)
    df["DistFrom52WHighPct"] = np.where(
        df["YearHigh"] > 0, (df["IEP"] - df["YearHigh"]) / df["YearHigh"] * 100, np.nan
    )
    df["DistFrom52WLowPct"] = np.where(
        df["YearLow"] > 0, (df["IEP"] - df["YearLow"]) / df["YearLow"] * 100, np.nan
    )
    df["NearCircuitFlag"] = df["PctChange"].abs() >= 9
    df["WatchScore"] = df["PctChange"].abs() * (1 + df["OrderImbalance"].abs().fillna(0))
    return df


def filter_to_fo_universe(df: pd.DataFrame, universe=SECURITIES_FO):
    universe_set = set(universe)
    filtered = df[df["Symbol"].isin(universe_set)].copy()
    found = set(filtered["Symbol"])
    missing = sorted(universe_set - found)
    return filtered, missing


def is_preopen_session_live():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False, "Weekend — market closed, data is stale.", now
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end = now.replace(hour=9, minute=15, second=0, microsecond=0)
    if start <= now <= end:
        return True, "Live pre-open window.", now
    return False, "Outside 9:00-9:15 AM IST window — this is a STALE/previous-session snapshot, not live premarket.", now


def plot_premarket(df: pd.DataFrame, top_n: int | None = None):
    plot_df = df.dropna(subset=["PctChange"]).sort_values("PctChange", ascending=True)
    if top_n:
        # take the top_n by absolute move, then re-sort ascending for the barh
        plot_df = plot_df.reindex(
            plot_df["PctChange"].abs().sort_values(ascending=False).head(top_n).index
        ).sort_values("PctChange", ascending=True)

    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in plot_df["PctChange"]]

    fig, axes = plt.subplots(
        1, 2, figsize=(16, max(6, len(plot_df) * 0.28)),
        gridspec_kw={"width_ratios": [3, 1]},
    )

    ax1 = axes[0]
    bars = ax1.barh(plot_df["Symbol"], plot_df["PctChange"], color=colors)
    ax1.axvline(0, color="black", linewidth=0.8)
    ax1.set_xlabel("% Change (Premarket vs Prev Close)")
    ax1.set_title("F&O Universe Premarket Movement", fontsize=13, fontweight="bold")
    ax1.tick_params(axis="y", labelsize=8)
    ax1.grid(axis="x", linestyle="--", alpha=0.4)

    max_abs = plot_df["PctChange"].abs().max() if len(plot_df) else 1
    pad = max_abs * 0.15 if max_abs > 0 else 1
    ax1.set_xlim(plot_df["PctChange"].min() - pad, plot_df["PctChange"].max() + pad)

    has_change = "Change" in plot_df.columns
    for bar, (_, row) in zip(bars, plot_df.iterrows()):
        width = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        pct_txt = f"{width:+.2f}%"
        if has_change and pd.notna(row.get("Change")):
            label = f"{pct_txt}  (₹{row['Change']:+.2f})"
        else:
            label = pct_txt
        offset = pad * 0.06
        if width >= 0:
            ax1.text(width + offset, y, label, va="center", ha="left",
                      fontsize=7, fontweight="bold", color="#1a7a3c")
        else:
            ax1.text(width - offset, y, label, va="center", ha="right",
                      fontsize=7, fontweight="bold", color="#a82c1a")

    ax2 = axes[1]
    up = int((df["PctChange"] > 0).sum())
    down = int((df["PctChange"] < 0).sum())
    flat = int((df["PctChange"] == 0).sum())
    sizes = [up, down, flat]
    labels = [f"Up ({up})", f"Down ({down})", f"Flat ({flat})"]
    colors_pie = ["#2ecc71", "#e74c3c", "#95a5a6"]
    nonzero = [(s, l, c) for s, l, c in zip(sizes, labels, colors_pie) if s > 0]
    if nonzero:
        sizes, labels, colors_pie = zip(*nonzero)
        ax2.pie(sizes, labels=labels, colors=colors_pie, autopct="%1.0f%%",
                startangle=90, wedgeprops={"width": 0.4})
    ax2.set_title("Market Breadth", fontsize=13, fontweight="bold")

    plt.tight_layout()
    return fig


def main():
    st.set_page_config(page_title="NSE F&O Premarket Tracker", layout="wide")
    st.title("NSE F&O Universe — Premarket Tracker")
    st.caption("Source: nseindia.com/market-data/pre-open-market-cotation")

    live, note, now = is_preopen_session_live()
    if live:
        st.success(f"🟢 {note}  (IST time: {now.strftime('%H:%M:%S')})")
    else:
        st.warning(f"🟠 {note}  (IST time: {now.strftime('%H:%M:%S')})")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("Refresh data"):
            fetch_preopen_data.clear()
    with col_b:
        top_n = st.slider("Show top N symbols by absolute move in chart",
                           min_value=10, max_value=len(SECURITIES_FO), value=40, step=5)

    try:
        with st.spinner("Fetching premarket data from NSE..."):
            raw = fetch_preopen_data(key="FNO")
    except Exception as exc:
        st.error(
            "Could not fetch premarket data from NSE. This usually means "
            "NSE is blocking/throttling requests from this server's IP.\n\n"
            f"Details: {exc}"
        )
        return

    df = parse_preopen(raw)
    df, missing = filter_to_fo_universe(df)
    df = df.dropna(subset=["PctChange"]).sort_values("PctChange", ascending=False)
    df = add_trade_signals(df)

    if missing:
        st.info(
            f"{len(missing)} symbol(s) in your F&O universe had no premarket "
            f"data returned (may be a listing/spelling issue): " + ", ".join(missing)
        )

    if df.empty:
        st.warning("No premarket data available right now.")
        return

    # --- Summary metrics ---
    up = int((df["PctChange"] > 0).sum())
    down = int((df["PctChange"] < 0).sum())
    flat = int((df["PctChange"] == 0).sum())
    total = len(df)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total stocks", total)
    m2.metric("Up", up, f"{up/total*100:.1f}%" if total else "0%")
    m3.metric("Down", down, f"{-down/total*100:.1f}%" if total else "0%")
    m4.metric("Flat", flat)

    # --- Must-check watchlist ---
    st.subheader("Must-Check Watchlist")
    st.caption(
        "Ranked by move size + order-imbalance conviction. Descriptive only — "
        "not a buy/sell recommendation. Always confirm live price/quantity "
        "before placing an order."
    )
    watch_cols = ["Symbol", "IEP", "PctChange", "OrderImbalance", "BuySellRatio",
                  "DistFrom52WHighPct", "DistFrom52WLowPct", "NearCircuitFlag", "WatchScore"]
    watch_cols = [c for c in watch_cols if c in df.columns]
    watchlist = df.dropna(subset=["WatchScore"]).sort_values("WatchScore", ascending=False).head(15)
    st.dataframe(watchlist[watch_cols].round(2), use_container_width=True)

    circuit_hits = df[df["NearCircuitFlag"] == True]
    if len(circuit_hits) > 0:
        st.warning(
            f"{len(circuit_hits)} stock(s) showing premarket move ≥9% — "
            "verify circuit limit before trading:"
        )
        st.dataframe(circuit_hits[["Symbol", "PctChange"]].round(2), use_container_width=True)

    # --- Gainers / Losers side by side ---
    st.subheader("Top Gainers / Top Losers")
    TOP_N_TABLE = 30
    gainers = df[df["PctChange"] > 0].sort_values("PctChange", ascending=False).head(TOP_N_TABLE)
    losers = df[df["PctChange"] < 0].sort_values("PctChange", ascending=True).head(TOP_N_TABLE)

    g_col, l_col = st.columns(2)
    with g_col:
        st.markdown(f"**🟢 Top Gainers ({len(gainers)} of {up})**")
        st.dataframe(gainers[["Symbol", "PrevClose", "IEP", "PctChange"]].round(2),
                     use_container_width=True, height=350)
    with l_col:
        st.markdown(f"**🔴 Top Losers ({len(losers)} of {down})**")
        st.dataframe(losers[["Symbol", "PrevClose", "IEP", "PctChange"]].round(2),
                     use_container_width=True, height=350)

    # --- Full detail table ---
    with st.expander("Full premarket detail table (all stocks, all fields)"):
        st.dataframe(df.round(2), use_container_width=True)

    # --- Charts ---
    st.subheader("Graphical View")
    fig = plot_premarket(df, top_n=top_n)
    st.pyplot(fig)


if __name__ == "__main__":
    main()
