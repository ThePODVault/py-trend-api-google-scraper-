from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

app = Flask(__name__)
CORS(app)  # ✅ Enables CORS for all domains

@app.route("/trend", methods=["GET"])
def get_trend():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"error": "Missing keyword"}), 400

    try:
        print(f"🔍 Scraping trends for: {keyword}")

        trends_url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=360&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        widget_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}")
        cleaned_json = widget_res.text.replace(")]}',", "").strip()
        widgets = json.loads(cleaned_json)

        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        token = widget["token"]
        req = widget["request"]
        geo = req.get("geo", {}).get("country", "")

        multiline_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(req)}&token={token}&geo={geo}"
        )
        multiline_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}")
        multiline_clean = multiline_res.text.replace(")]}',", "").strip()
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
