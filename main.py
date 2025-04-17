from flask import Flask, request, jsonify
from flask_cors import CORS
from pytrends.request import TrendReq
import pandas as pd
import re
import json
from random import choice
import os

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY") or "your_scraperapi_key_here"

def load_user_agents(file_path="user_agents.json"):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load user agents: {e}")
        return []

USER_AGENTS = load_user_agents()
recent_agents = []
TREND_CACHE_FILE = "trend_cache.json"

def get_unique_user_agent():
    global recent_agents
    available = [ua for ua in USER_AGENTS if ua not in recent_agents]
    if not available:
        recent_agents = []
        available = USER_AGENTS.copy()
    agent = choice(available)
    recent_agents.append(agent)
    if len(recent_agents) > 30:
        recent_agents = recent_agents[-30:]
    return agent

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

def get_scraperapi_proxy():
    return {
        "https": f"http://scraperapi.proxy:8000?api_key={SCRAPER_API_KEY}"
    }

def fetch_single_phrase_trend(phrase, user_agent, retries=3):
    for attempt in range(retries):
        try:
            pytrends = TrendReq(
                hl='en-US',
                tz=360,
                retries=2,
                backoff_factor=0.5,
                requests_args={
                    'headers': {'User-Agent': user_agent},
                    'proxies': get_scraperapi_proxy()
                }
            )
            pytrends.build_payload([phrase], cat=0, timeframe='today 12-m', geo='', gprop='')
            df = pytrends.interest_over_time()
            if df.empty:
                raise ValueError(f"No data for phrase: {phrase}")
            df = df.drop(columns=["isPartial"], errors="ignore")
            monthly = df.resample('ME').mean().round(0)
            return monthly.rename(columns={phrase: "interest"})
        except Exception as e:
            print(f"❌ Retry {attempt + 1} for '{phrase}': {e}")
    raise ValueError(f"Failed to fetch after {retries} attempts: {phrase}")

def fetch_trend_data(phrases):
    try:
        monthly_data = []

        for phrase in phrases:
            user_agent = get_unique_user_agent()
            try:
                print(f"📊 Fetching trend for: {phrase}")
                trend_df = fetch_single_phrase_trend(phrase, user_agent)
                monthly_data.append(trend_df)
            except Exception as inner_e:
                print(f"⚠️ Skipped '{phrase}': {inner_e}")
                continue

        if not monthly_data:
            raise ValueError("No trend data was returned for any keyword")

        combined = pd.concat(monthly_data, axis=1).fillna(0)
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
