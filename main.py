from flask import Flask, request, jsonify
import requests
import json
import re
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def clean_keyword(keyword):
    cleaned = re.sub(r'[^\w\s]', '', keyword.lower())
    parts = cleaned.split()
    filtered = [p for p in parts if len(p) > 2]
    return ' '.join(filtered[:4])

def scrape_google_trends(keyword):
    try:
        print(f"📥 Raw keyword: {keyword}")
        keyword = clean_keyword(keyword)
        print(f" -> Cleaned: {keyword}")
        if not keyword:
            raise ValueError("Keyword is empty after cleaning")

        print(f"🔍 Scraping trends for: {keyword}")

        trends_url = (
            "https://trends.google.com/trends/api/explore"
            f"?hl=en-US&tz=360&req={{\"comparisonItem\": [{{\"keyword\": \"{keyword}\", \"geo\": \"\", \"time\": \"today 12-m\"}}], \"category\": 0, \"property\": \"\"}}"
        )
        print(f"\n\n🧠 Widget URL: {trends_url}\n")

        proxy_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}"
        widget_res = requests.get(proxy_url, timeout=20)

        print(f"📥 Widget response: {widget_res.status_code}")

        rawText = widget_res.text
        if not rawText.startswith(")]}',"):
            raise ValueError("Invalid widget response format")

        cleaned_json = rawText.replace(")]}',", "")
        widgets = json.loads(cleaned_json)

        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        print(f"✅ Widget token: {widget['token']}")

        multiline_url = (
            "https://trends.google.com/trends/api/widgetdata/multiline"
            f"?hl=en-US&tz=360&req={json.dumps(widget['request'])}&token={widget['token']}&geo={widget['request']['geo']}"
        )
        multiline_proxy = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}"
        multiline_res = requests.get(multiline_proxy, timeout=20)
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
    keyword = request.args.get("keyword", "")
    trend_data = scrape_google_trends(keyword)
    if trend_data:
        return jsonify(trend_data)
    else:
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
