import time
import streamlit as st
import requests
import numpy as np
import pandas as pd
import pytz
import plotly.graph_objects as go
from datetime import datetime

BG = '#F5F7FA'
CARD = '#FFFFFF'
BORDER = '#E7EBF0'
PRIMARY = '#4F46E5'
UP = '#16A34A'
DOWN = '#DC2626'
UP_SOFT = '#DCFCE7'
DOWN_SOFT = '#FEE2E2'
TEXT = '#1E293B'
MUTED = '#64748B'
WARN = '#D97706'
WARN_SOFT = '#FEF3C7'

Securities_FNO = [
    "DIXON", "PATANJALI", "BHEL", "PAYTM", "ADANIPOWER", "M&M", "ANGELONE", "ICICIPRULI", "VMM", "KAYNES",
    "FORCEMOT", "JUBLFOOD", "PNBHOUSING", "IDEA", "BIOCON", "DALBHARAT", "MPHASIS", "NAM-INDIA", "BPCL", "KEI",
    "TCS", "AMBER", "PREMIERENE", "SIEMENS", "ASTRAL", "SWIGGY", "POLICYBZR", "GLENMARK", "EXIDEIND",
    "ADANIENSOL", "HINDPETRO", "DIVISLAB", "AMBUJACEM", "CGPOWER", "PAGEIND", "ADANIGREEN",
    "POWERINDIA", "BDL", "KPITTECH", "GODREJCP", "NUVAMA", "DABUR", "FORTIS", "LUPIN",
    "SOLARINDS", "CROMPTON", "GVT&D", "HEROMOTOCO", "NAUKRI", "INDIANB", "SHREECEM",
    "PFC", "HINDZINC", "RECLTD", "BSE", "COCHINSHIP", "KFINTECH", "NATIONALUM", "RVNL", "OFSS",
    "RADICO", "CHOLAFIN", "JSWENERGY", "SAIL", "WAAREEENER", "THINDIA", "GODFRYPHLP", "SUZLON", "LICHSGFIN",
    "DELHIVERY", "CDSL", "MOTILALOFS", "LODHA", "MANKIND", "MOTHERSON", "NYKAA", "TVSMOTOR", "VBL",
    "ZYDUSLIFE", "MFSL", "OBEROIRLTY", "PRESTIGE", "PIIND", "GMRAIRPORT", "PGEL", "COFORGE", "MCX",
    "SHRIRAMFIN", "VEDL", "INDUSTOWER", "TORNTPHARM", "CUMMINSIND", "GODREJPROP", "HAVELLS", "BOSCHLTD",
    "NMDC", "ASHOKLEY", "INOXWIND", "RBLBANK", "UNOMINDA", "COLPAL", "BHARATFORG", "PHOENIXLTD", "ABB",
    "IREDA", "BANKINDIA", "BLUESTARCO", "SRF", "TATAPOWER", "VOLTAS", "MAZDOCK", "DMART", "SUPREMEIND", "ALKEM",
    "SONACOMS", "AUROPHARMA", "BAJAJHLDNG", "HAL", "IRFC", "LAURUSLABS", "MANAPPURAM", "MARICO", "MUTHOOTFIN", "NHPC",
    "PERSISTENT", "PETRONET", "PIDILITIND", "SBICARD", "UNITDSPR", "APLAPOLLO", "TATAELXSI", "INDHOTEL", "JINDALSTEL",
    "UPL", "HYUNDAI", "ABCAPITAL", "BRITANNIA", "GAIL", "CONCOR", "CAMS", "HDFCAMC", "POLYCAB", "OIL", "KALYANKJIL", "ICICIGI"
]
TOTAL_SECURITIES = len(Securities_FNO)


@st.cache_resource
def get_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/market-data/pre-open-market-cotd",
    })
    s.get("https://www.nseindia.com", timeout=5)
    return s


def fetch_preopen(session):
    url = "https://www.nseindia.com/api/market-data-pre-open?key=ALL"
    try:
        r = session.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        session.cookies.clear()
        session.get("https://www.nseindia.com", timeout=5)
        r = session.get(url, timeout=5)
        r.raise_for_status()
        return r.json()


def to_dataframe(raw, symbols):
    rows = []
    for item in raw.get("data", []):
        meta = item.get("metadata", {})
        pre = item.get("detail", {}).get("preOpenMarket", {})
        symbol = meta.get("symbol")
        if symbol not in symbols:
            continue
        rows.append(
            {
                "symbol": symbol,
                "price": meta.get("lastPrice"),
                "change": meta.get("pChange"),
                "prevClose": meta.get("previousClose"),
                "iep": pre.get("IEP", meta.get("iep")),
                "yearHigh": meta.get("yearHigh"),
                "yearLow": meta.get("yearLow"),
                "buyQty": pre.get("totalBuyQuantity"),
                "sellQty": pre.get("totalSellQuantity"),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    buy = df["buyQty"].fillna(0)
    sell = df["sellQty"].fillna(0)
    total_qty = buy + sell
    df["orderImbalance"] = np.where(total_qty > 0, (buy - sell) / total_qty, np.nan)
    df["nearCircuit"] = df["change"].abs() >= 9
    df["watchScore"] = df["change"].abs() * (1 + df["orderImbalance"].abs().fillna(0))

    return df.sort_values("change", ascending=True).reset_index(drop=True)


def is_preopen_session_live():
    """Check whether we're inside NSE's 9:00-9:15 AM IST pre-open window."""
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False, "Weekend — market closed, data is stale.", now
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end = now.replace(hour=9, minute=15, second=0, microsecond=0)
    if start <= now <= end:
        return True, "Live pre-open window.", now
    return (
        False,
        "Outside 9:00–9:15 AM IST window — this is a STALE/previous-session snapshot, not live premarket.",
        now,
    )


st.set_page_config(page_title="Securities_FNO Pre-Market Dashboard", layout="wide", page_icon="📊")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

.stApp {{
    background-color: {BG};
}}

#MainMenu, footer, header {{visibility: hidden;}}

.block-container {{
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}}

.dash-title {{
    font-size: 28px;
    font-weight: 800;
    color: {TEXT};
    margin-bottom: 2px;
}}
.dash-sub {{
    font-size: 14px;
    color: {MUTED};
    font-weight: 500;
}}
.live-dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: {UP};
    margin-right: 6px;
}}

.kpi-card {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 18px 20px;
    height: 100%;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04), 0 1px 2px rgba(16, 24, 40, 0.06);
}}
.kpi-label {{
    font-size: 12px;
    color: {MUTED};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}}
.kpi-value {{
    font-size: 24px;
    font-weight: 700;
    color: {TEXT};
}}
.kpi-value.up {{ color: {UP}; }}
.kpi-value.down {{ color: {DOWN}; }}
.kpi-badge {{
    display: inline-block;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    margin-top: 8px;
}}
.kpi-badge.up {{ background-color: {UP_SOFT}; color: {UP}; }}
.kpi-badge.down {{ background-color: {DOWN_SOFT}; color: {DOWN}; }}

.chart-panel {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 24px;
    margin-top: 20px;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04), 0 1px 2px rgba(16, 24, 40, 0.06);
}}
.panel-heading {{
    font-size: 15px;
    font-weight: 700;
    color: {TEXT};
    margin-bottom: 16px;
}}

div.stButton > button {{
    background-color: {PRIMARY};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    padding: 8px 22px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);
}}
div.stButton > button:hover {{
    background-color: #4338CA;
    color: #FFFFFF;
}}

.footer-note {{
    font-size: 12px;
    color: {MUTED};
    margin-top: 18px;
}}

.stale-banner {{
    background-color: {WARN_SOFT};
    border: 1px solid {WARN};
    color: #92400E;
    border-radius: 12px;
    padding: 12px 18px;
    font-size: 14px;
    font-weight: 500;
    margin: 8px 0 20px 0;
}}

section[data-testid="stSidebar"] .stMarkdown h3 {{
    color: {TEXT};
}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data():
    session = get_session()
    raw = fetch_preopen(session)
    return to_dataframe(raw, Securities_FNO)


def make_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Readable horizontal bar chart that scales with the number of stocks.

    Instead of cramming a static-size matplotlib image with 140+ overlapping
    labels, this uses Plotly so the chart height grows with the row count,
    labels stay legible, and hover tooltips replace the inline text that was
    overlapping before.
    """
    colors = [UP if c >= 0 else DOWN for c in df["change"]]

    fig = go.Figure(
        go.Bar(
            x=df["change"],
            y=df["symbol"],
            orientation="h",
            marker_color=colors,
            hovertemplate="<b>%{y}</b><br>%{x:+.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(700, 26 * len(df)),   # ~26px per row so 144 stocks stay readable
        margin=dict(l=10, r=30, t=10, b=30),
        plot_bgcolor=CARD,
        paper_bgcolor=CARD,
        font=dict(family="Inter, sans-serif", color=TEXT, size=12),
        xaxis=dict(
            title="% Change",
            gridcolor=BORDER,
            zeroline=True,
            zerolinecolor=MUTED,
            zerolinewidth=1,
        ),
        yaxis=dict(
            tickfont=dict(size=11),
            automargin=True,
        ),
        bargap=0.25,
        showlegend=False,
    )
    return fig


with st.sidebar:
    st.markdown("### Settings")
    top_n = st.slider("Top N gainers/losers to show", 5, 50, 30)
    watch_n = st.slider("Watchlist size", 5, 30, 15)
    auto_refresh = st.checkbox("Auto-refresh every 30s (during 9:00–9:15 AM IST)")
    manual_refresh = st.button("🔄 Refresh now", use_container_width=True)

if manual_refresh:
    st.cache_data.clear()

st.markdown('<div class="dash-title">Securities_FNO Pre-Market Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-sub">NSE India &nbsp;·&nbsp; Pre-Open Session Overview</div>', unsafe_allow_html=True)

live, note, now_ist = is_preopen_session_live()
snapshot_time = now_ist.strftime("%Y-%m-%d %H:%M:%S")
st.markdown(
    f'<div class="dash-sub">Snapshot time: {snapshot_time} IST</div>',
    unsafe_allow_html=True
)
if not live:
    st.markdown(f'<div class="stale-banner">⚠️ {note}</div>', unsafe_allow_html=True)

try:
    df = load_data()
except Exception as e:
    st.markdown(f"""
    <div class="chart-panel">
        <div class="panel-heading" style="color:{DOWN};">Unable to fetch data</div>
        <div style="color:{TEXT};">{e}</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if df.empty:
    st.markdown(f"""
    <div class="chart-panel">
        <div class="panel-heading" style="color:{TEXT};">No premarket data returned</div>
        <div style="color:{MUTED};">Try again closer to 9:00–9:15 AM IST on a trading day.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

top_loser = df.iloc[0]
top_gainer = df.iloc[-1]
up_count = int((df["change"] >= 0).sum())
down_count = int((df["change"] < 0).sum())
ratio = up_count / down_count if down_count > 0 else float('inf')

st.markdown(
    f'<div class="dash-sub"><span class="live-dot"></span>Last updated {datetime.now().strftime("%d %b %Y, %H:%M:%S")} IST</div>',
    unsafe_allow_html=True
)
st.write("")

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Advancers</div>
        <div class="kpi-value up">{up_count}</div>
        <div class="kpi-badge up">of {TOTAL_SECURITIES} stocks</div></div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Decliners</div>
        <div class="kpi-value down">{down_count}</div>
        <div class="kpi-badge down">of {TOTAL_SECURITIES} stocks</div></div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">A/D Ratio</div>
        <div class="kpi-value">{ratio:.2f}</div>
        <div class="kpi-badge up" style="background-color:#EEF2FF; color:{PRIMARY};">advance / decline</div></div>""",
        unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Top Gainer</div>
        <div class="kpi-value up">{top_gainer['symbol']}</div>
        <div class="kpi-badge up">+{top_gainer['change']:.2f}%</div></div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Top Loser</div>
        <div class="kpi-value down">{top_loser['symbol']}</div>
        <div class="kpi-badge down">{top_loser['change']:.2f}%</div></div>""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-heading">Premarket Movement — % Change</div>', unsafe_allow_html=True)
    st.plotly_chart(make_bar_chart(df), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-heading">Market Breadth</div>', unsafe_allow_html=True)
    donut = go.Figure(
        go.Pie(
            values=[up_count, down_count],
            labels=[f"Up ({up_count})", f"Down ({down_count})"],
            hole=0.55,
            marker_colors=[UP, DOWN],
            textinfo="percent",
            textfont=dict(color="#FFFFFF", size=13),
            hovertemplate="<b>%{label}</b><br>%{value} stocks<extra></extra>",
        )
    )
    donut.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=CARD,
        paper_bgcolor=CARD,
        font=dict(family="Inter, sans-serif", color=TEXT, size=12),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
    )
    st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
st.markdown(
    f'<div class="panel-heading">🎯 Must-check Watchlist (Top {watch_n} by move + order-imbalance conviction)</div>',
    unsafe_allow_html=True,
)
watch_cols = ["symbol", "iep", "change", "orderImbalance", "nearCircuit", "watchScore"]
watch_cols = [c for c in watch_cols if c in df.columns]
watchlist_df = df.dropna(subset=["watchScore"]).sort_values("watchScore", ascending=False).head(watch_n)
st.dataframe(watchlist_df[watch_cols].round(2), use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

circuit_hits = df[df["nearCircuit"] == True]  # noqa: E712
if len(circuit_hits) > 0:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="panel-heading" style="color:{WARN};">⚠️ {len(circuit_hits)} stock(s) showing premarket move ≥9% — verify circuit limit before trading</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(circuit_hits[["symbol", "change"]].round(2), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

gcol, lcol = st.columns(2)
with gcol:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    gainers = df[df["change"] > 0].sort_values("change", ascending=False).head(top_n)
    st.markdown(
        f'<div class="panel-heading" style="color:{UP};">🟢 Top Gainers ({min(top_n, up_count)} of {up_count})</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(gainers[["symbol", "prevClose", "iep", "change"]].round(2), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
with lcol:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    losers = df[df["change"] < 0].sort_values("change", ascending=True).head(top_n)
    st.markdown(
        f'<div class="panel-heading" style="color:{DOWN};">🔴 Top Losers ({min(top_n, down_count)} of {down_count})</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(losers[["symbol", "prevClose", "iep", "change"]].round(2), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

with st.expander("📋 Full F&O premarket data — every stock, every field"):
    st.dataframe(df.sort_values("change", ascending=False), use_container_width=True, hide_index=True)

st.markdown(
    '<div class="footer-note">Data source: NSE India &nbsp;·&nbsp; Auto-refreshes every 60 seconds &nbsp;·&nbsp; '
    'Click Refresh for an immediate update</div>',
    unsafe_allow_html=True
)

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
