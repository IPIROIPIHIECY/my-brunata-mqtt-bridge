import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, METER_MAPPING

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Sensoren basierend auf den gefundenen Zählern anlegen."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Wir erstellen eine Liste von Sensoren basierend auf den Keys im Koordinator (HZ01, KW01, etc.)
    entities = []
    for meter_id in coordinator.data.keys():
        entities.append(BrunataMeterSensor(coordinator, meter_id, entry))
    
    async_add_entities(entities)

class BrunataMeterSensor(CoordinatorEntity, SensorEntity):
    """Repräsentation eines Brunata Zählers."""

    def __init__(self, coordinator, meter_id, entry):
        super().__init__(coordinator)
        self._meter_id = meter_id
        self._entry_id = entry.entry_id
        
        # Bestimme den Typ (HZ, WW, KW) anhand der ersten zwei Buchstaben
        prefix = meter_id[:2]
        self._config = METER_MAPPING.get(prefix, {
            "name": "Unbekannter Zähler",
            "device_class": None,
            "unit": None
        })

    @property
    def unique_id(self):
        """Eindeutige ID für den Sensor."""
        return f"{self._entry_id}_{self._meter_id}"

    @property
    def name(self):
        """Name des Sensors (z.B. Brunata Heizung HZ01)."""
        return f"Brunata {self._config['name']} {self._meter_id}"

    @property
    def native_value(self):
        """Der aktuelle Messwert aus dem Koordinator."""
        data = self.coordinator.data.get(self._meter_id)
        return data.value if data else None

    @property
    def native_unit_of_measurement(self):
        """Die Einheit (m³ oder MWh)."""
        # Wir versuchen die Einheit vom API-Objekt zu nehmen, sonst Fallback auf const.py
        data = self.coordinator.data.get(self._meter_id)
        return data.unit if data and hasattr(data, 'unit') else self._config["unit"]

    @property
    def device_class(self):
        """Die Kategorie (Energy oder Water)."""
        return self._config["device_class"]

    @property
    def extra_state_attributes(self):
        """Zusätzliche Infos wie das Ablesedatum."""
        data = self.coordinator.data.get(self._meter_id)
        if data:
            return {
                "reading_date": str(data.date),
                "sap_cost_type": self._meter_id
            }
        return {}

    @property
    def device_info(self):
        """Ordnet alle Sensoren einem gemeinsamen 'Gerät' zu."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Brunata München Nutzeinheit",
            "manufacturer": "Brunata Metrona",
            "model": "Digitales Nutzerportal",
        }