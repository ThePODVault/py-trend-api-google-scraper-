from flask import Flask, request, jsonify
import requests
import json
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = "your_scraperapi_key_here"  # Replace with your actual ScraperAPI key

def clean_keyword(keyword):
    cleaned = re.sub(r'[^\w\s]', '', keyword.lower())
    parts = cleaned.split()
    filtered = [p for p in parts if len(p) > 2]
    return ' '.join(filtered[:4])

def scrape_google_trends(keyword):
    try:
        print(f"📥 Raw keyword: {keyword}\n")
        keyword = clean_keyword(keyword)
        print(f" -> Cleaned: {keyword}\n")

        if not keyword:
            raise ValueError("Keyword is empty after cleaning")

        trends_url = (
            f"https://trends.google.com/trends/api/explore?hl=en-US&tz=360"
            f"&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        )
        print(f"\n🔍 Scraping trends for: {keyword}\n")
        print(f"\n🧠 Widget URL: {trends_url}\n")

        widget_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}",
            timeout=20
        )

        print(f"\n📥 Widget response: {widget_res.status_code}\n")

        if widget_res.status_code != 200:
            raise ValueError("Invalid widget response")

        # ✅ Updated prefix stripper with regex
        cleaned_json = re.sub(r"^\)\]\}'\s*", "", widget_res.text.strip())

        # Optional: log a preview
        print("\n📃 Widget response body preview:", cleaned_json[:300], "\n")

        widgets = json.loads(cleaned_json)

        # Find the TIMESERIES widget
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        print(f"\n✅ Widget token: {widget['token']}\n")

        multiline_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(widget['request'])}&token={widget['token']}&geo={widget['request'].get('geo', '')}"
        )

        multiline_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}",
            timeout=20
        )
        print(f"\n📥 Multiline response: {multiline_res.status_code}\n")

        multiline_clean = re.sub(r"^\)\]\}'\s*", "", multiline_res.text.strip())
        trend_json = json.loads(multiline_clean)

        timeline_data = trend_json["default"]["timelineData"]
        trend = [
            {"date": entry["formattedTime"], "interest": entry["value"][0]}
            for entry in timeline_data
        ]

        return {"keyword": keyword, "trend": trend}
    except Exception as e:
        print(f"\n❌ Trend scraping error: {e}\n")
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
