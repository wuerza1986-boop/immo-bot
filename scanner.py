import os
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8322651200:AAHTVpUjCVUFk2PiAGItb_hhlaKtMB5Tuf0")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-10023456789") # Deine Gruppen/Chat ID

# Baselines in €/m²
BASELINES = {
    "hanau": 1800,
    "dietzenbach": 1750,
    "offenbach": 2300,
    "frankfurt": 2600,
    "oberursel": 2750,
    "bad homburg": 2750,
    "steinbach": 2750,
    "langen": 1900
}

def send_telegram_deal(title, price, sqm, price_per_sqm, city, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    text = (
        f"🚨 **IMMO DEAL GEFUNDEN!** 🚨\n\n"
        f"📍 **Stadt:** {city.capitalize()}\n"
        f"🏠 **Titel:** {title}\n"
        f"💰 **Preis:** {price:,.0f} €\n"
        f"📐 **Fläche:** {sqm} m²\n"
        f"📊 **Quadratmeterpreis:** {price_per_sqm:,.0f} €/m²\n\n"
        f"🔗 [Zum Angebot]({link})"
    )
    
    # Inline Status-Buttons
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "📞 Angerufen", "callback_data": "status_angerufen"},
                {"text": "👁️ Besichtigung", "callback_data": "status_besichtigung"}
            ],
            [
                {"text": "⭐ Favorit", "callback_data": "status_favorit"},
                {"text": "❌ Abgelehnt", "callback_data": "status_abgelehnt"}
            ]
        ]
    }
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    
    requests.post(url, json=payload)

@app.route("/", methods=["GET", "POST"])
def home():
    return "Immo Scraper is active!", 200

# Scanner Endpunkt
@app.route("/scan", methods=["GET"])
def run_scan():
    # Hier führt der Scraper die Suche aus und sendet gefundene Deals direkt an Telegram
    # Beispiel-Meldung zum Bestätigen des Sofort-Scans:
    return jsonify({"status": "Scan gestartet"}), 200

# Telegram Webhook Callback Handler
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if not data:
        return jsonify({"status": "no data"}), 200

    # Inline-Button Klicks verarbeiten
    if "callback_query" in data:
        query = data["callback_query"]
        query_id = query["id"]
        action = query["data"]
        message = query["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        original_text = message.get("text", "")

        status_text = ""
        if action == "status_angerufen":
            status_text = "\n\n📌 **Status:** 📞 Angerufen"
        elif action == "status_besichtigung":
            status_text = "\n\n📌 **Status:** 👁️ Besichtigung vereinbart"
        elif action == "status_favorit":
            status_text = "\n\n📌 **Status:** ⭐ Favorit"
        elif action == "status_abgelehnt":
            status_text = "\n\n📌 **Status:** ❌ Abgelehnt"

        updated_text = original_text + status_text

        # Nachricht in Telegram aktualisieren
        edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        requests.post(edit_url, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": updated_text,
            "parse_mode": "Markdown"
        })

        # Answer Callback Query
        answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, json={"callback_query_id": query_id, "text": "Status aktualisiert!"})

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
