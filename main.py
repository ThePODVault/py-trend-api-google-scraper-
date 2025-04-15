from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)  # ✅ This enables CORS for all domains (including your Webflow site)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def scrape_google_trends(keyword):
    try:
        print(f"🔍 Scraping trends for: {keyword}")

        # Step 1: Fetch widgets
        explore_url = (
            "https://trends.google.com/trends/api/explore?hl=en-US&tz=360"
            f"&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        )
        widget_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={explore_url}")
        print(f"📥 Widget response: {widget_res.status_code}")

        cleaned = widget_res.text.replace(")]}',", "")
        widgets = json.loads(cleaned)

        # Step 2: Extract TIMESERIES widget
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        token = widget["token"]
        req = widget["request"]

        # Step 3: Fetch timeline data
        data_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(req)}&token={token}&geo="
        )
        data_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={data_url}")
        print(f"📥 Data response: {data_res.status_code}")
        trend_json = json.loads(data_res.text.replace(")]}',", ""))

        timeline = trend_json["default"]["timelineData"]
        trend_data = [{"date": t["formattedTime"], "interest": t["value"][0]} for t in timeline]

        return trend_data
    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
        return None

@app.route("/trend")
def trend():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"error": "Missing keyword"}), 400

    trend = scrape_google_trends(keyword)
    if trend is None:
        return jsonify({"error": "Failed to fetch trend data"}), 500

    return jsonify({"keyword": keyword, "trend": trend})
