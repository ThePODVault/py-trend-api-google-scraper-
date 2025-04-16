from flask import Flask, request, jsonify
import requests
import json
import re
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")  # Your ScraperAPI key

def clean_keyword(keyword):
    print(f"\n📥 Raw keyword: {keyword}\n")
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

        print(f"\n🔍 Scraping trends for: {keyword}\n")

        # STEP 1: Get widget config
        trends_url = (
            "https://trends.google.com/trends/api/explore"
            f"?hl=en-US&tz=360&req={json.dumps({'comparisonItem': [{'keyword': keyword, 'geo': '', 'time': 'today 12-m'}], 'category': 0, 'property': ''})}"
        )

        print(f"\n🧠 Widget URL: {trends_url}\n")

        widget_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}",
            timeout=20
        )

        print(f"\n📥 Widget response: {widget_res.status_code}\n")

        text = widget_res.text.strip()
        print(f"📃 Widget response body preview: {text[:300]}\n")  # First 300 characters for inspection

        if not text.startswith(")]}'"):
            print("⚠️ Widget response missing expected prefix\n")
            raise ValueError("Invalid widget response format")

        cleaned_json = text.replace(")]}',", "").strip()
        if not cleaned_json:
            raise ValueError("Widget JSON response is empty after cleaning")

        try:
            widgets = json.loads(cleaned_json)
        except Exception as e:
            print("❌ Failed to parse widget JSON:", e)
            raise

        # STEP 2: Get TIMESERIES widget
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        print(f"✅ Widget token: {widget['token']}\n")

        # STEP 3: Fetch trend data
        multiline_url = (
            "https://trends.google.com/trends/api/widgetdata/multiline"
            f"?hl=en-US&tz=360&req={json.dumps(widget['request'])}"
            f"&token={widget['token']}&geo={widget['request'].get('geo', '')}"
        )

        multiline_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}",
            timeout=20
        )

        print(f"📥 Multiline response: {multiline_res.status_code}\n")
        multiline_text = multiline_res.text.replace(")]}',", "").strip()
        trend_json = json.loads(multiline_text)

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
