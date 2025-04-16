from flask import Flask, request, jsonify
import requests
import json
import re
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")  # Make sure this is set in Railway or your environment

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

        trends_url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=360&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        print(f"\n🔍 Scraping trends for: {keyword}")
        print(f"\n🧠 Widget URL: {trends_url}\n")

        res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}",
            headers={"User-Agent": "Mozilla/5.0"}
        )

        print(f"\n📥 Widget response: {res.status_code}\n")

        if res.status_code != 200 or not res.text.startswith(")]}'"):
            print("\n⚠️ Widget response missing expected prefix\n")
            raise ValueError("Invalid widget response format")

        body = res.text.replace(")]}',", "", 1)
        print(f"\n📃 Widget response body preview: )]}}'\n\n{body[:400]}\n")

        data = json.loads(body)
        widget = next(w for w in data["widgets"] if w["id"] == "TIMESERIES")
        token = widget["token"]
        print(f"\n✅ Widget token: {token}")

        req = json.dumps(widget["request"])
        geo = widget["request"].get("geo", "")
        if isinstance(geo, dict): geo = ""

        multiline_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline"
            f"?hl=en-US&tz=360&req={req}&token={token}&geo={geo}"
        )

        multiline_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        print(f"\n📥 Multiline response: {multiline_res.status_code}\n")
        multiline_body = multiline_res.text.replace(")]}',", "", 1)
        trend_json = json.loads(multiline_body)

        timeline_data = trend_json["default"]["timelineData"]
        trend = [{"date": point["formattedTime"], "interest": point["value"][0]} for point in timeline_data]

        return {"keyword": keyword, "trend": trend}

    except Exception as e:
        print(f"\n❌ Trend scraping error: {e}")
        return None

@app.route("/trend")
def get_trend():
    keyword = request.args.get("keyword", "").strip()
    trend_data = scrape_google_trends(keyword)
    if trend_data:
        return jsonify(trend_data)
    else:
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
