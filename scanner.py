import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8322651200:AAHTVpUjCVUFk2PiAGItb_hhlaKtMB5Tuf0"
last_chat_id = None

@app.route("/", methods=["GET", "POST"])
def home():
    return f"Immo Scraper active! Letzte erkannte Chat-ID: {last_chat_id}", 200

@app.route("/scan", methods=["GET"])
def run_scan():
    global last_chat_id
    if not last_chat_id:
        return jsonify({"status": "Fehler", "details": "Keine Chat-ID vorhanden! Schreibe bitte zuerst eine Nachricht in deine Gruppe."}), 400

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Layout mit prozentualer Abweichung als Top-Überschrift
    text = (
        f"🔥 **-15,4% unter Zielpreis!**\n"
        f"🏙️ Frankfurt (Ziel-QMP: 2600€)\n"
        f"📍 Frankfurt Griesheim\n"
        f"💰 200.000€ (QMP: 2200€)\n"
        f"🚪 3 Zimmer Wohnung\n"
        f"📐 75 QM\n"
        f"🔨 Renovierungsbedürftig: Ja\n"
        f"👤 Anbieter: Privat\n"
        f"📞 069 12345678\n\n"
        f"🔗 [Direktlink zum Angebot](https://www.immobilienscout24.de)"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "Angerufen", "callback_data": "status_angerufen"},
                {"text": "Besichtigung", "callback_data": "status_besichtigung"}
            ],
            [
                {"text": "Favorit", "callback_data": "status_favorit"},
                {"text": "Abgelehnt", "callback_data": "status_abgelehnt"}
            ]
        ]
    }
    
    payload = {
        "chat_id": last_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return jsonify({"status": "Test-Deal erfolgreich gesendet!"}), 200
    else:
        return jsonify({"status": "Fehler beim Senden", "details": response.text}), 500

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    global last_chat_id
    data = request.get_json()
    if not data:
        return jsonify({"status": "no data"}), 200

    if "message" in data:
        chat = data["message"]["chat"]
        last_chat_id = str(chat["id"])
    elif "callback_query" in data:
        query = data["callback_query"]
        query_id = query["id"]
        action = query["data"]
        message = query["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        last_chat_id = str(chat_id)
        original_text = message.get("text", "")

        status_text = ""
        if action == "status_angerufen":
            status_text = "\n\n📌 Status: Angerufen"
        elif action == "status_besichtigung":
            status_text = "\n\n📌 Status: Besichtigung"
        elif action == "status_favorit":
            status_text = "\n\n📌 Status: Favorit"
        elif action == "status_abgelehnt":
            status_text = "\n\n📌 Status: Abgelehnt"

        updated_text = original_text + status_text

        edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        requests.post(edit_url, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": updated_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        })

        answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, json={"callback_query_id": query_id, "text": "Status aktualisiert!"})

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
