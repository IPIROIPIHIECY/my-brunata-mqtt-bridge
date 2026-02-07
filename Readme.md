# Brunata München Integration für Home Assistant

Diese Integration ermöglicht es, Verbrauchsdaten (Heizung, Warmwasser, Kaltwasser) aus dem **Brunata München Nutzerportal** direkt in Home Assistant einzubinden.

Die Integration erkennt automatisch alle in deinem Account hinterlegten Zähler und stellt sie als Sensoren zur Verfügung. Dank der korrekten Zuweisung von `device_class` können die Werte direkt im **Home Assistant Energie-Dashboard** verwendet werden.

## 🚀 Features
- **Automatisches Discovery:** Erkennt alle Zähler (HZ01, WW01, KW01, etc.) ohne manuelle Konfiguration.
- **Energie-Dashboard Ready:** Unterstützung für Energie- (MWh/kWh) und Wasser-Entitäten (m³).
- **Sicheres Polling:** Nutzt einen effizienten Koordinator, um die Brunata-Server nicht zu überlasten (Standard-Intervall: 12 Stunden).
- **Einfache Einrichtung:** Konfiguration direkt über die Home Assistant Benutzeroberfläche (Config Flow).

## 🛠 Basis
Diese Integration basiert auf dem Python-Client **[brunata-api](https://github.com/fjfricke/brunata-api)** von fjfricke. Ohne diese Vorarbeit bei der Entschlüsselung der SAP OData-Schnittstelle wäre diese Integration nicht möglich gewesen.

## 📦 Installation

### Über HACS (Empfohlen)
1. Öffne **HACS** in deinem Home Assistant.
2. Klicke auf die drei Punkte oben rechts und wähle **Benutzerdefinierte Repositories**.
3. Füge die URL dieses Repositories hinzu und wähle als Kategorie `Integration`.
4. Suche nach `Brunata München` und klicke auf **Herunterladen**.
5. Starte Home Assistant neu.

### Manuell
1. Lade dieses Repository als ZIP-Datei herunter.
2. Kopiere den Ordner `custom_components/brunata_muenchen` in dein `config/custom_components/` Verzeichnis.
3. Starte Home Assistant neu.

## ⚙️ Konfiguration
1. Gehe zu **Einstellungen** -> **Geräte & Dienste**.
2. Klicke auf **Integration hinzufügen** unten rechts.
3. Suche nach **Brunata München**.
4. Gib deine Zugangsdaten ein:
   - **Portal URL**: `https://nutzerportal.brunata-muenchen.de`
   - **E-Mail / Benutzername**: Deine E-Mail vom Brunata Portal.
   - **Passwort**: Dein Portal-Passwort.
   - **SAP Mandant**: In der Regel `201`.

## 📊 Sensoren
Nach erfolgreicher Einrichtung werden folgende Sensoren (je nach Verfügbarkeit in deinem Account) angelegt:
- `sensor.brunata_heizung_hz01` (Einheit: MWh)
- `sensor.brunata_warmwasser_ww01` (Einheit: m³)
- `sensor.brunata_kaltwasser_kw01` (Einheit: m³)

Das jeweilige Ablesedatum des SAP-Backends wird als Attribut `reading_date` am Sensor gespeichert.

## ⚠️ Disclaimer
Dies ist eine inoffizielle Integration. Sie steht in keiner Verbindung zur BRUNATA-METRONA GmbH oder BRUdirekt. Die Nutzung erfolgt auf eigene Gefahr. Alle Markennamen gehören ihren jeweiligen Eigentümern.