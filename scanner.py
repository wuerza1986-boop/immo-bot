import os
import threading
import time
import requests
from flask import Flask

app = Flask(__name__)

# Umgebungsvariablen aus Render laden
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


def background_deal_hunter():
  print("Hintergrund-Dienst gestartet...")
  # Test-Nachricht direkt beim Start senden, um zu prüfen, ob alles klappt
  send_telegram_message(
      "🤖 Deal Hunter Bot ist erfolgreich gestartet und überwacht den Markt!"
  )

  while True:
    # Hier läuft später deine Immobilien-Suche
    # Aktuelles Intervall: Alle 30 Minuten (1800 Sekunden)
    time.sleep(1800)


# Startet den Hintergrund-Dienst parallel zum Flask-Webserver
threading.Thread(target=background_deal_hunter, daemon=True).start()


@app.route("/")
def home():
  return "Hello, World! Immo-Bot ist live."


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
