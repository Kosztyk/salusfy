import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_ID
import homeassistant.helpers.config_validation as cv

from . import DOMAIN


class SalusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Salus Thermostat."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the options flow."""
        return SalusOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title="Salus Thermostat",
                data={
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_ID: user_input[CONF_ID],
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_ID): cv.string,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


class SalusOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to allow updating credentials/device id."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        # HA 2026+ exposes config_entry as a read-only property on OptionsFlow.
        # Different HA versions have different __init__ signatures, so guard it.
        try:
            super().__init__(config_entry)
        except TypeError:
            super().__init__()
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the Salus options."""
        if user_input is not None:
            # Store in entry.options; integration should prefer options over data.
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=current.get(CONF_USERNAME, "")): cv.string,
                vol.Required(CONF_PASSWORD, default=current.get(CONF_PASSWORD, "")): cv.string,
                vol.Required(CONF_ID, default=current.get(CONF_ID, "")): cv.string,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
