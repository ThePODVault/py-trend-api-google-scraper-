from flask import Flask, request, jsonify
import requests
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

@app.route("/trend", methods=["GET"])
def get_trend():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"error": "Missing 'keyword' parameter"}), 400

    print(f"🔍 Scraping trends for: {keyword}")

    try:
        trends_url = (
            "https://trends.google.com/trends/api/explore"
            f"?hl=en-US&tz=360&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        )
        print(f"🧠 Widget URL: {trends_url}")

        widget_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}"
        )

        print(f"📥 Widget response: {widget_res.status_code}")

        raw_text = widget_res.text.strip()

        # Confirm prefix
        if raw_text.startswith(")]}'"):
            cleaned_json = raw_text[5:]  # Remove prefix and newline
        else:
            print("⚠️ Widget response missing expected prefix")
            raise Exception("Invalid widget response format")

        widgets = json.loads(cleaned_json)
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        print(f"✅ Widget token: {widget['token']}")

        multiline_url = (
            "https://trends.google.com/trends/api/widgetdata/multiline"
            f"?hl=en-US&tz=360&req={json.dumps(widget['request'])}"
            f"&token={widget['token']}&geo={widget['request'].get('geo', '')}"
        )
        print(f"📊 Data URL: {multiline_url}")

        multiline_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}"
        )
        print(f"📥 Multiline response: {multiline_res.status_code}")

        multiline_clean = multiline_res.text.strip()

        if multiline_clean.startswith(")]}'"):
            multiline_clean = multiline_clean[5:]

        trend_json = json.loads(multiline_clean)

        timeline_data = trend_json["default"]["timelineData"]
        trend = [
            {"date": entry["formattedTime"], "interest": entry["value"][0]}
            for entry in timeline_data
        ]

        return jsonify({"keyword": keyword, "trend": trend})

    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Flask is running on port {port}")
    app.run(host="0.0.0.0", port=port)
