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
    cleaned = re.sub(r'[^\w\s]', '', keyword.lower())
    parts = cleaned.split()
    filtered = [p for p in parts if len(p) > 2]
    cleaned_keyword = ' '.join(filtered[:4])
    print(f" -> Cleaned: {cleaned_keyword}\n")
    return cleaned_keyword

def scrape_google_trends(keyword):
    try:
        keyword = clean_keyword(keyword)
        if not keyword:
            raise ValueError("Keyword is empty after cleaning")

        explore_url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=360&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        full_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={explore_url}"

        print(f"🔍 Scraping trends for: {keyword}\n")
        print(f"🧠 Widget URL: {explore_url}\n")

        response = requests.get(full_url)
        print(f"📥 Widget response: {response.status_code}\n")

        if response.status_code != 200:
            raise ValueError("Google Trends explore response not 200")

        text = response.text
        if not text.startswith(")]}'"):
            print("⚠️ Widget response missing expected prefix\n")
            raise ValueError("Invalid widget response format")

        cleaned_json = text.replace(")]}',", "")
        json_data = json.loads(cleaned_json)

        widget = next(w for w in json_data["widgets"] if w["id"] == "TIMESERIES")
        token = widget["token"]
        print(f"✅ Widget token: {token}\n")

        req_obj = widget["request"]
        geo = req_obj.get("geo", {}).get("country", "") if isinstance(req_obj.get("geo"), dict) else ""

        multiline_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(req_obj)}&token={token}&geo={geo}"
        )
        multiline_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}")
        print(f"📥 Multiline response: {multiline_res.status_code}\n")

        if multiline_res.status_code != 200:
            raise ValueError("Failed to fetch multiline data")

        multiline_clean = multiline_res.text.replace(")]}',", "")
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
