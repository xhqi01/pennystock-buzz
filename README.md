# Penny Stock Radar

Scans Reddit's penny stock communities, extracts mentioned tickers, and verifies each one against Yahoo Finance to confirm the stock actually exists and is priced under $5. No hardcoded ticker lists — everything is verified in real time.

## Features

- Monitors 6 penny stock subreddits (r/pennystocks, r/RobinhoodPennyStocks, r/pennystockDD, r/OTCstocks, r/smallstreetbets, r/Canadapennystocks)
- Extracts `$TICKER` mentions and validates each via Yahoo Finance
- Only shows stocks confirmed to be under $5
- Displays mention count, current price, and 1-day price change
- Links to the Reddit posts mentioning each stock
- Optional email summary report
- Clean web interface — no command line needed

## Setup

**1. Clone and install**

```bash
git clone https://github.com/xhqi01/penny-stock-radar.git
cd penny-stock-radar
pip install -r requirements.txt
```

**2. Get Reddit API credentials**

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **Create another app**
3. Choose type: **script**
4. Name it anything, redirect URI: `http://localhost`
5. Copy your `client_id` and `client_secret`

**3. Run**

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## Deploy to Render (runs 24/7 for free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → **Web Service**
3. Connect your GitHub repo
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python app.py`
6. Click Deploy

## How ticker verification works

Rather than maintaining a hardcoded list of penny stock tickers (which would go stale quickly), this tool:

1. Extracts all `$TICKER` patterns and uppercase words from Reddit posts
2. Queries Yahoo Finance for each candidate
3. Only includes tickers that return a valid price under $5

This means it catches newly listed or obscure stocks that a static list would miss.

## Notes

- Stock data from Yahoo Finance (15-minute delay)
- Verification adds ~10-30 seconds to each scan depending on how many tickers are found
- Not financial advice

---

# Penny Stock Radar（日本語）

Redditのペニー株コミュニティをスキャンし、言及された銘柄をYahoo Financeでリアルタイム検証して$5以下の株のみを表示するツールです。固定のティッカーリストは使わず、すべてリアルタイムで確認します。

## 機能

- 6つのペニー株サブレディットを監視
- `$TICKER` パターンを自動抽出し、Yahoo Financeで検証
- $5以下に確認された銘柄のみ表示
- 言及数・現在株価・前日比を表示
- 各銘柄に言及しているReddit投稿へのリンク付き
- メールレポート送信オプション
- Webインターフェース — コマンドライン不要

## セットアップ

**1. クローンとインストール**

```bash
git clone https://github.com/xhqi01/penny-stock-radar.git
cd penny-stock-radar
pip install -r requirements.txt
```

**2. Reddit APIキーの取得**

1. [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) にアクセス
2. **Create another app** をクリック
3. タイプ: **script** を選択
4. redirect URI: `http://localhost`
5. `client_id` と `client_secret` をコピー

**3. 起動**

```bash
python app.py
```

ブラウザで [http://localhost:5000](http://localhost:5000) を開く。

## Renderへのデプロイ（24時間稼働・無料）

1. このリポジトリをGitHubにプッシュ
2. [render.com](https://render.com) → New → **Web Service**
3. GitHubリポジトリを接続
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python app.py`
6. Deploy をクリック

## 注意事項

- 株価データはYahoo Finance（15分遅延）
- 検証処理のため、スキャンに10〜30秒かかる場合があります
- 投資アドバイスではありません
