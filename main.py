import json
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

@app.route("/trend", methods=["GET"])
def get_trend():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"error": "Missing keyword"}), 400

    try:
        print(f"🔍 Scraping trends for: {keyword}")

        # Step 1: Get widget config
        trends_url = (
            f"https://trends.google.com/trends/api/explore?hl=en-US&tz=360&req="
            f"{{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        )
        print(f"🧠 Widget URL: {trends_url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        widget_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}",
            headers=headers
        )
        print(f"📥 Widget response: {widget_res.status_code}")
        print(f"📥 Raw widget text (first 500 chars):\n{widget_res.text[:500]}")

        cleaned_json = widget_res.text.replace(")]}',", "").strip()
        if not cleaned_json or cleaned_json.startswith("<"):
            print("❌ Widget response is invalid or HTML")
            return jsonify({"error": "Invalid response from Google Trends"}), 500

        widgets = json.loads(cleaned_json)

        # Step 2: Extract TIMESERIES widget
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        token = widget["token"]
        print(f"✅ Widget token: {token}")

        multiline_url = (
            "https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(widget['request'])}&token={token}&geo="
        )
        print(f"📊 Data URL: {multiline_url}")

        multiline_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}",
            headers=headers
        )
        print(f"📥 Multiline response: {multiline_res.status_code}")
        cleaned_multiline = multiline_res.text.replace(")]}',", "").strip()

        if not cleaned_multiline or cleaned_multiline.startswith("<"):
            print("❌ Multiline response is invalid or HTML")
            return jsonify({"error": "Invalid trend data"}), 500

        trend_json = json.loads(cleaned_multiline)
        timeline_data = trend_json["default"]["timelineData"]

        trend = [
            {"date": point["formattedTime"], "interest": point["value"][0]}
            for point in timeline_data
        ]

        return jsonify({"keyword": keyword, "trend": trend})

    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Flask is running on port {port}")
    app.run(host="0.0.0.0", port=port)
