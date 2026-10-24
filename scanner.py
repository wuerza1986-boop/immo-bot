import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8322651200:AAHTVpUjCVUFk2PiAGItb_hhlaKtMB5Tuf0"
FIXED_CHAT_ID = "-10023456789"
