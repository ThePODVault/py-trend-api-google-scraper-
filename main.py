from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def scrape_google_trends(keyword):
    try:
        trends_url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=360&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        widget_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}")
        cleaned_json = widget_res.text.replace(")]}',", "")
        widgets = json.loads(cleaned_json)
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")

        multiline_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(widget['request'])}&token={widget['token']}&geo={widget['request']['geo']}"
        )
        multiline_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}")
        multiline_clean = multiline_res.text.replace(")]}',", "")
        trend_json = json.loads(multiline_clean)

        timeline_data = trend_json["default"]["timelineData"]
        trend = [
            {"date": entry["formattedTime"], "interest": entry["value"][0]}
            for entry in timeline_data
        ]

        return trend
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

@app.route("/trend", methods=["GET"])
def get_trend():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"error": "Missing 'keyword' parameter"}), 400

    trend = scrape_google_trends(keyword)
    if not trend:
        return jsonify({"error": "Failed to fetch trend data"}), 500

    return jsonify({"keyword": keyword, "trend": trend})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Flask is running on port {port}")
    app.run(host="0.0.0.0", port=port)
