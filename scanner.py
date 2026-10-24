import time
import threading
from math import radians, sin, cos, sqrt, atan2
from flask import Flask
import requests

# 1. Mini-Webserver für Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Immo Deal Hunter Bot läuft aktiv!"

# 2. Deine Zugangsdaten
BOT_TOKEN = "8322651200:AAHNfd8ag3qx-T0eUFz2gpL1NK-bHQRS14"
CHAT_ID = "-1004495350584"

# 3. Definition deiner 5 Zentren
ZONES = {
    "Hanau": {
        "lat": 50.1375, "lon": 8.9167,
        "target_price": 1700,
        "market_avg": 3372,
        "discount_percent": (1700 - 3372) / 3372
    },
    "Dietzenbach": {
        "lat": 50.0108, "lon": 8.7753,
        "target_price": 1850,
        "market_avg": 3251,
        "discount_percent": (1850 - 3251) / 3251
    },
    "Rüsselsheim": {
        "lat": 49.9944, "lon": 8.4131,
        "target_price": 1800,
        "market_avg": 3150,
        "discount_percent": (1800 - 3150) / 3150
    },
    "Darmstadt": {
        "lat": 49.8728, "lon": 8.6512,
        "target_price": 2200,
        "market_avg": 4120,
        "discount_percent": (2200 - 4120) / 4120
    },
    "Mainz": {
        "lat": 50.0000, "lon": 8.2711,
        "target_price": 2300,
        "market_avg": 4280,
        "discount_percent": (2300 - 4280) / 4280
    }
}

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def find_dynamic_zone(lat, lon):
    best_zone = None
    min_distance = float('inf')
    for zone_name, data in ZONES.items():
        dist = haversine_km(lat, lon, data["lat"], data["lon"])
        if dist < min_distance:
            min_distance = dist
            best_zone = zone_name
    return best_zone, min_distance

def evaluate_property(prop_title, prop_price, prop_size, prop_lat, prop_lon, local_village_market_avg, url):
    if prop_size <= 0:
        return None
    actual_qm_price = prop_price / prop_size
    matched_zone, distance = find_dynamic_zone(prop_lat, prop_lon)
    zone_data = ZONES[matched_zone]
    allowed_max_qm_price = local_village_market_avg * (1 + zone_data["discount_percent"])
    
    if actual_qm_price <= allowed_max_qm_price:
        return {
            "title": prop_title,
            "price": prop_price,
            "size": prop_size,
            "qm_price": round(actual_qm_price, 2),
            "zone": matched_zone,
            "distance": round(distance, 1),
            "max_allowed": round(allowed_max_qm_price, 2),
            "url": url
        }
    return None

def send_telegram_alert(deal):
    message = (
        f"🚨 **SCHNÄPPCHEN-DEAL GEFUNDEN!** 🚨\n\n"
        f"📌 **Objekt:** {deal['title']}\n"
        f"📍 **Zugeordnete Zone:** {deal['zone']} ({deal['distance']} km Entfernung)\n"
        f"💰 **Kaufpreis:** {deal['price']:,} €\n"
        f"📐 **Wohnfläche:** {deal['size']} m²\n"
        f"📊 **Dein Qm-Preis:** {deal['qm_price']} €/m²\n"
        f"🎯 **Erlaubtes Limit:** {deal['max_allowed']} €/m²\n\n"
        f"🔗 [Zum Original-Inserat]({deal['url']})"
    )
    
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(api_url, json=payload, timeout=10)
    except Exception as e:
        print("Fehler beim Senden:", e)

def run_scanner_loop():
    print("Immo Deal Hunter gestartet: Überprüfe dynamische Zonen & Radien...")
    # Testsimulation beim Start
    test_deal = evaluate_property(
        prop_title="Einfamilienhaus im Taunus mit Garten",
        prop_price=340000,
        prop_size=150,
        prop_lat=50.2500, prop_lon=8.5500,
        local_village_market_avg=4000.0,
        url="https://www.immobilienscout24.de"
    )
    if test_deal:
        send_telegram_alert(test_deal)

# Startet den Scanner im Hintergrund
threading.Thread(target=run_scanner_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
