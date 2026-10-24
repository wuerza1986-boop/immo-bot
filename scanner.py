import os
import requests
from flask import Flask

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_GROUP_ID = os.environ.get("TELEGRAM_GROUP_ID")


def send_telegram_message(text):
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_GROUP_ID:
    print("Telegram-Zugangsdaten fehlen!")
    return
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_GROUP_ID, "text": text}
  try:
    response = requests.post(url, json=payload)
    print("Telegram Antwort:", response.text)
  except Exception as e:
    print("Fehler beim Senden der Telegram-Nachricht:", e)


# Einmalige Startnachricht direkt beim Start senden
send_telegram_message(
    "🤖 Deal Hunter Bot ist erfolgreich gestartet und überwacht den Markt!"
)


@app.route("/")
def home():
  return "Immo Deal Hunter Bot läuft aktiv."


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
