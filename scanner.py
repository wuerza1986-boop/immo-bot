import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8322651200:AAHTVpUjCVUFk2PiAGItb_hhlaKtMB5Tuf0"
FIXED_CHAT_ID = "-10023456789"

@app.route("/", methods=["GET", "POST"])
def home():
    return "Immo Scraper active!", 200

@app.route("/scan", methods=["GET"])
def run_scan():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    text = (
        f"🚨 **IMMO DEAL GEFUNDEN!** 🚨\n\n"
        f"📍 **Stadt / QM Zielpreis:** Frankfurt am Main / 3.000 €/m²\n"
        f"💰 **Preis / QM Preis / -%:** 240.000 € / 2.526 €/m² / -15,8%\n"
        f"📐 **Quadratmeter:** 95 m²\n"
        f"🚪 **Zimmeranzahl:** 3 Zimmer\n"
        f"🏢 **Makler:** Ja\n"
        f"🔨 **Renovierungsbedürftig:** Nein\n"
        f"👤 **Kontaktdaten:** Immobilien Meyer GmbH\n"
        f"📞 **Telefonnummer:** [069 12345678](tel:+496912345678)\n\n"
        f"🔗 [Direktlink aufs Angebot](https://www.immobilienscout24.de)"
    )
    
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
        "chat_id": FIXED_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return jsonify({"status": "Test-Deal erfolgreich gesendet!"}), 200
    else:
        return jsonify({"status": "Fehler beim Senden", "details": response.text}), 500

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if not data:
        return jsonify({"status": "no data"}), 200

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

        edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        requests.post(edit_url, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": updated_text,
            "parse_mode": "Markdown"
        })

        answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, json={"callback_query_id": query_id, "text": "Status aktualisiert!"})

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
