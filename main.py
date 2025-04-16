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
    print(f"📥 Raw keyword: {keyword}")
    cleaned = re.sub(r"[^\w\s]", "", keyword.lower())
    cleaned = " ".join(cleaned.split())
    print(f" -> Cleaned: {cleaned}\n")
    return cleaned

def scrape_google_trends(keyword):
    try:
        keyword = clean_keyword(keyword)
        if not keyword:
            raise ValueError("Keyword is empty after cleaning")

        print(f"🔍 Scraping trends for: {keyword}\n")

        # Step 1: Get widget config
        explore_url = (
            "https://trends.google.com/trends/api/explore"
            f"?hl=en-US&tz=360&req={json.dumps({'comparisonItem': [{'keyword': keyword, 'geo': '', 'time': 'today 12-m'}], 'category': 0, 'property': ''})}"
        )
        print(f"🧠 Widget URL: {explore_url}\n")

        widget_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={explore_url}"
        )
        print(f"📥 Widget response: {widget_res.status_code}\n")

        if widget_res.status_code != 200:
            raise ValueError("Failed to fetch widget config")

        cleaned_json = widget_res.text.replace(")]}',", "").strip()
        print(f"📃 Widget response body preview: {cleaned_json[:500]}\n")  # Log first 500 characters

        widgets = json.loads(cleaned_json)

        # Step 2: Find the TIMESERIES widget
        timeseries_widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        token = timeseries_widget["token"]
        print(f"✅ Widget token: {token}\n")

        geo = timeseries_widget["request"].get("geo", "")
        if isinstance(geo, dict):  # in case geo is like: {"geo": {}}
            geo = geo.get("country", "")

        req_body = json.dumps(timeseries_widget["request"])
        trends_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline"
            f"?hl=en-US&tz=360&req={req_body}&token={token}&geo={geo}"
        )

        multiline_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}"
        )
        print(f"📥 Trends response: {multiline_res.status_code}")

        multiline_clean = multiline_res.text.replace(")]}',", "").strip()
        trend_json = json.loads(multiline_clean)

        timeline_data = trend_json["default"]["timelineData"]
        trend = [
            {"date": entry["formattedTime"], "interest": entry["value"][0]}
            for entry in timeline_data
        ]

        return {"keyword": keyword, "trend": trend}

    except Exception as e:
        print(f"❌ Trend scraping error: {e}\n")
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
