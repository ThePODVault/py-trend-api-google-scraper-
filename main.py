from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")  # Set this in Railway as an environment variable

def scrape_google_trends(keyword):
    try:
        print(f"🔍 Scraping trends for: {keyword}")

        # STEP 1: Get widget config
        explore_url = (
            "https://trends.google.com/trends/api/explore?hl=en-US&tz=360"
            f"&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        )
        explore_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={explore_url}",
            headers={"Accept": "application/json"},
        )
        print(f"📥 Widget response: {explore_res.status_code}")
        if explore_res.status_code != 200:
            raise Exception("Widget response not OK")

        cleaned = explore_res.text.replace(")]}',", "", 1)
        widgets = json.loads(cleaned)
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        token = widget["token"]
        print(f"✅ Widget token: {token}")

        # STEP 2: Get trend data
        data_url = (
            "https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(widget['request'])}&token={token}&geo="
        )
        data_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={data_url}",
            headers={"Accept": "application/json"},
        )
        print(f"📥 Data response: {data_res.status_code}")
        if data_res.status_code != 200:
            raise Exception("Data response not OK")

        cleaned_data = data_res.text.replace(")]}',", "", 1)
        timeline = json.loads(cleaned_data)["default"]["timelineData"]
        trend = [{"date": t["formattedTime"], "interest": t["value"][0]} for t in timeline]

        return trend
    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
        return None

@app.route("/trend", methods=["GET"])
def get_trend():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"error": "Missing 'keyword' parameter"}), 400

    trend_data = scrape_google_trends(keyword)
    if not trend_data:
        return jsonify({"error": "Failed to fetch trend data"}), 500

    return jsonify({"keyword": keyword, "trend": trend_data})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Flask is running on port {port}")
    app.run(host="0.0.0.0", port=port)
