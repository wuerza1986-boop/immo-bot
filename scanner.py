import os
import requests
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
  token = os.environ.get("TELEGRAM_BOT_TOKEN")
  chat_id = os.environ.get("TELEGRAM_GROUP_ID")

  if not token or not chat_id:
    return (
        "Fehler: TELEGRAM_BOT_TOKEN oder TELEGRAM_GROUP_ID fehlen in Render!"
    )

  url = f"https://api.telegram.org/bot{token}/sendMessage"
  payload = {
      "chat_id": chat_id,
      "text": "🤖 Test erfolgreich! Verbindung steht.",
  }

  try:
    response = requests.post(url, json=payload)
    return f"Telegram API Antwort: {response.text}"
  except Exception as e:
    return f"Fehler beim Senden: {str(e)}"


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
