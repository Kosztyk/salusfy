"""The Salus component."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SalusAuthError, SalusClient, SalusDeviceError, SalusError, select_device
from .const import DOMAIN
from .coordinator import SalusCoordinator

PLATFORMS = ["climate", "sensor", "binary_sensor"]


def _merged_entry_config(entry: ConfigEntry) -> dict:
    """Return config with options overriding data."""
    return {**dict(entry.data), **dict(entry.options)}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Salus integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    config = _merged_entry_config(entry)
    client = SalusClient(async_get_clientsession(hass), config[CONF_USERNAME], config[CONF_PASSWORD])
    try:
        device = select_device(await client.async_get_devices(), config.get(CONF_ID))
    except SalusAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SalusDeviceError as err:
        raise ConfigEntryNotReady(f"{err}; select the thermostat in the integration options") from err
    except SalusError as err:
        raise ConfigEntryNotReady(str(err)) from err
    coordinator = SalusCoordinator(hass, entry, client, device.device_id)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = {**config, "coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
