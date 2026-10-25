import os
import sqlite3
import requests
from datetime import datetime
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

    try:
        cursor.execute("ALTER TABLE deals ADD COLUMN erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
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
                if (deal.besichtigung) badges += '<span class="badge badge-view">👀
