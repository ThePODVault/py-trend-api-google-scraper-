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

        print(f"\n🔍 Scraping trends for: {keyword}\n")

        widget_url = (
            f"https://trends.google.com/trends/api/explore"
            f"?hl=en-US&tz=360&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        )
        print(f"\n🧠 Widget URL: {widget_url}\n")

        widget_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={widget_url}"
        )
        print(f"📥 Widget response: {widget_res.status_code}")

        cleaned_text = widget_res.text.replace(")]}',", "").strip()
        if not cleaned_text.startswith("{"):
            print(f"\n📃 Widget response body preview: {widget_res.text[:300]}")
            raise ValueError("Invalid widget response format")

        widgets = json.loads(cleaned_text)
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        print(f"✅ Widget token: {widget['token']}")

        # Build multiline request — don't append geo
        multiline_url = (
            "https://trends.google.com/trends/api/widgetdata/multiline"
            f"?hl=en-US&tz=360&req={json.dumps(widget['request'])}&token={widget['token']}"
        )

        multiline_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}"
        )
        print(f"📥 Multiline response: {multiline_res.status_code}")

        cleaned_data = multiline_res.text.replace(")]}',", "")
        trend_json = json.loads(cleaned_data)

        timeline_data = trend_json["default"]["timelineData"]
        trend = [{"date": point["formattedTime"], "interest": point["value"][0]} for point in timeline_data]

        return {"keyword": keyword, "trend": trend}

    except Exception as e:
        print(f"\n❌ Trend scraping error: {e}")
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

