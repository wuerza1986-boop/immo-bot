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
    
    # Telefonnummer komplett freistehend mit Leerzeilen davor und danach für perfekte Erkennung
    text = (
        f"🕒 **Online seit:** 24.10.2026, 21:43 Uhr\n"
        f"🔥 **-15,4% unter Zielpreis!**\n"
        f"📌 **Status:** Noch offen\n"
        f"🏙️ Frankfurt (Ziel-QMP: 2600€)\n"
        f"📍 Frankfurt Griesheim\n"
        f"💰 200.000€ (QMP: 2200€)\n"
        f"🚪 3 Zimmer Wohnung\n"
        f"📐 75 QM\n"
        f"🔨 Renovierungsbedürftig: Ja\n"
        f"👤 Anbieter: Privat\n\n"
        f"📞 06912345678\n\n"
        f"🔗 [Direktlink zum Angebot](https://www.immobilienscout24.de)"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "📞 Angerufen", "callback_data": "toggle_angerufen"},
                {"text": "👀 Besichtigung", "callback_data": "toggle_besichtigung"}
            ],
            [
                {"text": "⭐ Favorit", "callback_data": "toggle_favorit"},
                {"text": "❌ Abgelehnt", "callback_data": "toggle_abgelehnt"}
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
        current_markup = message.get("reply_markup", {}).get("inline_keyboard", [])

        is_angerufen = False
        is_besichtigung = False
        is_favorit = False
        is_abgelehnt = False

        for row in current_markup:
            for btn in row:
                cb = btn["callback_data"]
                txt = btn["text"]
                if cb == "toggle_angerufen" and "✅" in txt: is_angerufen = True
                if cb == "toggle_besichtigung" and "✅" in txt: is_besichtigung = True
                if cb == "toggle_favorit" and "✅" in txt: is_favorit = True
                if cb == "toggle_abgelehnt" and "✅" in txt: is_abgelehnt = True

        if action == "toggle_angerufen":
            is_angerufen = not is_angerufen
            if is_angerufen: is_abgelehnt = False
        elif action == "toggle_besichtigung":
            is_besichtigung = not is_besichtigung
        elif action == "toggle_favorit":
            is_favorit = not is_favorit
        elif action == "toggle_abgelehnt":
            is_abgelehnt = not is_abgelehnt
            if is_abgelehnt:
                is_angerufen = False
                is_besichtigung = False
                is_favorit = False

        b_angerufen = "✅ Angerufen" if is_angerufen else "📞 Angerufen"
        b_besichtigung = "✅ Besichtigung" if is_besichtigung else "👀 Besichtigung"
        b_favorit = "✅ Favorit" if is_favorit else "⭐ Favorit"
        b_abgelehnt = "✅ Abgelehnt" if is_abgelehnt else "❌ Abgelehnt"

        new_reply_markup = {
            "inline_keyboard": [
                [
                    {"text": b_angerufen, "callback_data": "toggle_angerufen"},
                    {"text": b_besichtigung, "callback_data": "toggle_besichtigung"}
                ],
                [
                    {"text": b_favorit, "callback_data": "toggle_favorit"},
                    {"text": b_abgelehnt, "callback_data": "toggle_abgelehnt"}
                ]
            ]
        }

        active_statuses = []
        if is_angerufen: active_statuses.append("📞 Angerufen")
        if is_besichtigung: active_statuses.append("👀 Besichtigung")
        if is_favorit: active_statuses.append("⭐ Favorit")
        if is_abgelehnt: active_statuses.append("❌ Abgelehnt")

        status_str = ", ".join(active_statuses) if active_statuses else "Noch offen"

        lines = original_text.split("\n")
        updated_lines = []
        
        for line in lines:
            if "Status:" in line:
                continue
            updated_lines.append(line)
            
        if len(updated_lines) > 1:
            updated_lines.insert(2, f"📌 **Status:** {status_str}")
        else:
            updated_lines.append(f"📌 **Status:** {status_str}")

        updated_text = "\n".join(updated_lines)

        edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        requests.post(edit_url, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": updated_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "reply_markup": new_reply_markup
        })

        answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, json={"callback_query_id": query_id, "text": f"Status aktualisiert: {status_str}"})

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
