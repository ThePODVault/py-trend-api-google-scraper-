from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def scrape_google_trends(keyword):
    try:
        print(f"🔍 Scraping trends for: {keyword}")

        # STEP 1: Get widget config
        trends_url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=360&req={{\"comparisonItem\":[{{\"keyword\":\"{keyword}\",\"geo\":\"\",\"time\":\"today 12-m\"}}],\"category\":0,\"property\":\"\"}}"
        print(f"🧠 Widget URL: {trends_url}")
        widget_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={trends_url}")
        print(f"📥 Widget response: {widget_res.status_code}")

        raw_text = widget_res.text.strip()
        if raw_text.startswith(")]}',"):
            cleaned_json = raw_text[len(")]}',"):].strip()
        else:
            print("⚠️ Widget response missing prefix")
            cleaned_json = raw_text

        if not cleaned_json:
            print("❌ Empty widget response.")
            return None
        if "<html" in cleaned_json.lower():
            print("❌ Google Trends returned HTML (block page for widgets):")
            print(cleaned_json[:1000])
            return None

        print("🔧 Raw widget preview:", cleaned_json[:300])
        widgets = json.loads(cleaned_json)

        # STEP 2: Get TIMESERIES widget
        widget = next(w for w in widgets["widgets"] if w["id"] == "TIMESERIES")
        print(f"✅ Widget token: {widget['token']}")

        # STEP 3: Fetch trend data
        multiline_url = (
            f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=360"
            f"&req={json.dumps(widget['request'])}&token={widget['token']}&geo={widget['request']['geo']}"
        )
        print(f"📊 Data URL: {multiline_url}")
        multiline_res = requests.get(f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={multiline_url}")
        print(f"📥 Multiline response: {multiline_res.status_code}")

        raw_multiline = multiline_res.text.strip()
        if raw_multiline.startswith(")]}',"):
            multiline_clean = raw_multiline[len(")]}',"):].strip()
        else:
            print("⚠️ Multiline response missing prefix")
            multiline_clean = raw_multiline

        if not multiline_clean:
            print("❌ Empty multiline response.")
            return None
        if "<html" in multiline_clean.lower():
            print("❌ Google Trends returned HTML (block page for multiline):")
            print(multiline_clean[:1000])
            return None

        print("🔧 Raw multiline preview:", multiline_clean[:300])

        try:
            trend_json = json.loads(multiline_clean)
        except json.JSONDecodeError as e:
            print("❌ Multiline JSON decode error:", e)
            print(multiline_clean[:1000])
            return None

        timeline_data = trend_json["default"]["timelineData"]
        trend = [
            {"date": entry["formattedTime"], "interest": entry["value"][0]}
            for entry in timeline_data
        ]

        return trend

    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
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
