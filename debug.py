import asyncio
import json
import logging
from brunata_api import BrunataClient
import paho.mqtt.client as mqtt

# --- KONFIGURATION ---
MQTT_BROKER = "192.168.1.XXX"  # Deine Broker IP
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "brunata/v1"

BRUNATA_USER = "..."
BRUNATA_PW = "..."

# Mapping der Keys auf lesbare Namen für MQTT
METERS = {
    "HZ01": "heating",
    "WW01": "hot_water",
    "KW01": "cold_water"
}

async def run_complete_bridge():
    async with BrunataClient(
        base_url="https://nutzerportal.brunata-muenchen.de",
        username=BRUNATA_USER,
        password=BRUNATA_PW,
        sap_client="201",
    ) as client:
        
        print("🔑 Login...")
        await client.login()

        # Wir nutzen 'get_monthly_consumption' für jeden Key einzeln,
        # da dies die sicherste Methode ist, um auch KW01 zu erzwingen.
        results = {}
        for sap_key, name in METERS.items():
            print(f"📡 Frage {name} ({sap_key}) ab...")
            try:
                # Wir holen die Liste der Monatswerte
                data = await client.get_monthly_consumption(cost_type=sap_key, in_kwh=False)
                if data:
                    # Wir nehmen den aktuellsten Wert (das letzte Element)
                    latest = data[-1]
                    results[name] = {
                        "value": getattr(latest, 'value', 0),
                        "unit": getattr(latest, 'unit', 'm³' if 'W' in sap_key else 'MWh'),
                        "date": str(getattr(latest, 'date', ''))
                    }
            except Exception as e:
                print(f"⚠️ Fehler bei {sap_key}: {e}")

        # --- MQTT VERSAND ---
        if results:
            mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            try:
                mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                for name, info in results.items():
                    topic = f"{MQTT_TOPIC_BASE}/{name}"
                    # Wir senden ein schönes JSON-Paket pro Zähler
                    mqtt_client.publish(f"{topic}/state", json.dumps(info), retain=True)
                    # Und den Einzelwert für einfache Sensoren
                    mqtt_client.publish(f"{topic}/value", info["value"], retain=True)
                    
                    print(f"✅ MQTT gesendet: {name} -> {info['value']} {info['unit']}")
                
                mqtt_client.disconnect()
            except Exception as e:
                print(f"❌ MQTT Broker Fehler: {e}")
        else:
            print("❌ Keine Daten zum Senden gefunden.")

if __name__ == "__main__":
    asyncio.run(run_complete_bridge())