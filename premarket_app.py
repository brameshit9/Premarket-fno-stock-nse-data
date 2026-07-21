import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from datetime import datetime

UP_COLOR = '#2ecc71'
DOWN_COLOR = '#e74c3c'
BG_COLOR = '#ffffff'
TEXT_COLOR = '#1a1a1a'

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


def fetch_preopen(session, key="FO"):
    # key options on NSE's pre-open API mirror the "Category" dropdown on the site:
    #   "ALL"  -> All securities
    #   "FO"   -> Securities in F&O  (matches your screenshot)
    #   "NIFTY", "BANKNIFTY", etc. -> specific index constituents
    url = f"https://www.nseindia.com/api/market-data-pre-open?key={key}"
    try:
        r = session.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"Fetch failed ({e}), retrying with a fresh session...")
        session.cookies.clear()
        session.get("https://www.nseindia.com", timeout=5)
        r = session.get(url, timeout=5)
        r.raise_for_status()
        return r.json()


def to_dataframe(raw, symbols):
    rows = [
        {
            "symbol": item["metadata"]["symbol"],
            "price": item["metadata"]["lastPrice"],
            "change": item["metadata"]["pChange"],
        }
        for item in raw["data"]
        if item["metadata"]["symbol"] in symbols
    ]
    df = pd.DataFrame(rows)
    return df.sort_values("change", ascending=True).reset_index(drop=True)


CSV_PATH = "preopen_fo_full.csv"
FULL_CHART_PATH = "preopen_fo_full_chart.png"
TOP_N = 20  # top N gainers + top N losers shown in the interactive window
ROW_HEIGHT_IN = 0.20  # inches per bar in the full-list PNG (keeps labels legible)


def save_full_chart(df_full):
    """Render every symbol as a tall bar chart and save to PNG.
    A live matplotlib window can't scroll, so all 210 rows are rendered
    to an image tall enough that each label has room; open the PNG and
    zoom/scroll it to read the full list.
    """
    n = len(df_full)
    height = max(6, n * ROW_HEIGHT_IN)
    fig2, ax2 = plt.subplots(figsize=(10, height))
    fig2.patch.set_facecolor(BG_COLOR)

    colors = [UP_COLOR if c >= 0 else DOWN_COLOR for c in df_full["change"]]
    ax2.barh(df_full["symbol"], df_full["change"], color=colors)
    ax2.set_facecolor(BG_COLOR)
    ax2.set_xlabel("% Change", color=TEXT_COLOR)
    ax2.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax2.set_title(
        f"All {n} Securities in F&O — Pre-Open % Change — {datetime.now():%H:%M:%S}",
        color=TEXT_COLOR,
    )
    ax2.axvline(0, color=TEXT_COLOR, linewidth=0.8)
    ax2.margins(y=0.002)  # tight vertical spacing between the many bars
    fig2.tight_layout()
    fig2.savefig(FULL_CHART_PATH, dpi=150, facecolor=BG_COLOR)
    plt.close(fig2)


def run_with_refresh_button():
    session = get_session()
    # Tall-ish window; readable bar chart with ~2*TOP_N rows instead of all 210.
    fig, ax1 = plt.subplots(figsize=(12, 11))
    fig.patch.set_facecolor(BG_COLOR)
    plt.subplots_adjust(bottom=0.06, top=0.90, left=0.22, right=0.95)

    def render(event=None):
        ax1.clear()
        try:
            raw = fetch_preopen(session)
            df_full = to_dataframe(raw, SECURITIES_FO)
        except Exception as e:
            ax1.text(
                0.5, 0.5, f"Fetch failed:\n{e}",
                ha="center", va="center",
                color=DOWN_COLOR, transform=ax1.transAxes,
            )
            fig.canvas.draw_idle()
            return

        # Full 210-row snapshot saved every refresh: CSV for the raw numbers,
        # plus a tall PNG chart since a single on-screen chart can't legibly
        # show all 210 symbols at once.
        df_full.to_csv(CSV_PATH, index=False)
        save_full_chart(df_full)

        # Interactive window: bottom N losers + top N gainers only (still
        # sorted ascending so reds are at the bottom, greens at the top).
        losers = df_full.head(TOP_N)
        gainers = df_full.tail(TOP_N)
        df = pd.concat([losers, gainers]).drop_duplicates(subset="symbol")
        df = df.sort_values("change", ascending=True).reset_index(drop=True)

        colors = [UP_COLOR if c >= 0 else DOWN_COLOR for c in df["change"]]
        ax1.barh(df["symbol"], df["change"], color=colors)
        ax1.set_facecolor(BG_COLOR)
        ax1.set_xlabel("% Change", color=TEXT_COLOR)
        ax1.tick_params(colors=TEXT_COLOR, labelsize=9)
        ax1.set_title(
            f"Top {TOP_N} Gainers & Losers — Securities in F&O — "
            f"{datetime.now():%H:%M:%S}\n"
            f"(full {len(df_full)}-symbol list: {CSV_PATH} / {FULL_CHART_PATH})",
            color=TEXT_COLOR, fontsize=10,
        )
        ax1.axvline(0, color=TEXT_COLOR, linewidth=0.8)
        fig.canvas.draw_idle()

    # Small dedicated axes in the top-right corner for the refresh button
    button_ax = fig.add_axes([0.82, 0.93, 0.12, 0.05])
    btn = Button(button_ax, "Refresh")
    btn.on_clicked(render)

    render()      # initial draw
    plt.show()    # keep window open


if __name__ == "__main__":
    run_with_refresh_button()
