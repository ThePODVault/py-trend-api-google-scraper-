from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")  # Set this in Railway environment variables

def scrape_google_trends(keyword):
    try:
        print(f"🔍 Scraping trends for: {keyword}")

        # Step 1: Get widget config
        explore_url = (
            "https://trends.google.com/trends/api/explore?hl=en-US&tz=360"
            f"&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        )
        widget_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={explore_url}"
        )

        print(f"📥 Widget response: {widget_res.status_code}")
        raw_text = widget_res.text.strip()

        if not raw_text or not raw_text.startswith(")]}'"):
            print("❌ Widget response missing expected prefix or empty")
            print(f"🔧 Raw widget response (first 500): {raw_text[:500]}")
            raise Exception("Widget data format invalid or blocked")

        cleaned_json = raw_text.replace(")]}',", "", 1)
        widgets = json.loads(cleaned_json)
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        token = widget["token"]

        print(f"✅ Widget token: {token}")

        # Step 2: Get trend data
        data_url = (
            "https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(widget['request'])}&token={token}&geo="
        )
        data_res = requests.get(
            f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={data_url}"
        )

        print(f"📥 Data response: {data_res.status_code}")
        raw_data = data_res.text.strip()

        if not raw_data or not raw_data.startswith(")]}'"):
            print("❌ Data response missing expected prefix or empty")
            print(f"🔧 Raw data response (first 500): {raw_data[:500]}")
            raise Exception("Trend data format invalid or blocked")

        cleaned_data = raw_data.replace(")]}',", "", 1)
        parsed_data = json.loads(cleaned_data)
        timeline = parsed_data["default"]["timelineData"]

        return [{"date": t["formattedTime"], "interest": t["value"][0]} for t in timeline]

    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
        return None

@app.route("/trend", methods=["GET"])
def get_trend():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "Missing keyword"}), 400

    trend = scrape_google_trends(keyword)
    if trend is None:
        return jsonify({"error": "Failed to fetch trend data"}), 500

    return jsonify({"keyword": keyword, "trend": trend})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Flask is running on port {port}")
    app.run(host="0.0.0.0", port=port)
