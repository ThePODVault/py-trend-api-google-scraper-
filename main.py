from flask import Flask, request, jsonify
from flask_cors import CORS
from pytrends.request import TrendReq
import re
import time
from random import choice

app = Flask(__name__)
CORS(app)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
]

def clean_keyword(keyword):
    print(f"📥 Raw keyword: {keyword}")
    cleaned = re.sub(r'[^\w\s]', '', keyword.lower()).strip()
    parts = cleaned.split()
    filtered = [p for p in parts if len(p) > 2]
    cleaned_keyword = ' '.join(filtered[:4])
    print(f" -> Cleaned: {cleaned_keyword}\n")
    return cleaned_keyword

def fetch_trend_data(keyword):
    try:
        user_agent = choice(USER_AGENTS)
        print(f"🔍 Scraping trends for: {keyword}\n")

        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            retries=3,
            backoff_factor=0.5,
            requests_args={'headers': {'User-Agent': user_agent}}
        )

        pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
        time.sleep(1)

        data = pytrends.interest_over_time()

        if data.empty:
            raise ValueError("Google Trends returned empty data")

        trend = [{"date": str(row[0].date()), "interest": int(row[1])} for row in data[[keyword]].itertuples()]
        return {"keyword": keyword, "trend": trend}

    except Exception as e:
        print(f"❌ Trend scraping error: {e}\n")
        return None

@app.route("/trend")
def get_trend():
    keyword = request.args.get("keyword", "")
    keyword = clean_keyword(keyword)
    trend_data = fetch_trend_data(keyword)
    if trend_data:
        return jsonify(trend_data)
    else:
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
