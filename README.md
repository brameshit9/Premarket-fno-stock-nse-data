# NSE F&O Universe Premarket Tracker

A Streamlit dashboard that tracks NSE's pre-open market data for a custom
watchlist of F&O securities, auto-refreshing every 30 seconds.

## Features
- Pulls NSE's `market-data-pre-open?key=FO` bucket and filters to your own
  `SECURITIES_FO` symbol list (edit the list in `app.py`).
- Auto-refreshes every 30 seconds (configurable in the sidebar).
- Bar chart of % change per stock + market-breadth donut chart.
- "Must-check" watchlist ranked by move size + order-imbalance conviction.
- Near-circuit flag (≥9% premarket move) callout.
- Gainers / losers tables and a full sortable data table.

## ⚠️ Important limitations
- **Live only ~9:00–9:15 AM IST** on NSE trading days. Outside that window
  the API still responds but with stale/previous-session data — the app
  will show a warning banner.
- **NSE blocks many datacenter/cloud IPs.** If you deploy this on Streamlit
  Community Cloud (or any cloud host) and it keeps failing to fetch data,
  that's NSE's bot-check rejecting the host's IP, not a bug in the app.
  Running it locally on a residential IP is the most reliable option.
- This dashboard is **descriptive only** — not investment advice. Always
  verify live price and quantity before placing an order.

## Setup

```bash
git clone <your-repo-url>
cd nse-premarket-tracker
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploying to Streamlit Community Cloud
1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo,
   and set the main file to `app.py`.
3. Because of NSE's IP blocking (see above), data fetches may fail
   intermittently on cloud hosts — the app will surface warnings when this
   happens rather than crash.

## Editing the watchlist
Edit the `SECURITIES_FO` list near the top of `app.py` to add or remove
symbols. Symbols must match NSE's exact ticker (e.g. `TIINDIA`, not
`THINDIA`).

## Project structure
```
.
├── app.py              # Streamlit app (fetch, parse, signals, UI)
├── requirements.txt
└── README.md
```
