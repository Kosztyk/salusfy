"""Shared mobile API polling and serialized thermostat commands."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import math
import time

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SalusAuthError, SalusClient, SalusError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_TEMP, MIN_TEMP
from .model import Mode, ThermostatState, decode, mode_writes

_LOGGER = logging.getLogger(__name__)
CONFIRM_DELAYS = (3, 3, 4, 5)


class SalusCoordinator(DataUpdateCoordinator[ThermostatState]):
    """Fetch cloud data without blocking the Home Assistant event loop."""

    def __init__(self, hass, entry, client: SalusClient, device_id: str) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL))
        self.entry = entry
        self.client = client
        self.device_id = device_id
        self.attributes = {}
        self._command_lock = asyncio.Lock()

    async def _async_update_data(self) -> ThermostatState:
        try:
            attributes = await self.client.async_get_attributes(self.device_id)
        except SalusAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SalusError as err:
            raise UpdateFailed(str(err)) from err
        state = decode(attributes)
        if state.current_temperature is None and state.target_temperature is None and state.online is not False:
            raise UpdateFailed("SALUS returned no thermostat readings")
        self.attributes = attributes
        return state

    async def _async_command(self, writes: list[tuple[str, str]]) -> None:
        """Wake on commands only, check acknowledgements, then read back."""
        async with self._command_lock:
            if not self.last_update_success or self.data is None or self.data.online is False:
                raise HomeAssistantError("The SALUS thermostat is unavailable")
            pending = [(n, v) for n, v in writes if n not in self.attributes or self.attributes[n].value != v]
            if not pending:
                return
            since_ms = int(time.time() * 1000) - 2000
            try:
                await self.client.async_set_attribute(self.device_id, "F", "60")
                for name, value in pending:
                    await self.client.async_set_attribute(self.device_id, name, value)
                for delay in CONFIRM_DELAYS:
                    await asyncio.sleep(delay)
                    try:
                        state = await self._async_update_data()
                    except UpdateFailed:
                        continue
                    self.async_set_updated_data(state)
                    if all(
                        name in self.attributes
                        and self.attributes[name].value == value
                        and self.attributes[name].updated_ms >= since_ms
                        for name, value in pending
                    ):
                        return
            except (SalusAuthError, ConfigEntryAuthFailed) as err:
                self.entry.async_start_reauth(self.hass)
                raise HomeAssistantError("SALUS requires authentication again") from err
            except SalusError as err:
                raise HomeAssistantError(str(err)) from err
            raise HomeAssistantError("SALUS accepted the command but the thermostat has not confirmed it yet")

    async def async_set_temperature(self, temperature: float) -> None:
        if not math.isfinite(temperature) or not MIN_TEMP <= temperature <= MAX_TEMP:
            raise HomeAssistantError(f"Temperature must be between {MIN_TEMP} and {MAX_TEMP} °C")
        await self._async_command([("A85", str(round(temperature * 10) * 10))])

    async def async_set_mode(self, mode: Mode) -> None:
        await self._async_command(mode_writes(mode))
