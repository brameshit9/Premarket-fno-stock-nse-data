# =========================================================
# NSE F&O Universe Premarket Tracker — Streamlit App
# =========================================================
# NSE pre-open session is live ~9:00–9:15 AM IST on trading days.
# Outside that window the API returns stale/previous-session data.
#
# NSE blocks many datacenter IPs. If deployed on Streamlit Cloud
# and you get repeated 401/403/blocked responses, that's NSE's
# bot-check rejecting the host IP — try a different host, or run
# locally, or use a proxy you control.
#
# Run locally:
#   pip install -r requirements.txt
#   streamlit run app.py
# =========================================================

import time
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytz
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# Your F&O security universe
# ---------------------------------------------------------
SECURITIES_FO = [
    "DIXON", "PATANJALI", "BHEL", "PAYTM", "ADANIPOWER", "M&M", "ANGELONE", "ICICIPRULI", "VMM", "KAYNES",
    "FORCEMOT", "JUBLFOOD", "PNBHOUSING", "IDEA", "BIOCON", "DALBHARAT", "MPHASIS", "NAM-INDIA", "BPCL", "KEI",
    "TCS", "AMBER", "PREMIERENE", "SIEMENS", "ASTRAL", "SWIGGY", "POLICYBZR", "GLENMARK", "EXIDEIND",
    "ADANIENSOL", "HINDPETRO", "DIVISLAB", "AMBUJACEM", "CGPOWER", "PAGEIND", "ADANIGREEN",
    "POWERINDIA", "BDL", "KPITTECH", "GODREJCP", "NUVAMA", "DABUR", "FORTIS", "LUPIN",
    "SOLARINDS", "CROMPTON", "GVT&D", "HEROMOTOCO", "NAUKRI", "INDIANB", "SHREECEM",
    "PFC", "HINDZINC", "RECLTD", "BSE", "COCHINSHIP", "KFINTECH", "NATIONALUM", "RVNL", "OFSS",
    "RADICO", "CHOLAFIN", "JSWENERGY", "SAIL", "WAAREEENER", "TIINDIA", "GODFRYPHLP", "SUZLON", "LICHSGFIN",
    "DELHIVERY", "CDSL", "MOTILALOFS", "LODHA", "MANKIND", "MOTHERSON", "NYKAA", "TVSMOTOR", "VBL",
    "ZYDUSLIFE", "MFSL", "OBEROIRLTY", "PRESTIGE", "PIIND", "GMRAIRPORT", "PGEL", "COFORGE", "MCX",
    "SHRIRAMFIN", "VEDL", "INDUSTOWER", "TORNTPHARM", "CUMMINSIND", "GODREJPROP", "HAVELLS", "BOSCHLTD",
    "NMDC", "ASHOKLEY", "INOXWIND", "RBLBANK", "UNOMINDA", "COLPAL", "BHARATFORG", "PHOENIXLTD", "ABB",
    "IREDA", "BANKINDIA", "BLUESTARCO", "SRF", "TATAPOWER", "VOLTAS", "MAZDOCK", "DMART", "SUPREMEIND", "ALKEM",
    "SONACOMS", "AUROPHARMA", "BAJAJHLDNG", "HAL", "IRFC", "LAURUSLABS", "MANAPPURAM", "MARICO", "MUTHOOTFIN", "NHPC",
    "PERSISTENT", "PETRONET", "PIDILITIND", "SBICARD", "UNITDSPR", "APLAPOLLO", "TATAELXSI", "INDHOTEL", "JINDALSTEL",
    "UPL", "HYUNDAI", "ABCAPITAL", "BRITANNIA", "GAIL", "CONCOR", "CAMS", "HDFCAMC", "POLYCAB", "OIL", "KALYANKJIL",
    "ICICIGI",
]
# NOTE: "TIINDIA" corrected from "THINDIA" (Tube Investments of India's NSE
# symbol is TIINDIA; THINDIA does not exist and would just show up in the
# "missing" list every run). If TIINDIA wasn't what you meant, edit the
# list above.

PREOPEN_COLUMNS = [
    "Symbol", "PrevClose", "IEP", "Change", "PctChange", "YearHigh", "YearLow",
    "FinalQuantity", "TotalTradedVolume", "TotalTurnover", "MarketCap",
    "TotalBuyQuantity", "TotalSellQuantity",
]

IST = pytz.timezone("Asia/Kolkata")


# ---------------------------------------------------------
# NSE session / fetch / parse helpers
# ---------------------------------------------------------
@st.cache_resource(ttl=300)  # refresh cookies every 5 minutes
def get_nse_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/market-data/pre-open-market-cotation",
    })
    session.get("https://www.nseindia.com", timeout=10)
    time.sleep(1)
    return session


def fetch_preopen_data(session, key="FO", retries=3):
    url = f"https://www.nseindia.com/api/market-data-pre-open?key={key}"
    last_json = None
    warnings = []
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=10)
        except requests.RequestException as e:
            warnings.append(f"Attempt {attempt + 1}: request error {e}")
            time.sleep(2)
            continue

        if resp.status_code == 200:
            try:
                last_json = resp.json()
            except ValueError:
                warnings.append(
                    f"Attempt {attempt + 1}: got 200 but non-JSON response "
                    f"(likely bot-check page)."
                )
                time.sleep(2)
                get_nse_session.clear()
                session = get_nse_session()
                continue
            if last_json.get("data"):
                return last_json, warnings
            warnings.append(
                f"Attempt {attempt + 1}: response had no 'data' rows for key={key!r}."
            )
        else:
            warnings.append(f"Attempt {attempt + 1}: HTTP {resp.status_code}")
        time.sleep(2)
        get_nse_session.clear()
        session = get_nse_session()

    return last_json, warnings


def parse_preopen(data):
    rows = []
    if data:
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
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=PREOPEN_COLUMNS)


def filter_to_fo_universe(df, universe=SECURITIES_FO):
    if df.empty or "Symbol" not in df.columns:
        return pd.DataFrame(columns=PREOPEN_COLUMNS), sorted(set(universe))

    universe_set = set(universe)
    filtered = df[df["Symbol"].isin(universe_set)].copy()
    found = set(filtered["Symbol"])
    missing = sorted(universe_set - found)
    return filtered, missing


def add_trade_signals(df):
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


def is_preopen_session_live():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False, "Weekend — market closed, data is stale."
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end = now.replace(hour=9, minute=15, second=0, microsecond=0)
    if start <= now <= end:
        return True, "Live pre-open window."
    return False, "Outside 9:00-9:15 AM IST window — this is a STALE/previous-session snapshot."


# ---------------------------------------------------------
# Plotly charts
# ---------------------------------------------------------
def plot_bar_chart(df):
    plot_df = df.dropna(subset=["PctChange"]).sort_values("PctChange", ascending=True)
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in plot_df["PctChange"]]

    text_labels = []
    for _, row in plot_df.iterrows():
        pct_txt = f"{row['PctChange']:+.2f}%"
        if pd.notna(row.get("Change")):
            text_labels.append(f"{pct_txt} (₹{row['Change']:+.2f})")
        else:
            text_labels.append(pct_txt)

    fig = go.Figure(
        go.Bar(
            x=plot_df["PctChange"],
            y=plot_df["Symbol"],
            orientation="h",
            marker_color=colors,
            text=text_labels,
            textposition="outside",
        )
    )
    fig.update_layout(
        title="F&O Universe Premarket Movement — All Stocks",
        xaxis_title="% Change (Premarket vs Prev Close)",
        height=max(500, len(plot_df) * 22),
        margin=dict(l=10, r=60, t=50, b=10),
        showlegend=False,
    )
    fig.add_vline(x=0, line_width=1, line_color="black")
    return fig


def plot_donut(df):
    up = int((df["PctChange"] > 0).sum())
    down = int((df["PctChange"] < 0).sum())
    flat = int((df["PctChange"] == 0).sum())
    labels, values, colors = [], [], []
    for l, v, c in [("Up", up, "#2ecc71"), ("Down", down, "#e74c3c"), ("Flat", flat, "#95a5a6")]:
        if v > 0:
            labels.append(f"{l} ({v})")
            values.append(v)
            colors.append(c)
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.5, marker_colors=colors))
    fig.update_layout(title="Market Breadth", height=400, margin=dict(l=10, r=10, t=50, b=10))
    return fig


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.set_page_config(page_title="NSE F&O Premarket Tracker", layout="wide")
st.title("📈 NSE F&O Universe Premarket Tracker")

with st.sidebar:
    st.header("Settings")
    refresh_sec = st.number_input("Auto-refresh interval (seconds)", min_value=10, max_value=300, value=30, step=5)
    top_n = st.slider("Top N gainers/losers to show", min_value=5, max_value=50, value=30)
    watch_n = st.slider("Watchlist size", min_value=5, max_value=30, value=15)
    manual_refresh = st.button("🔄 Refresh now")

# Auto-refresh every N seconds
st_autorefresh(interval=refresh_sec * 1000, key="autorefresh")

live, live_note = is_preopen_session_live()
if not live:
    st.warning(f"⚠️ {live_note}")

session = get_nse_session()
with st.spinner("Fetching NSE pre-open data..."):
    raw, warnings = fetch_preopen_data(session, key="FO")

for w in warnings:
    st.caption(f"⚠️ {w}")

df_raw = parse_preopen(raw)
df, missing = filter_to_fo_universe(df_raw)

if missing:
    with st.expander(f"⚠️ {len(missing)} symbol(s) in your list had no data returned"):
        st.write(", ".join(missing))

df = df.dropna(subset=["PctChange"]).sort_values("PctChange", ascending=False)

if df.empty:
    st.error(
        "No usable pre-open data returned for your watchlist. Most likely you're "
        "outside the 9:00–9:15 AM IST pre-open window, or the request was bot-blocked "
        "by NSE. This page will keep retrying on the next auto-refresh."
    )
    st.stop()

df = add_trade_signals(df)

now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
up = int((df["PctChange"] > 0).sum())
down = int((df["PctChange"] < 0).sum())
flat = int((df["PctChange"] == 0).sum())
total = len(df)

st.caption(f"Snapshot: {now_ist}  •  Auto-refreshing every {refresh_sec}s")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total tracked", total)
c2.metric("Up", up, f"{up/total*100:.1f}%" if total else None)
c3.metric("Down", down, f"{down/total*100:.1f}%" if total else None, delta_color="inverse")
c4.metric("Flat", flat)

col_chart, col_donut = st.columns([3, 1])
with col_chart:
    st.plotly_chart(plot_bar_chart(df), use_container_width=True)
with col_donut:
    st.plotly_chart(plot_donut(df), use_container_width=True)

st.subheader("🔎 Must-check watchlist")
st.caption("Ranked by move size + order-imbalance conviction. Descriptive only — always confirm live price/quantity before placing an order.")
watch_cols = ["Symbol", "IEP", "PctChange", "OrderImbalance", "BuySellRatio",
              "DistFrom52WHighPct", "DistFrom52WLowPct", "NearCircuitFlag", "WatchScore"]
watch_cols = [c for c in watch_cols if c in df.columns]
watchlist = df.dropna(subset=["WatchScore"]).sort_values("WatchScore", ascending=False).head(watch_n)
st.dataframe(watchlist[watch_cols].round(2), use_container_width=True, hide_index=True)

circuit_hits = df[df["NearCircuitFlag"] == True]  # noqa: E712
if len(circuit_hits) > 0:
    st.warning(f"{len(circuit_hits)} stock(s) showing premarket move ≥9% — verify circuit limit before trading.")
    st.dataframe(circuit_hits[["Symbol", "PctChange"]].round(2), use_container_width=True, hide_index=True)

tab1, tab2, tab3 = st.tabs(["📈 Gainers / 📉 Losers", "📋 Full data", "ℹ️ About"])

with tab1:
    gcol, lcol = st.columns(2)
    gainers = df[df["PctChange"] > 0].sort_values("PctChange", ascending=False).head(top_n)
    losers = df[df["PctChange"] < 0].sort_values("PctChange", ascending=True).head(top_n)
    with gcol:
        st.markdown(f"**Up stocks — showing {len(gainers)} of {up}**")
        st.dataframe(gainers[["Symbol", "PrevClose", "IEP", "PctChange"]].round(2),
                     use_container_width=True, hide_index=True)
    with lcol:
        st.markdown(f"**Down stocks — showing {len(losers)} of {down}**")
        st.dataframe(losers[["Symbol", "PrevClose", "IEP", "PctChange"]].round(2),
                     use_container_width=True, hide_index=True)

with tab2:
    sort_col = st.selectbox("Sort by", df.columns.tolist(), index=df.columns.get_loc("PctChange"))
    sort_desc = st.checkbox("Descending", value=True)
    st.dataframe(df.sort_values(sort_col, ascending=not sort_desc), use_container_width=True, hide_index=True)

with tab3:
    st.markdown(
        """
        - Data source: NSE's public pre-open market API (`market-data-pre-open?key=FO`).
        - Live only during NSE's pre-open window, roughly **9:00–9:15 AM IST** on trading days.
          Outside that window the API keeps responding but with a stale/previous snapshot.
        - NSE blocks many datacenter/cloud IPs. If this app is deployed on a cloud host and
          keeps failing to fetch data, that's NSE's bot-check rejecting the host's IP —
          try running locally, or route requests through infrastructure you control.
        - This dashboard is descriptive only, not investment advice. Always verify live
          price and quantity before placing any order.
        """
    )
