# F&O Premarket (NSE Pre-Open) Tracker

A Streamlit app that pulls the NSE pre-open (9:00–9:15 AM IST) snapshot for
**F&O-eligible securities only** (`key=FNO`) and surfaces gainers/losers,
market breadth, order-imbalance signals, and a near-circuit watchlist.

Outside the 9:00–9:15 AM IST window, the app clearly labels the data as a
stale/previous-session snapshot rather than pretending it's live.

## Files

- `app.py` — the Streamlit app
- `requirements.txt` — Python dependencies

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Running locally from a residential IP is the most reliable way to avoid NSE's
bot-check (see "NSE IP blocking" below).

## Deploy on GitHub + Streamlit Community Cloud

1. Create a new GitHub repo (e.g. `nifty-fno-premarket-tracker`) and push these
   two files to it:
   ```bash
   git init
   git add app.py requirements.txt README.md
   git commit -m "F&O premarket tracker"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. Click **"New app"**, pick your repo/branch, and set the main file path to
   `app.py`.
4. Click **Deploy**.

## NSE IP blocking (important)

NSE aggressively blocks requests coming from known datacenter/cloud IP
ranges — this includes Streamlit Community Cloud, Google Colab, AWS, GCP,
Azure, etc. If the deployed app repeatedly errors with 401/403:

- Use the **"🔄 Refresh now"** button — sometimes a fresh session cookie gets
  through.
- Run the app **locally** on a normal home/office connection, where NSE
  generally doesn't block you.
- Route requests through a residential/rotating proxy (set up your own
  `requests` proxy config in `get_nse_session()`), or
- Self-host on a VPS with a non-datacenter-flagged IP (results vary).

This is an NSE-side restriction, not a bug in the app.

## Disclaimer

This tool shows descriptive premarket market data only. It is not investment
advice. Always verify live price and quantity on your broker's terminal
before placing any order.
