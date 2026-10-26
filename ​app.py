import os
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
from bs4 import BeautifulSoup

app = Flask(__name__)

# Konfiguration
TELEGRAM_BOT_TOKEN = "7547633633:AAGYJ45T_21J5T7o2M8x3W8Y1Qz9K2v8l3c"
TELEGRAM_CHAT_ID = "5745129668"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

def init_db():
    conn = sqlite3.connect("deal_hunter.db")
    cursor = conn.cursor()
    # Erweiterte Tabelle für Anker-Städte mit QMP-Werten
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anker_staedte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stadt TEXT UNIQUE NOT NULL,
            markt_qmp REAL DEFAULT 3500,
            ziel_qmp REAL DEFAULT 2800,
            rabatt_prozent REAL DEFAULT -20.0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            location TEXT,
            link TEXT UNIQUE,
            status TEXT DEFAULT 'Neu'
        )
    """)
    conn.commit()
    
    # Standard-Ankerstadt Frankfurt hinzufügen, falls noch keine da ist
    cursor.execute("SELECT COUNT(*) FROM anker_staedte")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO anker_staedte (stadt, markt_qmp, ziel_qmp, rabatt_prozent) VALUES (?, ?, ?, ?)",
            ("Frankfurt am Main", 4500, 3600, -20.0)
        )
        conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

# API für das neue Frontend (Anker-Städte abrufen)
@app.route("/api/anker", methods=["GET"])
def get_anker():
    conn = sqlite3.connect("deal_hunter.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, stadt, markt_qmp, ziel_qmp, rabatt_prozent FROM anker_staedte")
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            "id": row[0],
            "stadt": row[1],
            "markt_qmp": row[2],
            "ziel_qmp": row[3],
            "rabatt_prozent": row[4]
        })
    return jsonify(data)

# API zum Aktualisieren des Ziel-QMP
@app.route("/api/anker/<int:anker_id>", methods=["PUT"])
def update_anker(anker_id):
    req_data = request.get_json()
    new_ziel_qmp = req_data.get("ziel_qmp")
    
    if new_ziel_qmp is not None:
        conn = sqlite3.connect("deal_hunter.db")
        cursor = conn.cursor()
        
        # Markt-QMP auslesen, um den Rabatt prozentual zu berechnen
        cursor.execute("SELECT markt_qmp FROM anker_staedte WHERE id = ?", (anker_id,))
        row = cursor.fetchone()
        if row:
            markt_qmp = row[0]
            neu_rabatt = round(((new_ziel_qmp - markt_qmp) / markt_qmp) * 100, 1)
            
            cursor.execute(
                "UPDATE anker_staedte SET ziel_qmp = ?, rabatt_prozent = ? WHERE id = ?",
                (new_ziel_qmp, neu_rabatt, anker_id)
            )
            conn.commit()
        conn.close()
        return jsonify({"success": True})
    
    return jsonify({"success": False}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
