"""
Adds support for the Salus Thermostat units.
"""
import time
import logging
import re
import requests

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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_LOGIN = "https://salus-it500.com/public/login.php"
URL_CONTROL = "https://salus-it500.com/public/control.php"
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

    async_add_entities(
        [SalusThermostat(name, username, password, device_id)],
        update_before_add=True,
    )


class SalusThermostat(ClimateEntity):
    """Representation of a Salus Thermostat device."""

    def __init__(self, name, username, password, device_id):
        self._name = name
        self._username = username
        self._password = password
        self._id = device_id

        self._current_temperature = None
        self._target_temperature = None
        self._current_operation_mode = None

        # Device-reported heating status (CH1heatOnOffStatus)
        self._heat_onoff_status_raw = None  # "0" / "1" (string)
        self._is_heating = None  # True/False
        self._status = None  # "ON" / "OFF" (friendly)

        self._token = None
        self._token_timestamp = None
        self._session = requests.Session()

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self) -> str:
        return f"{self._name}_climate"

    @property
    def should_poll(self):
        return True

    @property
    def min_temp(self):
        return MIN_TEMP

    @property
    def max_temp(self):
        return MAX_TEMP

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        if self._current_operation_mode == "OFF":
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT, HVACMode.OFF]

    @property
    def hvac_action(self):
        """
        Return the running action.

        Per your request: use device truth (CH1heatOnOffStatus) when available.
        Fallback to temperature-based inference only if the device status is not known yet.
        """
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        if self._is_heating is not None:
            return HVACAction.HEATING if self._is_heating else HVACAction.IDLE

        # Fallback (legacy): infer from current vs target (only if both known)
        if self._target_temperature is not None and self._current_temperature is not None:
            return HVACAction.HEATING if self._current_temperature < self._target_temperature else HVACAction.IDLE

        return HVACAction.IDLE

    @property
    def extra_state_attributes(self):
        return {
            "ch1_heat_on_off_status_raw": self._heat_onoff_status_raw,
            "ch1_heat_on_off_status": self._status,  # "ON"/"OFF"
            "is_heating": self._is_heating,
        }

    def set_temperature(self, **kwargs):
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            temperature = kwargs.get(ATTR_TEMPERATURE)
            self._target_temperature = temperature
            self._set_data(temperature)

    def turn_off(self):
        self._current_operation_mode = "OFF"
        self._set_data(self._target_temperature, off=True)

    def turn_on(self):
        self._current_operation_mode = "ON"
        self._set_data(self._target_temperature)

    # ---------------------------
    # TOKEN / AUTH
    # ---------------------------

    def get_token(self):
        """Login and scrape the session token from control.php."""
        try:
            _LOGGER.debug("Requesting new token for Salus user: %s", self._username)

            payload = {
                "IDemail": self._username,
                "password": self._password,
                "login": "Login",
            }
            headers = {"content-type": "application/x-www-form-urlencoded"}

            # Step 1: login (establish session cookies)
            login_resp = self._session.post(URL_LOGIN, data=payload, headers=headers, timeout=30)
            if not login_resp or login_resp.status_code not in (200, 302):
                _LOGGER.error("Salus login failed: status_code=%s", getattr(login_resp, "status_code", None))
                return

            # Step 2: fetch control page (contains hidden token)
            ctrl_resp = self._session.get(URL_CONTROL, params={"devId": self._id}, timeout=30)
            if not ctrl_resp or ctrl_resp.status_code != 200:
                _LOGGER.error("Salus control page fetch failed: status_code=%s", getattr(ctrl_resp, "status_code", None))
                return

            html = ctrl_resp.text or ""

            # Try multiple patterns (site markup varies)
            patterns = [
                r'id=["\']token["\'][^>]*value=["\']([^"\']+)["\']',           # <input id="token" ... value="...">
                r'name=["\']token["\'][^>]*value=["\']([^"\']+)["\']',         # <input name="token" ... value="...">
                r"token'\s*:\s*'([^']+)'",                                     # 'token': '...'
                r'"token"\s*:\s*"([^"]+)"',                                    # "token": "..."
                r"token\s*=\s*['\"]([^'\"]+)['\"]",                            # token = "..."
            ]

            token = None
            for pat in patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    token = m.group(1)
                    break

            if not token:
                # Log a short snippet to help future debugging without dumping full HTML
                snippet = html[:300].replace("\n", " ").replace("\r", " ")
                _LOGGER.error("Could not parse token from control.php HTML. Snippet: %s", snippet)
                return

            self._token = token
            self._token_timestamp = int(time.time())
            _LOGGER.info("Got new token. Timestamp: %s", self._token_timestamp)

        except Exception as ex:
            _LOGGER.error("Error during token retrieval: %s", ex)

    # ---------------------------
    # SET / GET DATA
    # ---------------------------

    def _set_data(self, temperature, off=False):
        """Send data to the thermostat."""
        if not self._token:
            self.get_token()

        if not self._token:
            _LOGGER.error("No token available; cannot set temperature.")
            return

        # Preserve your existing on/off semantics
        heat_onoff = "1" if off else "0"

        payload = {
            "token": self._token,
            "devId": self._id,
            "heatOnOff": heat_onoff,
            "currentSetPoint": temperature,
        }

        r = self._session.post(URL_SET_DATA, data=payload, timeout=30)
        if not r or r.status_code != 200:
            _LOGGER.error("Error setting data: status_code=%s", getattr(r, "status_code", None))

    def _get_data(self):
        """Retrieve data from the device."""
        cur_timestamp = int(time.time())
        _LOGGER.debug("Starting _get_data. Timestamp: %s", cur_timestamp)

        # Token refresh if older than 1h
        if self._token is None or (cur_timestamp - (self._token_timestamp or 0)) > 3600:
            _LOGGER.debug("No token or token expired, calling get_token().")
            self.get_token()

        if not self._token:
            _LOGGER.error("Could not get a valid token from Salus.")
            return

        r = self._session.get(URL_GET_DATA, params={"token": self._token, "devId": self._id}, timeout=30)
        if not r or r.status_code != 200:
            _LOGGER.error("Could not get data from Salus: status_code=%s", getattr(r, "status_code", None))
            return

        data = r.json() or {}
        if not data:
            _LOGGER.error("No JSON data returned from Salus.")
            return

        # Temperatures
        try:
            self._target_temperature = float(data.get("CH1currentSetPoint"))
        except Exception:
            self._target_temperature = None

        try:
            self._current_temperature = float(data.get("CH1currentRoomTemp"))
        except Exception:
            self._current_temperature = None

        # Operation mode (preserve your existing mapping)
        mode = str(data.get("CH1heatOnOff", "1"))
        self._current_operation_mode = "OFF" if mode == "1" else "ON"

        # Device-reported heating output status (CH1heatOnOffStatus)
        raw = data.get("CH1heatOnOffStatus", "0")
        self._heat_onoff_status_raw = str(raw)
        self._is_heating = self._heat_onoff_status_raw == "1"
        self._status = "ON" if self._is_heating else "OFF"

    def update(self):
        """Get the latest data from Salus."""
        self._get_data()
