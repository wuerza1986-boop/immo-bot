import os
import math
import sqlite3
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- DATENBANK-SETUP ---
def init_db():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Tabelle für deine FIXEN Anker-Städte (Nur manuell durch dich veränderbar)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anker_staedte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stadt TEXT UNIQUE NOT NULL,
            ziel_qmp REAL NOT NULL,      -- Dein fester Wunsch-Quadratmeterpreis (Heilig!)
            markt_qmp REAL NOT NULL,     -- Offizieller Marktpreis der Ankerstadt zum Zeitpunkt der Definition
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    ''')
    
    # 2. Tabelle für die offiziellen Marktpreise aller Orte, Dörfer & Städte im Umland
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ort_marktpreise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ort TEXT UNIQUE NOT NULL,
            aktueeller_markt_qmp REAL NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    ''')

    # 3. Tabelle für gefundene Immobilien-Deals
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
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initiale 8 Anker-Städte eintragen (Falls noch nicht vorhanden)
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

# Datenbank beim Start initialisieren
init_db()

def berechne_entfernung(lat1, lon1, lat2, lon2):
    """Berechnet die Distanz in km zwischen zwei Koordinaten."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 6371 * c

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

# API: Anker-Wert manuell aktualisieren
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

# API: Gefundene Deals für das Dashboard abrufen
@app.route('/api/deals', methods=['GET'])
def get_deals():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT titel, ort, anker_stadt, preis, flaeche, qmp, link FROM deals ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    
    deals = []
    for r in rows:
        deals.append({
            "titel": r[0],
            "ort": r[1],
            "anker_stadt": r[2],
            "preis": r[3],
            "flaeche": r[4],
            "qmp": r[5],
            "link": r[6]
        })
    return jsonify(deals)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
