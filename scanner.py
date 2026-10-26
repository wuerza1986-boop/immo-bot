import os
import sqlite3
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "ein_sehr_geheimer_session_schluessel_hier"

TELEGRAM_TOKEN = "8322651200:AAGmeU2XEF2frad2d9eVf2nMgEr2K8Ws7BQ"
TELEGRAM_CHAT_ID = "-1004495350584"

# Passwörter & Zugang
FRIEND_PASSWORD = "geheimepasswort123"
ADMIN_BYPASS_TOKEN = "mein_geheimer_admin_link"

def init_db():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS anker_staedte (id INTEGER PRIMARY KEY AUTOINCREMENT, stadt TEXT UNIQUE NOT NULL, ziel_qmp REAL NOT NULL, markt_qmp REAL NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS deals (id INTEGER PRIMARY KEY AUTOINCREMENT, titel TEXT, ort TEXT, anker_stadt TEXT, preis REAL, flaeche REAL, qmp REAL, link TEXT UNIQUE, kontakt TEXT DEFAULT '', angerufen INTEGER DEFAULT 0, besichtigung INTEGER DEFAULT 0, favorit INTEGER DEFAULT 0, abgelehnt INTEGER DEFAULT 0, todo INTEGER DEFAULT 0, erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
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
        cursor.execute('INSERT OR IGNORE INTO anker_staedte (stadt, ziel_qmp, markt_qmp, lat, lon) VALUES (?, ?, ?, ?, ?)', (stadt, ziel, markt, lat, lon))
    conn.commit()
    conn.close()

init_db()

def get_target_qmp(anker_stadt):
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT ziel_qmp FROM anker_staedte WHERE stadt = ?", (anker_stadt,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 2500.0

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Immo Deal Hunter</title>
    <!-- Zielscheiben-Icon für Web & Smartphone-Startbildschirm -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8fafc; color: #1e293b; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); width: 100%; max-width: 350px; text-align: center; border: 1px solid #e2e8f0; }
        h2 { margin-bottom: 20px; font-size: 20px; color: #0f172a; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background-color: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; }
        .error { color: #dc2626; font-size: 13px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🎯 Immo Deal Hunter</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Passwort eingeben..." required autofocus>
            <button type="submit">Einloggen</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Immo Deal Hunter</title>
    <!-- Zielscheiben-Icon für Web & Smartphone-Startbildschirm -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">
    <style>
        :root { --primary: #2563eb; --success: #16a34a; --danger: #dc2626; --bg: #f8fafc; --card-bg: #ffffff; --text: #1e293b; --text-light: #64748b; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding: 15px; }
        .container { max-width: 800px; margin: auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 20px; margin: 0; color: #0f172a; }
        button { cursor: pointer; border: none; border-radius: 8px; font-weight: 600; padding: 10px 14px; font-size: 14px; }
        .btn-primary { background-color: var(--primary); color: white; }
        .btn-success { background-color: var(--success); color: white; }
        .btn-delete { background: #fee2e2; color: #b91c1c; padding: 6px 10px; font-size: 12px; border-radius: 6px; }
        .tabs { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 15px; scrollbar-width: none; }
        .tabs::-webkit-scrollbar { display: none; }
        .tab { background: #e2e8f0; color: var(--text-light); padding: 8px 14px; border-radius: 20px; font-size: 13px; white-space: nowrap; cursor: pointer; }
        .tab.active { background: var(--primary); color: white; }
        .deal-card { background: var(--card-bg); border-radius: 12px; padding: 16px; margin-bottom: 12px; border: 1px solid #e2e8f0; }
        .deal-title { font-size: 16px; font-weight: 700; color: #0f172a; }
        .deal-price { font-size: 18px; font-weight: 800; color: var(--primary); margin: 8px 0; }
        .deal-details { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; font-size: 13px; color: var(--text-light); margin-bottom: 12px; }
        .badges { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }
        .badge { padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge-fav { background: #fef3c7; color: #b45309; }
        .badge-call { background: #e0f2fe; color: #0369a1; }
        .badge-view { background: #dcfce7; color: #15803d; }
        .badge-todo { background: #f3e8ff; color: #7e22ce; }
        .badge-no { background: #fee2e2; color: #b91c1c; }
        .badge-target { background: #dcfce7; color: #15803d; }
        .badge-above { background: #fee2e2; color: #991b1b; }
        .deal-contact { font-size: 12px; color: var(--text-light); background: #f1f5f9; padding: 6px 10px; border-radius: 6px; margin-bottom: 10px; }
        .deal-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 10px; margin-top: 8px; font-size: 12px; color: var(--text-light); }
        .link-btn { color: var(--primary); text-decoration: none; font-weight: 600; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 100; }
        .modal-content { background: white; width: 90%; max-width: 500px; border-radius: 12px; padding: 20px; max-height: 85vh; overflow-y: auto; }
        .anker-item { background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e2e8f0; }
        .anker-item input { width: 75px; padding: 4px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Immo Deal Hunter</h1>
            <div style="display:flex; gap:8px;">
                <button class="btn-primary" onclick="openAnkerModal()">🏙️ Anker</button>
                <button class="btn-success" onclick="sendTestDeal()">🚀 Test</button>
            </div>
        </header>
        <div class="tabs">
            <div class="tab active" onclick="setTab('alle', this)">Alle</div>
            <div class="tab" onclick="setTab('favorit', this)">⭐ Favoriten</div>
            <div class="tab" onclick="setTab('todo', this)">📋 To-Do</div>
            <div class="tab" onclick="setTab('angerufen', this)">📞 Angerufen</div>
            <div class="tab" onclick="setTab('besichtigung', this)">👀 Besichtigung</div>
            <div class="tab" onclick="setTab('abgelehnt', this)">❌ Abgelehnt</div>
        </div>
        <div id="deals-container"><p style="text-align:center; color:var(--text-light);">Lade Deals...</p></div>
    </div>
    <div id="ankerModal" class="modal">
        <div class="modal-content">
            <h3>🏙️ Anker-Städte</h3>
            <div id="anker-list-container">Lade...</div>
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
                const res = await fetch('/api/deals');
                allDeals = await res.json();
                renderDeals();
            } catch (err) { console.error(err); }
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
                container.innerHTML = '<div style="text-align:center; padding: 40px; color:var(--text-light);">Keine Deals gefunden.</div>';
                return;
            }
            container.innerHTML = '';
            filtered.forEach(deal => {
                let badges = '';
                if (deal.diff_percent !== undefined) {
                    if (deal.diff_percent <= 0) badges += `<span class="badge badge-target">🎯 ${Math.abs(deal.diff_percent)}% unter Ziel</span>`;
                    else badges += `<span class="badge badge-above">📈 +${deal.diff_percent}% über Ziel</span>`;
                }
                if (deal.favorit) badges += '<span class="badge badge-fav">⭐ Favorit</span>';
                if (deal.angerufen) badges += '<span class="badge badge-call">📞 Angerufen</span>';
                if (deal.besichtigung) badges += '<span class="badge badge-view">👀 Besichtigung</span>';
                if (deal.todo) badges += '<span class="badge badge-todo">📋 To-Do</span>';
                if (deal.abgelehnt) badges += '<span class="badge badge-no">❌ Abgelehnt</span>';
                const card = document.createElement('div');
                card.className = 'deal-card';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <div>
                            <div class="deal-title">${deal.titel || 'Immobilie'}</div>
                            <div style="font-size:13px; color:var(--text-light);">📍 ${deal.ort || '-'} (Anker: ${deal.anker_stadt || '-'})</div>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:12px; font-weight:600; color:var(--text-light);">#${deal.id}</span>
                            <button class="btn-delete" onclick="deleteDeal(${deal.id})">🗑️</button>
                        </div>
                    </div>
                    <div class="deal-price">${deal.preis ? deal.preis.toLocaleString() + ' €' : '-'}</div>
                    <div class="deal-details">
                        <div>📐 Fläche: <strong>${deal.flaeche ? deal.flaeche + ' m²' : '-'}</strong></div>
                        <div>💰 qm²: <strong>${deal.qmp ? Math.round(deal.qmp).toLocaleString() + ' €' : '-'}</strong></div>
                    </div>
                    ${deal.kontakt ? `<div class="deal-contact">👤 Kontakt: <strong>${deal.kontakt}</strong></div>` : ''}
                    <div class="badges">${badges}</div>
                    <div class="deal-footer">
                        <span>📅 <strong>${deal.erstellt_am || '-'}</strong></span>
                        ${deal.link ? `<a class="link-btn" href="${deal.link}" target="_blank">Angebot 🔗</a>` : ''}
                    </div>
                `;
                container.appendChild(card);
            });
        }
        async function deleteDeal(id) {
            if (confirm("Löschen?")) {
                await fetch('/api/deal/delete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) });
                loadDeals();
            }
        }
        async function sendTestDeal() {
            await fetch('/api/deal/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    titel: "Wohnung #" + Math.floor(Math.random()*1000),
                    ort: "Frankfurt Griesheim",
                    anker_stadt: "Frankfurt",
                    preis: 175000.0,
                    flaeche: 65.0,
                    kontakt: "Herr Mustermann (0170-1234567)",
                    link: "https://immobilienscout24.de"
                })
            });
            loadDeals();
        }
        async function openAnkerModal() {
            document.getElementById('ankerModal').style.display = 'flex';
            const res = await fetch('/api/anker');
            const ankers = await res.json();
            const container = document.getElementById('anker-list-container');
            container.innerHTML = '';
            ankers.forEach(a => {
                container.innerHTML += `
                    <div class="anker-item">
                        <strong>${a.stadt}</strong>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; font-size:13px;">
                            <span>Markt: <input type="number" id="markt_${a.id}" value="${a.markt_qmp}"> €</span>
                            <span>Ziel: <input type="number" id="ziel_${a.id}" value="${a.ziel_qmp}"> €</span>
                            <button class="btn-primary" style="padding:4px 8px; font-size:12px;" onclick="updateAnker(${a.id}, '${a.stadt}')">Speichern</button>
                        </div>
                    </div>`;
            });
        }
        function closeAnkerModal() { document.getElementById('ankerModal').style.display = 'none'; }
        async function updateAnker(id, stadt) {
            const markt_qmp = document.getElementById(`markt_${id}`).value;
            const ziel_qmp = document.getElementById(`ziel_${id}`).value;
            await fetch('/api/anker/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, stadt, markt_qmp, ziel_qmp})
            });
            alert("Aktualisiert!");
        }
        loadDeals();
        setInterval(loadDeals, 5000);
    </script>
</body>
</html>"""

@app.before_request
def check_auth():
    if request.path in ['/webhook']:
        return
    
    token = request.args.get('admin')
    if token == ADMIN_BYPASS_TOKEN:
        session['logged_in'] = True
        
    if not session.get('logged_in'):
        if request.method == 'POST':
            pw = request.form.get('password')
            if pw == FRIEND_PASSWORD:
                session['logged_in'] = True
                return redirect(url_for('home'))
            else:
                return render_template_string(LOGIN_HTML, error="Falsches Passwort!")
        return render_template_string(LOGIN_HTML)

@app.route("/")
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
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE anker_staedte SET markt_qmp = ?, ziel_qmp = ? WHERE id = ?", (data.get('markt_qmp'), data.get('ziel_qmp'), data.get('id')))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/deals', methods=['GET'])
def get_deals():
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id, titel, ort, anker_stadt, preis, flaeche, qmp, link, angerufen, besichtigung, favorit, abgelehnt, todo, erstellt_am, kontakt FROM deals ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    
    out = []
    for r in rows:
        ziel = get_target_qmp(r[3])
        diff = round(((r[6] - ziel) / ziel) * 100, 1) if ziel > 0 and r[6] > 0 else 0
        out.append({
            "id": r[0], "titel": r[1], "ort": r[2], "anker_stadt": r[3],
            "preis": r[4], "flaeche": r[5], "qmp": r[6], "link": r[7],
            "angerufen": r[8], "besichtigung": r[9], "favorit": r[10],
            "abgelehnt": r[11], "todo": r[12], "erstellt_am": r[13], "kontakt": r[14],
            "diff_percent": diff
        })
    return jsonify(out)

@app.route('/api/deal/delete', methods=['POST'])
def delete_deal():
    data = request.get_json()
    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deals WHERE id = ?", (data.get('id'),))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/deal/add', methods=['POST'])
def add_deal():
    data = request.get_json()
    preis, flaeche = data.get('preis', 0), data.get('flaeche', 0)
    qmp = preis / flaeche if flaeche > 0 else 0
    ziel = get_target_qmp(data.get('anker_stadt'))
    diff = round(((qmp - ziel) / ziel) * 100, 1) if ziel > 0 else 0
    diff_str = f"🎯 {abs(diff)}% unter Ziel" if diff <= 0 else f"📈 +{diff}% über Ziel"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO deals (titel, ort, anker_stadt, preis, flaeche, qmp, link, kontakt, erstellt_am) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (data.get('titel'), data.get('ort'), data.get('anker_stadt'), preis, flaeche, qmp, data.get('link'), data.get('kontakt'), time_str))
    conn.commit()
    deal_id = cursor.lastrowid
    conn.close()

    if TELEGRAM_CHAT_ID:
        kontakt_info = f"👤 Kontakt: {data.get('kontakt')}\n" if data.get('kontakt') else ""
        text = (f"🔥 **NEUER DEAL GEFUNDEN** 🔥\n"
                f"🏙️ Anker: {data.get('anker_stadt')}\n"
                f"📍 Ort: {data.get('ort')}\n"
                f"💰 Preis: {preis:,.2f}€ (QMP: {qmp:,.2f}€)\n"
                f"🎯 Ziel-QMP: {ziel:,.2f}€ ({diff_str})\n"
                f"📐 Fläche: {flaeche} m²\n"
                f"{kontakt_info}"
                f"📅 Erstellt am: {time_str}\n"
                f"🔗 [Zum Angebot]({data.get('link')})")
        keyboard = {
            "inline_keyboard": [
                [{"text": "📞 Angerufen", "callback_data": f"angerufen_{deal_id}"}, {"text": "👀 Besichtigung", "callback_data": f"besichtigung_{deal_id}"}],
                [{"text": "⭐ Favorit", "callback_data": f"favorit_{deal_id}"}, {"text": "📋 To-Do", "callback_data": f"todo_{deal_id}"}],
                [{"text": "❌ Abgelehnt", "callback_data": f"abgelehnt_{deal_id}"}]
            ]
        }
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "reply_markup": keyboard})

    return jsonify({"status": "success", "deal_id": deal_id}), 201

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or 'callback_query' not in data: return jsonify({"status": "ignored"})
    cb = data['callback_query']
    parts = cb['data'].split('_')
    if len(parts) == 2:
        action, did = parts[0], int(parts[1])
        conn = sqlite3.connect('deal_hunter.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {action} FROM deals WHERE id = ?", (did,))
        row = cursor.fetchone()
        if row:
            new_val = 0 if row[0] == 1 else 1
            cursor.execute(f"UPDATE deals SET {action} = ? WHERE id = ?", (new_val, did))
            conn.commit()
            cursor.execute("SELECT angerufen, besichtigung, favorit, abgelehnt, todo FROM deals WHERE id = ?", (did,))
            st = cursor.fetchone()
            conn.close()
            
            kb = {
                "inline_keyboard": [
                    [{"text": f"📞 Angerufen {'✅' if st[0] else ''}", "callback_data": f"angerufen_{did}"}, {"text": f"👀 Besichtigung {'✅' if st[1] else ''}", "callback_data": f"besichtigung_{did}"}],
                    [{"text": f"⭐ Favorit {'✅' if st[2] else ''}", "callback_data": f"favorit_{did}"}, {"text": f"📋 To-Do {'✅' if st[4] else ''}", "callback_data": f"todo_{did}"}],
                    [{"text": f"❌ Abgelehnt {'✅' if st[3] else ''}", "callback_data": f"abgelehnt_{did}"}]
                ]
            }
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup", json={"chat_id": cb['message']['chat']['id'], "message_id": cb['message']['message_id'], "reply_markup": kb})
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb['id'], "text": "Aktualisiert!"})
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
