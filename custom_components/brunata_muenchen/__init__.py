import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_URL
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from brunata_api import BrunataClient

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry):
    """Setup Brunata München via Config Flow."""
    client = BrunataClient(
        base_url=entry.data["CONF_URL"],
        username=entry.data["CONF_USERNAME"],
        password=entry.data["CONF_PASSWORD"],
        sap_client=entry.data["sap_client"],
    )

    coordinator = BrunataMuenchenCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    # Weiterleitung an die Sensor-Plattform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

class BrunataMuenchenCoordinator(DataUpdateCoordinator):
    """Klasse zur Verwaltung des Datenabrufs."""

    def __init__(self, hass, client):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=12), # Brunata reicht 2x am Tag
        )
        self.client = client

    async def _async_update_data(self):
        """Daten von der API abrufen."""
        try:
            async with self.client:
                await self.client.login()
                
                # Dynamisches Discovery: Welche Kostenarten existieren?
                periods = await self.client.get_supported_cost_types()
                if not periods:
                    return {}

                # Nimm die aktuellste Periode
                latest_period = list(periods.keys())[-1]
                meter_ids = periods[latest_period]

                results = {}
                for meter_id in meter_ids:
                    # Abruf für jeden einzelnen Zähler
                    data = await self.client.get_monthly_consumption(cost_type=meter_id)
                    if data:
                        # Wir speichern das komplette letzte Objekt
                        results[meter_id] = data[-1]
                
                return results
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abruf der Brunata Daten: {err}")