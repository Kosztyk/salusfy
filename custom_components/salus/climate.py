"""
Adds support for the Salus Thermostat units.
"""
import datetime
import time
import logging
import re
import requests
import json

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.components.climate.const import (
    HVACAction,
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_ID,
    UnitOfTemperature,
)

try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_LOGIN = "https://salus-it500.com/public/login.php"
URL_GET_TOKEN = "https://salus-it500.com/public/control.php"
URL_GET_DATA = "https://salus-it500.com/public/ajax_device_values.php"
URL_SET_DATA = "https://salus-it500.com/includes/set.php"

DEFAULT_NAME = "Salus Thermostat"

MIN_TEMP = 5
MAX_TEMP = 34.5

SUPPORT_FLAGS = ClimateEntityFeature.TARGET_TEMPERATURE


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the climate entity from a config entry."""
    config_data = hass.data[DOMAIN][entry.entry_id]

    name = config_data.get("name", DEFAULT_NAME)
    username = config_data.get(CONF_USERNAME)
    password = config_data.get(CONF_PASSWORD)
    device_id = config_data.get(CONF_ID)

    # Create and add a single SalusThermostat entity
    async_add_entities(
        [SalusThermostat(name, username, password, device_id)],
        update_before_add=True,
    )


class SalusThermostat(ClimateEntity):
    """Representation of a Salus Thermostat device."""

    def __init__(self, name, username, password, device_id):
        """Initialize the thermostat."""
        self._name = name
        self._username = username
        self._password = password
        self._id = device_id
        self._current_temperature = None
        self._target_temperature = None
        self._frost = None
        self._status = None
        self._current_operation_mode = None
        self._token = None
        self._token_timestamp = None
        self._session = requests.Session()

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this thermostat."""
        return f"{self._name}_climate"

    @property
    def should_poll(self):
        """Return if polling is required."""
        return True

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return hvac operation mode."""
        try:
            climate_mode = self._current_operation_mode
            curr_hvac_mode = HVACMode.OFF
            if climate_mode == "ON":
                curr_hvac_mode = HVACMode.HEAT
            else:
                curr_hvac_mode = HVACMode.OFF
        except KeyError:
            return HVACMode.OFF
        return curr_hvac_mode

    @property
    def hvac_modes(self):
        """HVAC modes."""
        return [HVACMode.HEAT, HVACMode.OFF]

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        if (
            self._target_temperature is not None
            and self._current_temperature is not None
        ):
            if self._target_temperature <= self._current_temperature:
                return HVACAction.IDLE
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        return self._status

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        # If you have custom preset modes, define and return them here.
        # Otherwise, return an empty list.
        return []

    @property
    def icon(self) -> str:
        """
        Return a custom icon for the entity.

        Options:
          - Return any official MDI icon name, e.g. "mdi:thermostat".
          - For a truly custom icon, use a custom icon set or reference
            an icon served from /local/.

        Example:
        """
        return "mdi:thermostat"

    @property
    def extra_state_attributes(self):
        """Return extra state attributes for binary sensor compatibility."""
        # Track if currently heating based on target vs current temperature
        is_heating = None
        if self._target_temperature is not None and self._current_temperature is not None:
            is_heating = self._current_temperature < self._target_temperature
        
        return {
            "is_heating": is_heating,
            "ch1_heat_on_off_status_raw": self._status,
        }

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._set_temperature(temperature)

    def _set_temperature(self, temperature):
        """Set new target temperature, via URL commands."""
        payload = {
            "token": self._token,
            "devId": self._id,
            "tempUnit": "0",
            "current_tempZ1_set": "1",
            "current_tempZ1": temperature,
        }
        headers = {"content-type": "application/x-www-form-urlencoded"}
        response = self._session.post(URL_SET_DATA, data=payload, headers=headers)
        if response and response.status_code == 200:
            self._target_temperature = temperature

    def set_hvac_mode(self, hvac_mode):
        """Set HVAC mode, via URL commands."""
        headers = {"content-type": "application/x-www-form-urlencoded"}
        if hvac_mode == HVACMode.OFF:
            payload = {"token": self._token, "devId": self._id, "auto": "1", "auto_setZ1": "1"}
            response = self._session.post(URL_SET_DATA, data=payload, headers=headers)
            if response and response.status_code == 200:
                self._current_operation_mode = "OFF"
        elif hvac_mode == HVACMode.HEAT:
            payload = {"token": self._token, "devId": self._id, "auto": "0", "auto_setZ1": "1"}
            response = self._session.post(URL_SET_DATA, data=payload, headers=headers)
            if response and response.status_code == 200:
                self._current_operation_mode = "ON"

    def get_token(self):
        """Get the Session Token of the Thermostat."""
        payload = {
            "IDemail": self._username,
            "password": self._password,
            "login": "Login"
        }
        headers = {"content-type": "application/x-www-form-urlencoded"}
        self._session.post(URL_LOGIN, data=payload, headers=headers)

        params = {"devId": self._id}
        get_token_resp = self._session.get(URL_GET_TOKEN, params=params)
        if get_token_resp and get_token_resp.status_code == 200:
            result = re.search(r'<input id="token" type="hidden" value="(.*)" />', get_token_resp.text)
            if result:
                self._token = result.group(1)
                self._token_timestamp = int(time.time())
                _LOGGER.info("Got new token. Timestamp: %s", self._token_timestamp)

    def _get_data(self):
        """Retrieve data from the device."""
        cur_timestamp = int(time.time())
        _LOGGER.debug("Starting _get_data. Timestamp: %s", cur_timestamp)

        # if no token or token older than 1h, re-login
        if self._token is None or (cur_timestamp - (self._token_timestamp or 0)) > 3600:
            _LOGGER.debug("No token or token expired, calling get_token().")
            self.get_token()

        if not self._token:
            _LOGGER.error("Could not get a valid token from Salus.")
            return

        params = {
            "devId": self._id,
            "token": self._token,
            "&_": str(int(round(time.time() * 1000))),
        }
        r = self._session.get(URL_GET_DATA, params=params)
        if r and r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                _LOGGER.error("Invalid JSON returned from Salus.")
                return

            self._target_temperature = float(data.get("CH1currentSetPoint", 0))
            self._current_temperature = float(data.get("CH1currentRoomTemp", 0))
            self._frost = float(data.get("frost", 0))

            # On/Off status
            status = data.get("CH1heatOnOffStatus", "0")
            self._status = "ON" if status == "1" else "OFF"

            # Manual/Auto mode
            mode = data.get("CH1heatOnOff", "1")
            if mode == "1":
                self._current_operation_mode = "OFF"
            else:
                self._current_operation_mode = "ON"
        else:
            _LOGGER.error(
                "Could not get data from Salus (status_code=%s).",
                r.status_code if r else "No response",
            )

    def update(self):
        """Get the latest data from Salus."""
        self._get_data()
