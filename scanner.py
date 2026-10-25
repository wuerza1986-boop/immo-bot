import os
import sqlite3
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ==========================================
# FESTE KONFIGURATION
# ==========================================
TELEGRAM_TOKEN = "8322651200:AAGmeU2XEF2frad2d9eVf2nMgEr2K8Ws7BQ"
TELEGRAM_CHAT_ID = "-1004495350584"
# ==========================================

def init_db():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ort_marktpreise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ort TEXT UNIQUE NOT NULL,
            aktueeller_markt_qmp REAL NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    ''')

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
    
    try:
        cursor.execute("ALTER TABLE deals ADD COLUMN todo INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
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

# HTML DASHBOARD TEMPLATE
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Immo Deal Hunter Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: auto; }
        h1 { color: #2c3e50; font-size: 24px; margin-bottom: 5px; }
        p.subtitle { color: #7f8c8d; margin-top: 0; margin-bottom: 25px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 25px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ecf0f1; font-size: 14px; }
        th { background-color: #f8f9fa; color: #2c3e50; font-weight: 600; }
        tr:hover { background-color: #f9fbfd; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; display: inline-block; margin-right: 3px; }
        .badge-yes { background-color: #e1f5fe; color: #0288d1; }
        .badge-fav { background-color: #fff8e1; color: #fbc02d; }
        .badge-no { background-color: #ffebee; color: #c62828; }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Immo Deal Hunter Dashboard</h1>
        <p class="subtitle">Echtzeit-Übersicht deiner erfassten Immobilien-Deals & Status</p>
        
        <div class="card">
            <h3>🔥 Aktuelle Deals</h3>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Titel / Ort</th>
                            <th>Anker</th>
                            <th>Preis</th>
                            <th>Fläche</th>
                            <th>QMP</th>
                            <th>Status / Badges</th>
                            <th>Link</th>
                        </tr>
                    </thead>
                    <tbody id="deals-table">
                        <tr><td colspan="8" style="text-align:center;">Lade Deals...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        async function loadDeals() {
            try {
                const response = await fetch('/api/deals');
                const deals = await response.json();
                const tbody = document.getElementById('deals-table');
                
                if (deals.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Keine Deals gefunden.</td></tr>';
                    return;
                }
                
                tbody.innerHTML = '';
                deals.forEach(deal => {
                    let badges = '';
                    if (deal.favorit) badges += '<span class="badge badge-fav">⭐ Favorit</span>';
                    if (deal.angerufen) badges += '<span class="badge badge-yes">📞 Angerufen</span>';
                    if (deal.besichtigung) badges += '<span class="badge badge-yes">👀 Besichtigung</span>';
                    if (deal.todo) badges += '<span class="badge badge-yes">📋 To-Do</span>';
                    if (deal.abgelehnt) badges += '<span class="badge badge-no">❌ Abgelehnt</span>';
                    if (!badges) badges = '<span style="color: #95a5a6;">Neu / Offen</span>';

                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>#${deal.id}</td>
                        <td><strong>${deal.titel || 'Immobilie'}</strong><br><small style="color:#7f8c8d;">${deal.ort || '-'}</small></td>
                        <td>${deal.anker_stadt || '-'}</td>
                        <td><strong>${deal.preis ? deal.preis.toLocaleString() + ' €' : '-'}</strong></td>
                        <td>${deal.flaeche ? deal.flaeche + ' m²' : '-'}</td>
                        <td>${deal.qmp ? Math.round(deal.qmp).toLocaleString() + ' €/m²' : '-'}</td>
                        <td>${badges}</td>
                        <td>${deal.link ? `<a href="${deal.link}" target="_blank">Ansehen 🔗</a>` : '-'}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (err) {
                console.error('Fehler beim Laden der Deals:', err);
            }
        }
        loadDeals();
        setInterval(loadDeals, 5000); // Alle 5 Sekunden automatisch aktualisieren
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(DASHBOARD_HTML)

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

@app.route('/api/deal/add', methods=['POST'])
def add_deal():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Keine Daten übergeben"}), 400
        
    titel = data.get('titel')
    ort = data.get('ort')
    anker_stadt = data.get('anker_stadt')
    preis = data.get('preis')
    flaeche = data.get('flaeche')
    link = data.get('link')
    
    if not all([preis, flaeche, link]):
        return jsonify({"error": "Pflichtfelder fehlen (preis, flaeche, link)"}), 400
        
    qmp = preis / flaeche if flaeche > 0 else 0
    
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO deals (titel, ort, anker_stadt, preis, flaeche, qmp, link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (titel, ort, anker_stadt, preis, flaeche, qmp, link))
        conn.commit()
        deal_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Deal mit diesem Link existiert bereits"}), 400
    
    conn.close()
    
    if TELEGRAM_CHAT_ID:
        text = (
            f"🔥 **NEUER DEAL GEFUNDEN** 🔥\n"
            f"🏙️ Anker: {anker_stadt}\n"
            f"📍 Ort: {ort}\n"
            f"💰 Preis: {preis:,.2f}€ (QMP: {qmp:,.2f}€)\n"
            f"📐 Fläche: {flaeche} m²\n"
            f"🔗 [Zum Angebot]({link})"
        )
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📞 Angerufen", "callback_data": f"angerufen_{deal_id}"},
                    {"text": "👀 Besichtigung", "callback_data": f"besichtigung_{deal_id}"}
                ],
                [
                    {"text": "⭐ Favorit", "callback_data": f"favorit_{deal_id}"},
                    {"text": "📋 To-Do", "callback_data": f"todo_{deal_id}"}
                ],
                [
                    {"text": "❌ Abgelehnt", "callback_data": f"abgelehnt_{deal_id}"}
                ]
            ]
        }
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
        )

    return jsonify({"status": "success", "deal_id": deal_id}), 201

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or 'callback_query' not in data:
        return jsonify({"status": "ignored"})
    
    callback_query = data['callback_query']
    callback_data = callback_query['data']
    message = callback_query['message']
    chat_id = message['chat']['id']
    message_id = message['message_id']
    query_id = callback_query['id']
    
    parts = callback_data.split('_')
    if len(parts) == 2:
        action, deal_id_str = parts
        if action not in ['angerufen', 'besichtigung', 'favorit', 'abgelehnt', 'todo']:
            return jsonify({"status": "invalid action"})
            
        try:
            deal_id = int(deal_id_str)
        except ValueError:
            return jsonify({"status": "invalid id"})
        
        conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
        cursor = conn.cursor()
        
        # Aktuellen Wert auslesen
        cursor.execute(f"SELECT {action} FROM deals WHERE id = ?", (deal_id,))
        row = cursor.fetchone()
        
        if row is not None:
            current_val = row[0]
            new_val = 0 if current_val == 1 else 1
            
            # Wert umschalten und speichern
            cursor.execute(f"UPDATE deals SET {action} = ? WHERE id = ?", (new_val, deal_id))
            conn.commit()
            
            # Alle Status-Werte für die Buttons abrufen
            cursor.execute("SELECT angerufen, besichtigung, favorit, abgelehnt, todo FROM deals WHERE id = ?", (deal_id,))
            st = cursor.fetchone()
            conn.close()
            
            ang = st[0]
            bes = st[1]
            fav = st[2]
            abg = st[3]
            todo_val = st[4]
            
            # Tastatur mit aktualisierten Häkchen zusammenbauen
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
            
            if TELEGRAM_TOKEN:
                # Buttons in Telegram aktualisieren
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "reply_markup": keyboard
                    }
                )
                # Klick-Bestätigung an Telegram senden
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": query_id, "text": "Status aktualisiert & in App synchronisiert!"}
                )

    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
