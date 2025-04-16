from flask import Flask, request, jsonify
from flask_cors import CORS
from pytrends.request import TrendReq
import re

app = Flask(__name__)
CORS(app)

pytrends = TrendReq(hl='en-US', tz=360)

def clean_keyword(keyword):
    cleaned = re.sub(r'[^\w\s]', '', keyword.lower())
    parts = cleaned.split()
    filtered = [p for p in parts if len(p) > 2]
    return ' '.join(filtered[:3])

@app.route("/trend", methods=["GET"])
def get_trend():
    keyword = request.args.get("keyword", "")
    if not keyword:
        return jsonify({"error": "Missing keyword parameter"}), 400

    cleaned_keyword = clean_keyword(keyword)
    print(f"📥 Raw keyword: {keyword}\n -> Cleaned: {cleaned_keyword}")

    try:
        pytrends.build_payload([cleaned_keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
        data = pytrends.interest_over_time()

        if data.empty or 'isPartial' not in data.columns:
            return jsonify({"error": "No trend data found"}), 404

        trend = [
            {"date": date.strftime("%Y-%m-%d"), "interest": int(row[cleaned_keyword])}
            for date, row in data.iterrows()
        ]

        return jsonify({"keyword": cleaned_keyword, "trend": trend})

    except Exception as e:
        print(f"❌ Trend scraping error: {e}")
        return jsonify({"error": "Failed to fetch trend data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
