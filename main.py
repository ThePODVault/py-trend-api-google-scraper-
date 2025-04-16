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
    split_by_comma = re.split(r"[,\-]", raw_title.lower())
    phrases = []
    for part in split_by_comma:
        sub_parts = part.strip().split()
        for i in range(len(sub_parts)):
            for j in range(i+1, min(len(sub_parts)+1, i+4)):  # generate 2-3 word phrases
                phrase = " ".join(sub_parts[i:j])
                cleaned = re.sub(r"[^\w\s]", "", phrase).strip()
                if len(cleaned.split()) >= 2 and cleaned not in phrases:
                    phrases.append(cleaned)
    print(f"🔍 Final phrases to analyze: {phrases[:10]}")
    return phrases[:10]  # Limit to top 10 phrases for performance

def fetch_single_phrase_trend(phrase, user_agent):
    pytrends = TrendReq(
        hl='en-US',
        tz=360,
        retries=3,
        backoff_factor=0.5,
        requests_args={'headers': {'User-Agent': user_agent}}
    )
    pytrends.build_payload([phrase], cat=0, timeframe='today 12-m', geo='', gprop='')
    df = pytrends.interest_over_time()
    if df.empty:
        raise ValueError(f"No data for phrase: {phrase}")
    df = df.drop(columns=["isPartial"], errors="ignore")
    monthly = df.resample('M').mean().round(0)
    return monthly.rename(columns={phrase: "interest"})

def fetch_trend_data(phrases):
    try:
        user_agent = choice(USER_AGENTS)
        monthly_data = []

        for phrase in phrases:
            try:
                print(f"📊 Fetching trend for: {phrase}")
                trend_df = fetch_single_phrase_trend(phrase, user_agent)
                monthly_data.append(trend_df)
                time.sleep(1)  # small delay to avoid rate limits
            except Exception as inner_e:
                print(f"⚠️ Skipped '{phrase}': {inner_e}")
                continue

        if not monthly_data:
            raise ValueError("No trend data was returned for any keyword")

        combined = pd.concat(monthly_data, axis=1)
        combined = combined.fillna(0)
        combined["average"] = combined.mean(axis=1).astype(int)

        trend = [{"date": str(index.date()), "interest": row["average"]} for index, row in combined.iterrows()]
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
