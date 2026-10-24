import os
import requests
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
  # Direkt hartcodiert zum Testen:
  token = "8322651200:AAEo1XuXZF5webGi1EW1tWSRnKk6bcx61c"
  chat_id = "-1004495350584"

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
