"""Sensoren für die Brunata München Integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    METER_MAPPING,
    SENSOR_TYPE_CUMULATIVE,
    SENSOR_TYPE_METER,
    SENSOR_TYPE_MONTHLY,
)

_LOGGER = __import__("logging").getLogger(__name__)


@dataclass(frozen=True)
class SensorDefinition:
    """Definition eines Brunata Sensors."""

    key: str
    name: str
    sensor_type: str
    cost_type: str
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None


def _get_label_for_cost_type(cost_type: str) -> str:
    """Bestimme das Label basierend auf dem Kostenart-Präfix."""
    prefix = cost_type[:2] if len(cost_type) >= 2 else cost_type
    config = METER_MAPPING.get(prefix, {})
    return config.get("name", cost_type)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensoren basierend auf den gefundenen Zählern anlegen."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}

    meter_readings = dict(data.get("meter_readings_by_cost_type") or {})
    monthly_by_cost_type = dict(data.get("monthly_by_cost_type") or {})
    kwh_histories = dict(data.get("kwh_histories_by_cost_type") or {})
    cold_water_data = dict(data.get("cold_water_data") or {})

    # Alle verfügbaren Kostenarten sammeln
    cost_types = sorted(
        {
            *meter_readings.keys(),
            *monthly_by_cost_type.keys(),
            *cold_water_data.keys(),
        }
    )

    entities: list[BrunataSensor] = []

    for cost_type in cost_types:
        label = _get_label_for_cost_type(cost_type)
        prefix = cost_type[:2] if len(cost_type) >= 2 else cost_type
        config = METER_MAPPING.get(prefix, {})

        # Sensor 1: Zählerstand (meter reading)
        if meter_readings.get(cost_type) or cold_water_data.get(cost_type):
            entities.append(
                BrunataSensor(
                    coordinator=coordinator,
                    entry=entry,
                    definition=SensorDefinition(
                        key=f"meter_{cost_type.lower()}",
                        name=f"{label} {cost_type} Zählerstand",
                        sensor_type=SENSOR_TYPE_METER,
                        cost_type=cost_type,
                        device_class=config.get("device_class"),
                        state_class=SensorStateClass.TOTAL_INCREASING,
                    ),
                )
            )

        # Sensor 2: Monatsverbrauch (kWh) - nur für HZ und WW
        if monthly_by_cost_type.get(cost_type):
            entities.append(
                BrunataSensor(
                    coordinator=coordinator,
                    entry=entry,
                    definition=SensorDefinition(
                        key=f"monthly_{cost_type.lower()}",
                        name=f"{label} {cost_type} Monatsverbrauch",
                        sensor_type=SENSOR_TYPE_MONTHLY,
                        cost_type=cost_type,
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.TOTAL,
                    ),
                )
            )

        # Sensor 3: Kumulativer Verbrauch (kWh)
        if kwh_histories.get(cost_type):
            entities.append(
                BrunataSensor(
                    coordinator=coordinator,
                    entry=entry,
                    definition=SensorDefinition(
                        key=f"cumulative_{cost_type.lower()}",
                        name=f"{label} {cost_type} Verbrauch Kumulativ",
                        sensor_type=SENSOR_TYPE_CUMULATIVE,
                        cost_type=cost_type,
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.TOTAL_INCREASING,
                    ),
                )
            )

    async_add_entities(entities)
    _LOGGER.info("Brunata München: %d Sensoren erstellt", len(entities))


class BrunataSensor(CoordinatorEntity, SensorEntity):
    """Repräsentation eines Brunata Sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        definition: SensorDefinition,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._def = definition

        # Eindeutige ID
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_{definition.key}"

        # Sensor-Attribute
        self._attr_name = definition.name
        self._attr_device_class = definition.device_class
        self._attr_state_class = definition.state_class

    @property
    def device_info(self) -> DeviceInfo:
        """Ordnet alle Sensoren einem gemeinsamen 'Gerät' zu."""
        uid = self._entry.unique_id or self._entry.entry_id
        return DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name="Brunata München Nutzeinheit",
            manufacturer="Brunata Metrona",
            model="Digitales Nutzerportal",
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Die Einheit des Sensors."""
        # Für monatliche und kumulative Sensoren: kWh
        if self._def.sensor_type in (SENSOR_TYPE_MONTHLY, SENSOR_TYPE_CUMULATIVE):
            readings = self._get_readings()
            if readings:
                return readings[-1].unit if hasattr(readings[-1], "unit") else "kWh"
            return "kWh"

        # Für Zählerstände: aus METER_MAPPING
        prefix = self._def.cost_type[:2]
        config = METER_MAPPING.get(prefix, {})
        return config.get("unit")

    @property
    def native_value(self) -> float | None:
        """Der aktuelle Messwert."""
        data = self.coordinator.data or {}

        if self._def.sensor_type == SENSOR_TYPE_METER:
            # Zählerstand
            meter_readings = data.get("meter_readings_by_cost_type") or {}
            cold_water = data.get("cold_water_data") or {}

            reading = meter_readings.get(self._def.cost_type)
            if reading:
                return reading.value if hasattr(reading, "value") else reading

            # Fallback auf Kaltwasser-Daten
            kw_reading = cold_water.get(self._def.cost_type)
            if kw_reading:
                return kw_reading.value if hasattr(kw_reading, "value") else kw_reading

        elif self._def.sensor_type == SENSOR_TYPE_MONTHLY:
            # Monatlicher Verbrauch (letzter Wert)
            monthly = data.get("monthly_by_cost_type") or {}
            readings = monthly.get(self._def.cost_type, [])
            if readings:
                return readings[-1].value

        elif self._def.sensor_type == SENSOR_TYPE_CUMULATIVE:
            # Kumulativer Verbrauch
            totals = data.get("kwh_totals_by_cost_type") or {}
            return totals.get(self._def.cost_type)

        return None

    @property
    def last_reset(self) -> datetime | None:
        """Gibt das Datum des letzten Resets zurück (für monatliche Sensoren)."""
        if self._def.sensor_type != SENSOR_TYPE_MONTHLY:
            return None

        readings = self._get_readings()
        if not readings:
            return None

        latest = readings[-1]
        if not hasattr(latest, "timestamp"):
            return None

        # Reset am Monatsanfang
        ts = dt_util.as_utc(latest.timestamp)
        return ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Zusätzliche Attribute für den Sensor."""
        attrs: dict[str, Any] = {
            "cost_type": self._def.cost_type,
            "sensor_type": self._def.sensor_type,
        }

        readings = self._get_readings()
        if readings:
            latest = readings[-1]

            # Timestamp hinzufügen
            if hasattr(latest, "timestamp"):
                attrs["last_reading"] = latest.timestamp.isoformat()

            # History (letzte 12 Einträge)
            history = []
            for r in readings[-12:]:
                entry = {"value": r.value if hasattr(r, "value") else r}
                if hasattr(r, "timestamp"):
                    entry["timestamp"] = r.timestamp.isoformat()
                if hasattr(r, "unit"):
                    entry["unit"] = r.unit
                history.append(entry)

            if len(history) > 1:
                attrs["history"] = history

        return attrs

    def _get_readings(self) -> list:
        """Hole die Readings für diesen Sensor."""
        data = self.coordinator.data or {}

        if self._def.sensor_type == SENSOR_TYPE_METER:
            meter_readings = data.get("meter_readings_by_cost_type") or {}
            reading = meter_readings.get(self._def.cost_type)
            if reading:
                return [reading]

            cold_water = data.get("cold_water_data") or {}
            kw_reading = cold_water.get(self._def.cost_type)
            if kw_reading:
                return [kw_reading]

        elif self._def.sensor_type == SENSOR_TYPE_MONTHLY:
            monthly = data.get("monthly_by_cost_type") or {}
            return list(monthly.get(self._def.cost_type, []))

        elif self._def.sensor_type == SENSOR_TYPE_CUMULATIVE:
            histories = data.get("kwh_histories_by_cost_type") or {}
            return list(histories.get(self._def.cost_type, []))

        return []