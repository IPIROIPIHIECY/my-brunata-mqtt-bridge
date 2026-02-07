import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_URL
from brunata_api import BrunataClient
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

class BrunataMuenchenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Behandelt den Setup-Dialog in der UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt bei der manuellen Einrichtung."""
        errors = {}
        if user_input is not None:
            try:
                # Validierung: Klappt der Login mit diesen Daten?
                client = BrunataClient(
                    base_url=user_input[CONF_URL],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    sap_client=user_input["sap_client"],
                )
                async with client:
                    await client.login()
                
                return self.async_create_entry(
                    title=f"Brunata ({user_input[CONF_USERNAME]})", 
                    data=user_input
                )
            except Exception:
                errors["base"] = "auth_error"

        # Das Formular, das der Nutzer sieht
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_URL, default="https://nutzerportal.brunata-muenchen.de"): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required("sap_client", default="201"): str,
            }),
            errors=errors,
        )