"""Mobile-cloud polling, capability discovery, and serialized thermostat commands."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import math
import time

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SalusAuthError, SalusClient, SalusError
from .runtime import HeatingRuntime
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_TEMP, MIN_TEMP
from .model import Mode, ThermostatState, HOT_WATER_MODES, can_set_mode, can_set_temperature, decode, heating_zones, mode_writes, value, has_hot_water

_LOGGER = logging.getLogger(__name__)
CONFIRM_DELAYS = (3, 3, 4, 5)


class SalusCoordinator(DataUpdateCoordinator[ThermostatState]):
    """Share device attributes across all heating zones and read-only devices."""

    def __init__(self, hass, entry, client: SalusClient, device_id: str, device_type_id: str = "") -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN,
                         update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL))
        self.entry = entry
        self.client = client
        self.device_id = device_id
        self.device_type_id = device_type_id
        self.attributes = {}
        self.zones: tuple[str, ...] = ()
        self._command_lock = asyncio.Lock()
        self.runtime = HeatingRuntime()
        self.device = None

    def zone_state(self, zone: str = "A") -> ThermostatState:
        """Return the independently decoded state of a discovered heating zone."""
        return decode(self.attributes, zone)

    async def _async_update_data(self) -> ThermostatState:
        try:
            if self.device_type_id:
                attributes = await self.client.async_get_attributes(self.device_id, self.device_type_id)
            else:
                attributes = await self.client.async_get_attributes(self.device_id)
        except SalusAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SalusError as err:
            raise UpdateFailed(str(err)) from err
        if not attributes:
            raise UpdateFailed("SALUS returned no device attributes")
        zones = heating_zones(attributes)
        state = decode(attributes)
        if "A" in zones and state.current_temperature is None and state.target_temperature is None and state.online is not False:
            raise UpdateFailed("SALUS returned no zone-one thermostat readings")
        self.attributes = attributes
        self.zones = zones
        # A87 reports actual relay activation. Cooling is not heating runtime.
        active = (state.heating if "A" in zones and state.online is not False
                  and value(attributes, "S05") != "1" else None)
        self.runtime.observe(dt_util.now(), active)
        return state

    async def _async_command(self, writes: list[tuple[str, str]]) -> None:
        """Wake known heating devices, check ack, then require a fresh readback."""
        async with self._command_lock:
            if not self.last_update_success or self.data is None or self.data.online is False:
                raise HomeAssistantError("The SALUS device is unavailable")
            pending = [(n, v) for n, v in writes if n not in self.attributes or self.attributes[n].value != v]
            if not pending:
                return
            since_ms = int(time.time() * 1000) - 2000
            try:
                # Both bundled Android APKs send F=1, not F=60.
                if "F" in self.attributes or self.zones:
                    await self.client.async_set_attribute(self.device_id, "F", "1")
                for name, val in pending:
                    await self.client.async_set_attribute(self.device_id, name, val)
                for delay in CONFIRM_DELAYS:
                    await asyncio.sleep(delay)
                    try:
                        state = await self._async_update_data()
                    except UpdateFailed:
                        continue
                    self.async_set_updated_data(state)
                    if all(
                        name in self.attributes
                        and self.attributes[name].value == val
                        and self.attributes[name].updated_ms >= since_ms
                        for name, val in pending
                    ):
                        return
            except (SalusAuthError, ConfigEntryAuthFailed) as err:
                self.entry.async_start_reauth(self.hass)
                raise HomeAssistantError("SALUS requires authentication again") from err
            except SalusError as err:
                raise HomeAssistantError(str(err)) from err
            raise HomeAssistantError("SALUS accepted the command but the device has not confirmed it yet")

    async def async_set_temperature(self, temperature: float, zone: str = "A") -> None:
        if zone not in self.zones or not can_set_temperature(self.attributes, zone):
            raise HomeAssistantError(f"SALUS zone {zone} does not expose target-temperature control")
        if not math.isfinite(temperature) or not MIN_TEMP <= temperature <= MAX_TEMP:
            raise HomeAssistantError(f"Temperature must be between {MIN_TEMP} and {MAX_TEMP} °C")
        writes = [(f"{zone}85", str(round(temperature * 10) * 10))]
        # During scheduled operation, setting a temperature starts an override
        # in the RT310i app (A88/B88=1). Manual mode retains its saved program.
        if self.zone_state(zone).mode == Mode.AUTO and f"{zone}88" in self.attributes:
            writes.append((f"{zone}88", "1"))
        await self._async_command(writes)

    async def async_set_mode(self, mode: Mode, zone: str = "A") -> None:
        if zone not in self.zones or not can_set_mode(self.attributes, zone):
            raise HomeAssistantError(f"SALUS zone {zone} does not expose the app's mode controls")
        await self._async_command(mode_writes(mode, zone))

    async def async_set_hot_water_mode(self, mode: str) -> None:
        """iT500 hot-water C42: 0 Schedule, 1 Once, 2 On, 3 Off."""
        if not has_hot_water(self.attributes) or "C42" not in self.attributes or mode not in HOT_WATER_MODES.values():
            raise HomeAssistantError("The SALUS device does not expose a supported hot-water mode")
        code = next(k for k, label in HOT_WATER_MODES.items() if label == mode)
        await self._async_command([("C42", code)])

    async def async_set_hot_water_boost(self, hours: int) -> None:
        """iT500 C43 boost: 0 Off, or 1-3 hours."""
        if not has_hot_water(self.attributes) or "C43" not in self.attributes or type(hours) is not int or hours not in (0, 1, 2, 3):
            raise HomeAssistantError("The SALUS device does not expose hot-water boost (0-3 h)")
        await self._async_command([("C43", str(hours))])
