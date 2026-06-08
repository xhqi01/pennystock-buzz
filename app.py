import os
import re
import smtplib
import threading
import time
from datetime import datetime
from collections import Counter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import praw
import yfinance as yf
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".")

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
PENNY_STOCK_MAX_PRICE = 5.0

EXCLUDE_WORDS = {
    "A", "I", "AM", "PM", "US", "UK", "EU", "IT", "BE", "DO", "GO", "NO",
    "OR", "IF", "AT", "BY", "TO", "OF", "ON", "IN", "IS", "RE", "DD",
    "WSB", "OTC", "IPO", "ETF", "CEO", "CFO", "CTO", "SEC", "FDA", "FED",
    "GDP", "AI", "ML", "EV", "AR", "VR", "ATH", "ATL", "IMO", "EPS",
    "PE", "PS", "PB", "ROI", "YTD", "EOD", "EOW", "YOLO", "FOMO",
    "THE", "FOR", "AND", "BUT", "NOT", "ALL", "NEW", "OUT", "UP",
}

# Cache to avoid re-fetching the same ticker multiple times per scan
_price_cache = {}
_cache_time  = {}
CACHE_TTL    = 300  # 5 minutes

# ── TICKER EXTRACTION ─────────────────────────────────────────────────────────
def extract_tickers(text):
    """Extract $TICKER patterns and verify via Yahoo Finance."""
    # Prioritize $TICKER mentions (more reliable on penny stock subs)
    dollar = re.findall(r'\$([A-Z]{1,5})', text.upper())
    # Also catch plain uppercase 2-5 char words
    plain  = re.findall(r'\b([A-Z]{2,5})\b', text.upper())

    candidates = set(dollar + plain)
    return {t for t in candidates if t not in EXCLUDE_WORDS and len(t) >= 2}

def verify_penny_stock(ticker):
    """Check if ticker exists and price is under $5. Returns price or None."""
    now = time.time()
    if ticker in _price_cache and now - _cache_time.get(ticker, 0) < CACHE_TTL:
        return _price_cache[ticker]

    try:
        stock = yf.Ticker(ticker)
        hist  = stock.history(period="2d")
        if hist.empty:
            _price_cache[ticker] = None
            _cache_time[ticker]  = now
            return None

        price = round(hist["Close"].iloc[-1], 4)
        result = price if price <= PENNY_STOCK_MAX_PRICE and price > 0 else None
        _price_cache[ticker] = result
        _cache_time[ticker]  = now
        return result
    except:
        _price_cache[ticker] = None
        _cache_time[ticker]  = now
        return None

def get_price_change(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if len(hist) >= 2:
            today = hist["Close"].iloc[-1]
            prev  = hist["Close"].iloc[-2]
            return round(((today - prev) / prev) * 100, 2)
    except:
        pass
    return None

# ── REDDIT SCRAPER ─────────────────────────────────────────────────────────────
def scrape_subreddits(subreddits, client_id, client_secret, post_limit=30):
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="penny-stock-radar:v1.0 (by /u/anonymous)"
    )

    ticker_counter = Counter()
    post_data      = {}
    errors         = []

    for sub_name in subreddits:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.hot(limit=post_limit):
                text     = f"{post.title} {post.selftext}"
                tickers  = extract_tickers(text)

                for ticker in tickers:
                    ticker_counter[ticker] += 1
                    if ticker not in post_data:
                        post_data[ticker] = []
                    post_data[ticker].append({
                        "title": post.title,
                        "url":   f"https://reddit.com{post.permalink}",
                        "score": post.score,
                        "sub":   sub_name,
                    })
        except Exception as e:
            errors.append(f"r/{sub_name}: {str(e)}")

    return ticker_counter, post_data, errors

# ── EMAIL ─────────────────────────────────────────────────────────────────────
def build_email(results, subreddits):
    rows = ""
    for r in results:
        chg       = r.get("change")
        chg_color = "#2ecc71" if (chg or 0) >= 0 else "#e74c3c"
        chg_str   = f"{'+' if (chg or 0) >= 0 else ''}{chg}%" if chg is not None else "—"

        posts = r.get("posts", [])[:2]
        links = " · ".join(
            f'<a href="{p["url"]}" style="color:#888;font-size:11px">{p["title"][:50]}…</a>'
            for p in posts
        )

        rows += f"""
        <tr style="border-bottom:1px solid #f0f0f0">
          <td style="padding:10px 12px;font-weight:700">{r["ticker"]}</td>
          <td style="padding:10px 12px;text-align:center">
            <span style="background:#f0f0f0;padding:3px 10px;border-radius:12px;font-size:12px">{r["mentions"]}</span>
          </td>
          <td style="padding:10px 12px;font-size:13px">${r["price"]}</td>
          <td style="padding:10px 12px;color:{chg_color};font-size:13px">{chg_str}</td>
          <td style="padding:10px 12px">{links}</td>
        </tr>"""

    subs = ", ".join(f"r/{s}" for s in subreddits)
    return f"""
    <html><body style="font-family:monospace;background:#f7f6f3;padding:32px">
    <div style="max-width:640px;margin:0 auto;background:#fff;border:1px solid #ddd;padding:28px">
      <h2 style="margin:0 0 4px;font-size:15px">🔬 Penny Stock Radar Report</h2>
      <p style="color:#888;font-size:12px;margin:0 0 20px">
        {subs} · {datetime.now().strftime("%Y-%m-%d %H:%M")} · stocks under $5 only
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="border-bottom:2px solid #eee;color:#aaa;font-size:10px;text-transform:uppercase">
            <th style="padding:8px 12px;text-align:left">Ticker</th>
            <th style="padding:8px 12px;text-align:center">Mentions</th>
            <th style="padding:8px 12px;text-align:left">Price</th>
            <th style="padding:8px 12px;text-align:left">1d Change</th>
            <th style="padding:8px 12px;text-align:left">Posts</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="font-size:11px;color:#bbb;margin-top:16px">
        penny-stock-radar · not financial advice
      </p>
    </div>
    </body></html>"""

def send_email(sender, password, receiver, subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = receiver
    msg.attach(MIMEText(body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(sender, password)
        s.sendmail(sender, receiver, msg.as_string())

# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.json

    reddit_id     = data.get("reddit_id", "").strip()
    reddit_secret = data.get("reddit_secret", "").strip()
    subreddits    = data.get("subreddits", [])
    send_mail     = data.get("send_email", False)
    email_sender  = data.get("email_sender", "").strip()
    email_pass    = data.get("email_password", "").strip()
    email_recv    = data.get("email_receiver", "").strip()

    if not reddit_id or not reddit_secret:
        return jsonify({"error": "Reddit API credentials required."}), 400
    if not subreddits:
        return jsonify({"error": "Select at least one subreddit."}), 400

    try:
        ticker_counter, post_data, errors = scrape_subreddits(
            subreddits, reddit_id, reddit_secret
        )

        # Verify each ticker is a real penny stock
        verified = []
        for ticker, count in ticker_counter.most_common(50):
            price = verify_penny_stock(ticker)
            if price is not None:
                change = get_price_change(ticker)
                verified.append({
                    "ticker":   ticker,
                    "mentions": count,
                    "price":    price,
                    "change":   change,
                    "posts":    post_data.get(ticker, [])[:3],
                })
            if len(verified) >= 20:
                break

        if send_mail and email_sender and email_pass and email_recv and verified:
            subject = f"🔬 Penny Radar: {', '.join(r['ticker'] for r in verified[:5])}"
            body    = build_email(verified, subreddits)
            threading.Thread(
                target=send_email,
                args=(email_sender, email_pass, email_recv, subject, body)
            ).start()

        return jsonify({"results": verified, "scanned": subreddits, "errors": errors})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
