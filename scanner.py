import os
import sqlite3
import requests
from math import radians, sin, cos, sqrt, atan2
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
            kontakt TEXT DEFAULT '',
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

    try:
        cursor.execute("ALTER TABLE deals ADD COLUMN kontakt TEXT DEFAULT ''")
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

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def recalculate_radius_for_anker(anker_stadt_name):
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT stadt, ziel_qmp, markt_qmp, lat, lon FROM anker_staedte WHERE stadt = ?", (anker_stadt_name,))
    anker = cursor.fetchone()
    if not anker:
        conn.close()
        return
    conn.close()

def get_target_qmp_for_anker(anker_stadt_name):
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT ziel_qmp FROM anker_staedte WHERE stadt = ?", (anker_stadt_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 2500.0

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Immo Deal Hunter</title>
    <style>
        :root { --primary: #2563eb; --success: #16a34a; --warning: #d97706; --danger: #dc2626; --bg: #f8fafc; --card-bg: #ffffff; --text: #1e293b; --text-light: #64748b; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding: 15px; }
        .container { max-width: 800px; margin: auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 20px; margin: 0; color: #0f172a; display: flex; align-items: center; gap: 8px; }
        .nav-btns { display: flex; gap: 8px; }
        button { cursor: pointer; border: none; border-radius: 8px; font-weight: 600; padding: 10px 14px; font-size: 14px; transition: all 0.2s; }
        .btn-primary { background-color: var(--primary); color: white; }
        .btn-primary:hover { background-color: #1d4ed8; }
        .btn-success { background-color: var(--success); color: white; }
        .btn-success:hover { background-color: #15803d; }
        .btn-delete { background: #fee2e2; color: #b91c1c; padding: 6px 10px; font-size: 12px; border-radius: 6px; }
        .btn-delete:hover { background: #fca5a5; }
        
        .tabs { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 15px; scrollbar-width: none; }
        .tabs::-webkit-scrollbar { display: none; }
        .tab { background: #e2e8f0; color: var(--text-light); padding: 8px 14px; border-radius: 20px; font-size: 13px; white-space: nowrap; cursor: pointer; }
        .tab.active { background: var(--primary); color: white; }

        .deal-card { background: var(--card-bg); border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; position: relative; }
        .deal-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
        .deal-title { font-size: 16px; font-weight: 700; color: #0f172a; }
        .deal-location { font-size: 13px; color: var(--text-light); }
        .deal-price { font-size: 18px; font-weight: 800; color: var(--primary); margin: 8px 0; }
        .deal-details { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; font-size: 13px; color: var(--text-light); margin-bottom: 12px; }
        
        .badges { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }
        .badge { padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge-fav { background: #fef3c7; color: #b45309; }
        .badge-call { background: #e0f2fe; color: #0369a1; }
        .badge-view { background: #dcfce7; color: #15803d; }
        .badge-todo { background: #f3e8ff; color: #7e22ce; }
        .badge-no { background: #fee2e2; color: #b91c1c; }
        .badge-target { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
        .badge-above { background: #fee2e2; color: #991b1b; }

        .deal-contact { font-size: 12px; color: var(--text-light); background: #f1f5f9; padding: 6px 10px; border-radius: 6px; margin-bottom: 10px; }
        
        .deal-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 10px; margin-top: 8px; }
        .link-btn { color: var(--primary); text-decoration: none; font-size: 13px; font-weight: 600; }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 100; }
        .modal-content { background: white; width: 90%; max-width: 500px; border-radius: 12px; padding: 20px; max-height: 85vh; overflow-y: auto; }
        .anker-item { background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e2e8f0; }
        .anker-item input { width: 75px; padding: 4px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏠 Immo Deal Hunter</h1>
            <div class="nav-btns">
                <button class="btn-primary" onclick="openAnkerModal()">🏙️ Anker-Liste</button>
                <button class="btn-success" onclick="sendTestDeal()">🚀 Test</button>
            </div>
        </header>

        <div class="tabs">
            <div class="tab active" onclick="setTab('alle', this)">Alle Deals</div>
            <div class="tab" onclick="setTab('favorit', this)">⭐ Favoriten</div>
            <div class="tab" onclick="setTab('todo', this)">📋 To-Do</div>
            <div class="tab" onclick="setTab('angerufen', this)">📞 Angerufen</div>
            <div class="tab" onclick="setTab('besichtigung', this)">👀 Besichtigung</div>
            <div class="tab" onclick="setTab('abgelehnt', this)">❌ Abgelehnt</div>
        </div>

        <div id="deals-container">
            <p style="text-align:center; color:var(--text-light);">Lade Deals...</p>
        </div>
    </div>

    <div id="ankerModal" class="modal">
        <div class="modal-content">
            <h3>🏙️ Anker-Städte & qm²-Preise</h3>
            <p style="font-size:13px; color:var(--text-light);">Passe Markt- und Zielpreise direkt an.</p>
            <div id="anker-list-container">Lade Anker...</div>
            <button class="btn-primary" style="width:100%; margin-top:15px;" onclick="closeAnkerModal()">Schließen</button>
        </div>
    </div>

    <script>
        let currentTab = 'alle';
        let allDeals = [];

        function setTab(tab, element) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            element.classList.add('active');
            renderDeals();
        }

        async function loadDeals() {
            try {
                const response = await fetch('/api/deals');
                allDeals = await response.json();
                renderDeals();
            } catch (err) {
                console.error('Fehler beim Laden:', err);
            }
        }

        function renderDeals() {
            const container = document.getElementById('deals-container');
            
            let filtered = allDeals.filter(deal => {
                if (currentTab === 'alle') return true;
                if (currentTab === 'favorit') return deal.favorit;
                if (currentTab === 'todo') return deal.todo;
                if (currentTab === 'angerufen') return deal.angerufen;
                if (currentTab === 'besichtigung') return deal.besichtigung;
                if (currentTab === 'abgelehnt') return deal.abgelehnt;
                return true;
            });

            if (filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding: 40px; color:var(--text-light);">Keine Deals in diesem Ordner gefunden.</div>';
                return;
            }

            container.innerHTML = '';
            filtered.forEach(deal => {
                let badges = '';
                if (deal.diff_percent !== undefined) {
                    if (deal.diff_percent <= 0) {
                        badges += `<span class="badge badge-target">🎯 ${Math.abs(deal.diff_percent)}% unter Ziel</span>`;
                    } else {
                        badges += `<span class="badge badge-above">📈 +${deal.diff_percent}% über Ziel</span>`;
                    }
                }
                if (deal.favorit) badges += '<span class="badge badge-fav">⭐ Favorit</span>';
                if (deal.angerufen) badges += '<span class="badge badge-call">📞 Angerufen</span>';
                if (deal.besichtigung) badges += '<span class="badge badge-view">👀 Besichtigung</span>';
                if (deal.todo) badges += '<span class="badge badge-todo">📋 To-Do</span>';
                if (deal.abgelehnt) badges += '<span class="badge badge-no">❌ Abgelehnt</span>';

                const card = document.createElement('div');
                card.className = 'deal-card';
                card.innerHTML = `
                    <div class="deal-header">
                        <div>
                            <div class="deal-title">${deal.titel || 'Immobilie'}</div>
                            <div class="deal-location">📍 ${deal.ort || '-'} (Anker: ${deal.anker_stadt || '-'})</div>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:12px; font-weight:600; color:var(--text-light);">#${deal.id}</span>
                            <button class="btn-delete" onclick="deleteDeal(${deal.id})">🗑️</button>
                        </div>
                    </div>
                    <div class="deal-price">${deal.preis ? deal.preis.toLocaleString() + ' €' : '-'}</div>
                    <div class="deal-details">
                        <div>📐 Fläche: <strong>${deal.flaeche ? deal.flaeche + ' m²' : '-'}</strong></div>
                        <div>💰 qm²-Preis: <strong>${deal.qmp ? Math.round(deal.qmp).toLocaleString() + ' €/m²' : '-'}</strong></div>
                    </div>
                    ${deal.kontakt ? `<div class="deal-contact">👤 Kontakt: <strong>${deal.kontakt}</strong></div>` : ''}
                    <div class="badges">${badges}</div>
                    <div class="deal-footer">
                        <span style="font-size:11px; color:var(--text-light);">${deal.erstellt_am || ''}</span>
                        ${deal.link ? `<a class="link-btn" href="${deal.link}" target="_blank">Zum Angebot 🔗</a>` : ''}
                    </div>
                `;
                container.appendChild(card);
            });
        }

        async function deleteDeal(dealId) {
            if (confirm("Möchtest du diesen Deal wirklich löschen?")) {
                const res = await fetch('/api/deal/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: dealId })
                });
                if (res.ok) loadDeals();
            }
        }

        async function sendTestDeal() {
            const randomNum = Math.floor(Math.random() * 10000);
            await fetch('/api/deal/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    titel: "Wohnung #" + randomNum,
                    ort: "Frankfurt Griesheim",
                    anker_stadt: "Frankfurt",
                    preis: 175000.0,
                    flaeche: 65.0,
                    kontakt: "Herr Mustermann (0170-1234567)",
                    link: "https://immobilienscout24.de/expose/test-" + randomNum
                })
            });
            loadDeals();
        }

        async function openAnkerModal() {
            document.getElementById('ankerModal').style.display = 'flex';
            await refreshAnkerUI();
        }

        async function refreshAnkerUI() {
            const res = await fetch('/api/anker');
            const ankers = await res.json();
            const listContainer = document.getElementById('anker-list-container');
            
            listContainer.innerHTML = '';
            ankers.forEach(a => {
                const div = document.createElement('div');
                div.className = 'anker-item';
                div.innerHTML = `
                    <strong>${a.stadt}</strong><br>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; font-size:13px;">
                        <span>Markt: <input type="number" id="markt_${a.id}" value="${a.markt_qmp}"> €</span>
                        <span>Ziel: <input type="number" id="ziel_${a.id}" value="${a.ziel_qmp}"> €</span>
                        <button class="btn-primary" style="padding:6px 10px; font-size:12px;" onclick="updateAnker(${a.id}, '${a.stadt}')">Speichern</button>
                    </div>
                `;
                listContainer.appendChild(div);
            });
        }

        function closeAnkerModal() {
            document.getElementById('ankerModal').style.display = 'none';
        }

        async function updateAnker(id, stadt) {
            const newMarkt = document.getElementById(`markt_${id}`).value;
            const newZiel = document.getElementById(`ziel_${id}`).value;
            const res = await fetch('/api/anker/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, stadt: stadt, markt_qmp: newMarkt, ziel_qmp: newZiel })
            });
            if(res.ok) alert("Anker-Preise erfolgreich aktualisiert!");
        }

        loadDeals();
        setInterval(loadDeals, 5000);
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
    return jsonify([{"id": r[0], "stadt": r[1], "ziel_qmp": r[2], "markt_qmp": r[3]} for r in rows])

@app.route('/api/anker/update', methods=['POST'])
def update_anker():
    data = request.get_json()
    anker_id = data.get('id')
    stadt = data.get('stadt')
    newMarkt = data.get('markt_qmp')
    newZiel = data.get('ziel_qmp')
    
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE anker_staedte SET markt_qmp = ?, ziel_qmp = ? WHERE id = ?", (newMarkt, newZiel, anker_id))
    conn.commit()
    conn.close()
    
    recalculate_radius_for_anker(stadt)
    return jsonify({"status": "success"})

@app.route('/api/deals', methods=['GET'])
def get_deals():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titel, ort, anker_stadt, preis, flaeche, qmp, link, 
               angerufen, besichtigung, favorit, abgelehnt, todo, erstellt_am, kontakt 
        FROM deals ORDER BY id DESC LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    
    deals_list = []
    for r in rows:
        anker_stadt = r[3]
        qmp = r[6]
        ziel_qmp = get_target_qmp_for_anker(anker_stadt)
        
        diff_percent = 0
        if ziel_qmp > 0 and qmp > 0:
            diff_percent = round(((qmp - ziel_qmp) / ziel_qmp) * 100, 1)

        deals_list.append({
            "id": r[0], "titel": r[1], "ort": r[2], "anker_stadt": r[3],
            "preis": r[4], "flaeche": r[5], "qmp": r[6], "link": r[7],
            "angerufen": r[8], "besichtigung": r[9], "favorit": r[10],
            "abgelehnt": r[11], "todo": r[12], "erstellt_am": r[13], "kontakt": r[14],
            "ziel_qmp": ziel_qmp, "diff_percent": diff_percent
        })
        
    return jsonify(deals_list)

@app.route('/api/deal/delete', methods=['POST'])
def delete_deal():
    data = request.get_json()
    deal_id = data.get('id')
    if not deal_id: return jsonify({"error": "Keine ID"}), 400
        
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted", "id": deal_id})

@app.route('/api/deal/add', methods=['POST'])
def add_deal():
    data = request.get_json()
    if not data: return jsonify({"error": "Keine Daten"}), 400
        
    titel, ort, anker_stadt, preis, flaeche, link, kontakt = (
        data.get('titel'), data.get('ort'), data.get('anker_stadt'),
        data.get('preis'), data.get('flaeche'), data.get('link'), data.get('kontakt', '')
    )
    qmp = preis / flaeche if flaeche > 0 else 0
    ziel_qmp = get_target_qmp_for_anker(anker_stadt)
    
    diff_percent = round(((qmp - ziel_qmp) / ziel_qmp) * 100, 1) if ziel_qmp > 0 else 0
    diff_str = f"🎯 {abs(diff_percent)}% unter Zielpreis!" if diff_percent <= 0 else f"📈 +{diff_percent}% über Zielpreis"

    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO deals (titel, ort, anker_stadt, preis, flaeche, qmp, link, kontakt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (titel, ort, anker_stadt, preis, flaeche, qmp, link, kontakt))
        conn.commit()
        deal_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Bereits vorhanden"}), 400
    conn.close()
    
    if TELEGRAM_CHAT_ID:
        text = (
            f"🔥 **NEUER DEAL GEFUNDEN** 🔥\n"
            f"🏙️ Anker: {anker_stadt}\n"
            f"📍 Ort: {ort}\n"
            f"💰 Preis: {preis:,.2f}€ (QMP: {qmp:,.2f}€)\n"
            f"🎯 Ziel-QMP: {ziel_qmp:,.2f}€ ({diff_str})\n"
            f"📐 Fläche: {flaeche} m²\n"
            f"{f'👤 Kontakt: {kontakt}' if kontakt else ''}\n"
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
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "reply_markup": keyboard
        })

    return jsonify({"status": "success", "deal_id": deal_id}), 201

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or 'callback_query' not in data: return jsonify({"status": "ignored"})
    
    callback_query = data['callback_query']
    callback_data = callback_query['data']
    message = callback_query['message']
    chat_id, message_id, query_id = message['chat']['id'], message['message_id'], callback_query['id']
    
    parts = callback_data.split('_')
    if len(parts) == 2:
        action, deal_id_str = parts
        if action in ['angerufen', 'besichtigung', 'favorit', 'abgelehnt', 'todo']:
            try:
                deal_id = int(deal_id_str)
            except ValueError:
                return jsonify({"status": "invalid id"})
            
            conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(f"SELECT {action} FROM deals WHERE id = ?", (deal_id,))
            row = cursor.fetchone()
            
            if row is not None:
                new_val = 0 if row[0] == 1 else 1
                cursor.execute(f"UPDATE deals SET {action} = ? WHERE id = ?", (new_val, deal_id))
                conn.commit()
                
                cursor.execute("SELECT angerufen, besichtigung, favorit, abgelehnt, todo FROM deals WHERE id = ?", (deal_id,))
                st = cursor.fetchone()
                conn.close()
                
                ang, bes, fav, abg, todo_val = st[0], st[1], st[2], st[3], st[4]
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
                
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup", json={
                    "chat_id": chat_id, "message_id": message_id, "reply_markup": keyboard
                })
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={
                    "callback_query_id": query_id, "text": "Häkchen aktualisiert & Ordner verschoben!"
                })

    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
