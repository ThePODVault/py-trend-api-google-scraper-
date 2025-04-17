from flask import Flask, request, jsonify
from flask_cors import CORS
from pytrends.request import TrendReq
import pandas as pd
import re
import json
from random import choice
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY") or "your_scraperapi_key_here"
TREND_CACHE_FILE = "trend_cache.json"

# Load user agents
def load_user_agents(file_path="user_agents.json"):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load user agents: {e}")
        return []

USER_AGENTS = load_user_agents()
recent_agents = []

# Load trend cache
try:
    with open(TREND_CACHE_FILE, "r") as f:
        trend_cache = json.load(f)
except:
    trend_cache = {}

def save_trend_cache():
    with open(TREND_CACHE_FILE, "w") as f:
        json.dump(trend_cache, f)

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
    if phrase in trend_cache:
        print(f"⚡ Using cached trend for '{phrase}'")
        df = pd.DataFrame(trend_cache[phrase])
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        return df.rename(columns={"interest": "interest"})

    for attempt in range(retries):
        try:
            pytrends = TrendReq(
                hl='en-US',
                tz=360,
                retries=2,
                backoff_factor=0.5,
                requests_args={
                    'headers': {'User-Agent': user_agent},
                    'proxies': get_scraperapi_proxy(),
                    'verify': True
                }
            )
            pytrends.build_payload([phrase], cat=0, timeframe='today 12-m', geo='', gprop='')
            df = pytrends.interest_over_time()
            if df.empty:
                raise ValueError(f"No data for phrase: {phrase}")
            df = df.drop(columns=["isPartial"], errors="ignore")
            monthly = df.resample('M').mean().round(0)
            result = monthly.rename(columns={phrase: "interest"})

            # Cache it
            trend_cache[phrase] = [
                {"date": str(index.date()), "interest": int(row["interest"])}
                for index, row in result.iterrows()
            ]
            save_trend_cache()

            return result
        except Exception as e:
            print(f"❌ Retry {attempt + 1} for '{phrase}': {e}")
    raise ValueError(f"Failed to fetch after {retries} attempts: {phrase}")

def fetch_trend_data(phrases):
    try:
        monthly_data = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(fetch_single_phrase_trend, phrase, get_unique_user_agent())
                for phrase in phrases
            ]

            for future in futures:
                try:
                    monthly_data.append(future.result())
                except Exception as e:
                    print(f"⚠️ Skipped phrase due to error: {e}")

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
