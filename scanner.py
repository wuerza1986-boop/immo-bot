import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# CONFIGURATION
TELEGRAM_TOKEN = "8322651200:AAHTVpUjCV"
CHAT_ID = "-1004495350584"

# TARGET m² PRICES IN EUR
TARGET_PRICES = {
    "Hanau": 1800,
    "Dietzenbach": 1750,
    "Offenbach": 2300,
    "Frankfurt": 2600,
    "Oberursel": 2750,
    "Bad Homburg": 2750,
    "Steinbach": 2750,
    "Langen": 1900
}

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "bot": "Immo Deal Hunter",
        "monitored_cities": list(TARGET_PRICES.keys())
    })

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if "callback_query" in data:
        query = data["callback_query"]
        callback_data = query["data"]
        message = query["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        
        # Status Mapping
        status_map = {
            "btn_call": "Angerufen 📞",
            "btn_view": "Besichtigung 📅",
            "btn_fav": "Favorit ⭐",
            "btn_reject": "Abgelehnt ❌"
        }
        
        new_status = status_map.get(callback_data, "Unbekannt")
        
        # Answer callback to remove loading animation on button
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": query["id"],
            "text": f"Status aktualisiert: {new_status}"
        })
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "ignored"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
