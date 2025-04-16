from flask import Flask, request, jsonify
import requests
import json
import re
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")  # Load from Railway or .env

def clean_keyword(keyword):
    # Lowercase, remove punctuation, and keep only alphanumeric + space
    cleaned = re.sub(r'[^\w\s]', '', keyword.lower())
    parts = cleaned.split()
    filtered = [p for p in parts if len(p) > 2]  # Filter out short/noise words
    return ' '.join(filtered[:4])  # Limit to first 4 strong words

def scrape_google_trends(keyword):
    try:
        print(f"🔍 Scraping trends for: {keyword}")
        keyword = clean_keyword(keyword)
        if not keyword:
            raise ValueError("Keyword is empty after cleaning")

        # STEP 1: Get widget config
        trends_url = (
            "https://trends.google.com/trends/api/explore?hl=en-US&tz=360&req="
            + json.dumps({
                "comparisonItem": [{"keyword": keyword, "geo": "", "time": "today 12-m"}],
                "category": 0,
                "property": ""
            })
        )
        print(f"\n🧠 Widget URL: {trends_url}")
        widget_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}")
        print(f"📥 Widget response: {widget_res.status_code}")

        if not widget_res.text.startswith(")]}'"):
            print("⚠️ Widget response missing expected prefix")
            raise ValueError("Invalid widget response format")

        cleaned_json = widget_res.text.replace(")]}',", "")
        widgets = json.loads(cleaned_json)

        # STEP 2: Get TIMESERIES widget
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        print(f"✅ Widget token: {widget['token']}")

        # STEP 3: Fetch trend data
        multiline_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(widget['request'])}&token={widget['token']}&geo={widget['request']['geo']}"
        )
        multiline_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}")
        print(f"📥 Multiline response: {multiline_res.status_code}")

        multiline_clean = multiline_res.text.replace(")]}',", "")
        trend_json = json.loads(multiline_clean)

        timeline_data = trend_json["default"]["timelineData"]
        trend = [
            {"date": entry["formattedTime"], "interest": entry["value"][0]}
            for entry in timeline_data
        ]

        return {"keyword": keyword, "trend": trend}

    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
        return None

@app.route("/trend")
def get_trend():
    raw_keyword = request.args.get("keyword", "").strip()
    keyword = raw_keyword.replace("\n", "").replace("\r", "").strip()
    print(f"📥 Raw keyword: {raw_keyword}\n -> Cleaned: {keyword}")

    trend_data = scrape_google_trends(keyword)
    if trend_data:
        return jsonify(trend_data)
    else:
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
