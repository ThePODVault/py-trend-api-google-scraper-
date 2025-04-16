from flask import Flask, request, jsonify
from flask_cors import CORS
from pytrends.request import TrendReq
import pandas as pd
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

def clean_phrases(raw_title):
    print(f"📥 Raw keyword: {raw_title}")
    raw_phrases = raw_title.lower().split(",")[:4]
    phrases = []
    for phrase in raw_phrases:
        cleaned = re.sub(r"[^\w\s]", "", phrase).strip()
        if cleaned:
            phrases.append(cleaned)
    print(f"🔍 Phrases to analyze: {phrases}\n")
    return phrases

def fetch_trend_data(phrases):
    try:
        user_agent = choice(USER_AGENTS)
        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            retries=3,
            backoff_factor=0.5,
            requests_args={'headers': {'User-Agent': user_agent}}
        )

        pytrends.build_payload(phrases, cat=0, timeframe='today 12-m', geo='', gprop='')
        time.sleep(1)
        df = pytrends.interest_over_time()
        if df.empty:
            raise ValueError("Google Trends returned empty data")

        # Drop 'isPartial' column if it exists
        df = df.drop(columns=["isPartial"], errors="ignore")

        # Resample weekly trend data to monthly average
        monthly_df = df.resample('M').mean().round(0)

        # Calculate average interest across phrases
        monthly_df["average"] = monthly_df.mean(axis=1).astype(int)

        trend = [{"date": str(index.date()), "interest": row["average"]} for index, row in monthly_df.iterrows()]
        return {"keyword": ", ".join(phrases), "trend": trend}

    except Exception as e:
        print(f"❌ Trend scraping error: {e}\n")
        return None

@app.route("/trend")
def get_trend():
    raw_title = request.args.get("keyword", "")
    phrases = clean_phrases(raw_title)
    trend_data = fetch_trend_data(phrases)
    if trend_data:
        return jsonify(trend_data)
    else:
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
