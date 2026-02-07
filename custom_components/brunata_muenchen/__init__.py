"""Brunata München Integration für Home Assistant."""

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from brunata_api import BrunataClient, ReadingKind
from brunata_api.models import MeterReading, Reading

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup Brunata München via Config Flow."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = BrunataMuenchenCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Weiterleitung an die Sensor-Plattform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload_ok


def _kind_from_cost_type(cost_type: str) -> ReadingKind:
    """Bestimme den ReadingKind basierend auf dem Kostenart-Präfix."""
    if cost_type.startswith("HZ"):
        return ReadingKind.heating
    if cost_type.startswith("WW"):
        return ReadingKind.hot_water
    # Fallback für unbekannte Typen (z.B. KW)
    return ReadingKind.heating


def _build_cumulative_history(
    cost_type: str, monthly_readings: list[Reading]
) -> list[MeterReading]:
    """Erstelle kumulative kWh-Historie aus Monats-Readings."""
    if not monthly_readings:
        return []

    sorted_readings = sorted(monthly_readings, key=lambda r: r.timestamp)
    unit = sorted_readings[-1].unit if sorted_readings else "kWh"
    unit = unit or "kWh"

    total = 0.0
    history: list[MeterReading] = []

    for reading in sorted_readings:
        total += float(reading.value)
        history.append(
            MeterReading(
                timestamp=reading.timestamp,
                value=round(total, 6),
                unit=unit,
                cost_type=cost_type,
                kind=_kind_from_cost_type(cost_type),
            )
        )

    return history


class BrunataMuenchenCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Klasse zur Verwaltung des Datenabrufs mit erweiterter Datenstruktur."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self._client: BrunataClient | None = None
        self._client_lock = asyncio.Lock()

    def _create_client(self) -> BrunataClient:
        """Erstelle den API Client."""
        return BrunataClient(
            base_url=self.entry.data[CONF_URL],
            username=self.entry.data[CONF_USERNAME],
            password=self.entry.data[CONF_PASSWORD],
            sap_client=self.entry.data.get("sap_client", "201"),
        )

    async def _async_get_client(self) -> BrunataClient:
        """Hole oder erstelle den API Client."""
        if self._client is not None:
            return self._client

        async with self._client_lock:
            if self._client is not None:
                return self._client

            self._client = await self.hass.async_add_executor_job(self._create_client)
            return self._client

    async def async_shutdown(self) -> None:
        """Schließe den Client beim Entladen."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Daten von der API abrufen mit erweiterter Struktur."""
        try:
            client = await self._async_get_client()

            # Login sicherstellen
            await client.login()

            # Paralleler Abruf der Hauptdaten
            meter_readings_task = client.get_meter_readings()
            monthly_heating_task = client.get_monthly_consumptions(
                ReadingKind.heating, in_kwh=True
            )
            monthly_hot_water_task = client.get_monthly_consumptions(
                ReadingKind.hot_water, in_kwh=True
            )
            supported_types_task = client.get_supported_cost_types()

            (
                meter_readings_by_cost_type,
                monthly_heating_by_cost_type,
                monthly_hot_water_by_cost_type,
                supported_types,
            ) = await asyncio.gather(
                meter_readings_task,
                monthly_heating_task,
                monthly_hot_water_task,
                supported_types_task,
            )

            # Zusammenführen der monatlichen Daten
            monthly_by_cost_type: dict[str, list[Reading]] = {}
            monthly_by_cost_type.update(monthly_heating_by_cost_type or {})
            monthly_by_cost_type.update(monthly_hot_water_by_cost_type or {})

            # Kaltwasser-Daten separat abrufen (KW-Präfix)
            cold_water_data: dict[str, Any] = {}
            if supported_types:
                latest_period = list(supported_types.keys())[-1]
                meter_ids = supported_types[latest_period]

                for meter_id in meter_ids:
                    if meter_id.startswith("KW"):
                        try:
                            data = await client.get_monthly_consumption(cost_type=meter_id)
                            if data:
                                cold_water_data[meter_id] = data[-1]
                        except Exception as err:
                            _LOGGER.debug("Fehler beim Abruf von %s: %s", meter_id, err)

            # Kumulative kWh-Historien berechnen
            kwh_histories_by_cost_type: dict[str, list[MeterReading]] = {}
            kwh_totals_by_cost_type: dict[str, float] = {}

            for cost_type, monthly in monthly_by_cost_type.items():
                if not monthly:
                    continue
                history = _build_cumulative_history(cost_type, monthly)
                if history:
                    kwh_histories_by_cost_type[cost_type] = history
                    kwh_totals_by_cost_type[cost_type] = history[-1].value

            # Datenstruktur zusammenstellen
            data: dict[str, Any] = {
                "meter_readings_by_cost_type": meter_readings_by_cost_type or {},
                "monthly_by_cost_type": monthly_by_cost_type,
                "kwh_histories_by_cost_type": kwh_histories_by_cost_type,
                "kwh_totals_by_cost_type": kwh_totals_by_cost_type,
                "cold_water_data": cold_water_data,
            }

            _LOGGER.debug(
                "Brunata Daten aktualisiert: %d Zähler, %d Monatsserien, %d KW-Zähler",
                len(meter_readings_by_cost_type or {}),
                len(monthly_by_cost_type),
                len(cold_water_data),
            )

            return data

        except Exception as err:
            _LOGGER.error("Fehler beim Abruf der Brunata Daten: %s", err)
            raise UpdateFailed(f"Fehler beim Abruf der Brunata Daten: {err}") from err