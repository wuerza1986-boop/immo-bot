import os
import math
import sqlite3
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Telegram Bot Token aus Umgebungsvariablen holen
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

# --- DATENBANK-SETUP ---
def init_db():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Tabelle für deine FIXEN Anker-Städte
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anker_staedte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stadt TEXT UNIQUE NOT NULL,
            ziel_qmp REAL NOT NULL,
            markt_qmp REAL NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    ''')
    
    # 2. Tabelle für Marktpreise
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ort_marktpreise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ort TEXT UNIQUE NOT NULL,
            aktueeller_markt_qmp REAL NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    ''')

    # 3. Tabelle für Deals mit allen Status-Spalten (inkl. todo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT,
            ort TEXT,
            anker_stadt TEXT,
            preis REAL,
            flaeche REAL,
            qmp REAL,
            link TEXT UNIQUE,
            angerufen INTEGER DEFAULT 0,
            besichtigung INTEGER DEFAULT 0,
            favorit INTEGER DEFAULT 0,
            abgelehnt INTEGER DEFAULT 0,
            todo INTEGER DEFAULT 0,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Falls die Tabelle schon existierte, fügen wir die Spalte 'todo' falls nötig per ALTER TABLE hinzu
    try:
        cursor.execute("ALTER TABLE deals ADD COLUMN todo INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Spalte existiert bereits
    
    # Initiale 8 Anker-Städte eintragen
    initial_ankers = [
        ("Hanau", 1800, 2200, 50.1328, 8.9169),
        ("Dietzenbach", 1750, 2150, 50.0086, 8.7758),
        ("Offenbach", 2300, 2950, 50.1055, 8.7662),
        ("Frankfurt", 2600, 3200, 50.1109, 8.6821),
        ("Oberursel", 2750, 5500, 50.2014, 8.5739),
        ("Bad Homburg", 2750, 5200, 50.2268, 8.6181),
        ("Steinbach", 2750, 4800, 50.1681, 8.5714),
        ("Langen", 1900, 2400, 49.9889, 8.6631)
    ]
    
    for stadt, ziel, markt, lat, lon in initial_ankers:
        cursor.execute('''
            INSERT OR IGNORE INTO anker_staedte (stadt, ziel_qmp, markt_qmp, lat, lon)
            VALUES (?, ?, ?, ?, ?)
        ''', (stadt, ziel, markt, lat, lon))
        
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("index.html")

# API: Anker-Städte abrufen
@app.route('/api/anker', methods=['GET'])
def get_ankers():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id, stadt, ziel_qmp, markt_qmp FROM anker_staedte")
    rows = cursor.fetchall()
    conn.close()
    
    ankers = []
    for r in rows:
        rabatt = ((r[2] - r[3]) / r[3]) * 100
        ankers.append({
            "id": r[0],
            "stadt": r[1],
            "ziel_qmp": r[2],
            "markt_qmp": r[3],
            "rabatt_prozent": round(rabatt, 1)
        })
    return jsonify(ankers)

# API: Anker-Wert aktualisieren
@app.route('/api/anker/<int:anker_id>', methods=['PUT'])
def update_anker(anker_id):
    data = request.json
    neuer_ziel_qmp = data.get('ziel_qmp')
    
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE anker_staedte SET ziel_qmp = ? WHERE id = ?", (neuer_ziel_qmp, anker_id))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "Anker erfolgreich aktualisiert!"})

# API: Deals abrufen (inklusive To-Do Status)
@app.route('/api/deals', methods=['GET'])
def get_deals():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titel, ort, anker_stadt, preis, flaeche, qmp, link, 
               angerufen, besichtigung, favorit, abgelehnt, todo 
        FROM deals ORDER BY id DESC LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    
    deals = []
    for r in rows:
        deals.append({
            "id": r[0],
            "titel": r[1],
            "ort": r[2],
            "anker_stadt": r[3],
            "preis": r[4],
            "flaeche": r[5],
            "qmp": r[6],
            "link": r[7],
            "angerufen": r[8],
            "besichtigung": r[9],
            "favorit": r[10],
            "abgelehnt": r[11],
            "todo": r[12]
        })
    return jsonify(deals)

# TELEGRAM WEBHOOK: Verarbeitet Button-Klicks (inkl. To-Do)
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or 'callback_query' not in data:
        return jsonify({"status": "ignored"})
    
    callback_query = data['callback_query']
    callback_data = callback_query['data']  # z.B. "todo_12" oder "favorit_12"
    message = callback_query['message']
    chat_id = message['chat']['id']
    message_id = message['message_id']
    query_id = callback_query['id']
    
    parts = callback_data.split('_')
    if len(parts) == 2:
        action, deal_id_str = parts
        # Sicherheitsprüfung, ob die Aktion erlaubt ist
        if action not in ['angerufen', 'besichtigung', 'favorit', 'abgelehnt', 'todo']:
            return jsonify({"status": "invalid action"})
            
        try:
            deal_id = int(deal_id_str)
        except ValueError:
            return jsonify({"status": "invalid id"})
        
        conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
        cursor = conn.cursor()
        
        # Aktuellen Status aus der DB holen
        cursor.execute(f"SELECT {action} FROM deals WHERE id = ?", (deal_id,))
        row = cursor.fetchone()
        
        if row is not None:
            current_val = row[0]
            new_val = 0 if current_val == 1 else 1  # Umschalten (Toggle)
            
            # In DB speichern
            cursor.execute(f"UPDATE deals SET {action} = ? WHERE id = ?", (new_val, deal_id))
            conn.commit()
            
            # Alle Statuswerte für die Buttons neu laden
            cursor.execute("SELECT angerufen, besichtigung, favorit, abgelehnt, todo FROM deals WHERE id = ?", (deal_id,))
            st = cursor.fetchone()
            conn.close()
            
            ang, bes, fav, abg, todo_val = st
            
            # Schönes Tastatur-Layout mit 5 Buttons (2 oben, 2 mitte, 1 unten)
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": f"📞 Angerufen {'✅' if ang else ''}", "callback_data": f"angerufen_{deal_id}"},
                        {"text": f"👀 Besichtigung {'✅' if bes else ''}", "callback_data": f"besichtigung_{deal_id}"}
                    ],
                    [
                        {"text": f"⭐ Favorit {'✅' if fav else ''}", "callback_data": f"favorit_{deal_id}"},
                        {"text": f"📋 To-Do {'✅' if todo_val else ''}", "callback_data": f"todo_{deal_id}"}
                    ],
                    [
                        {"text": f"❌ Abgelehnt {'✅' if abg else ''}", "callback_data": f"abgelehnt_{deal_id}"}
                    ]
                ]
            }
            
            # Nachricht bei Telegram aktualisieren
            if TELEGRAM_TOKEN:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "reply_markup": keyboard
                    }
                )
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": query_id, "text": "To-Do Status aktualisiert!" if action=='todo' else "Status aktualisiert!"}
                )

    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
