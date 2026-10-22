"""Validate the app credentials and discover iT500 devices without the website."""

from collections.abc import Mapping

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SalusAuthError, SalusClient, SalusDeviceError, SalusError, select_device
from .const import DEFAULT_NAME, DOMAIN

CREDENTIAL_KEYS = (CONF_USERNAME, CONF_PASSWORD, CONF_ID)


def _merged_config(entry):
    return {**entry.data, **entry.options}


def _schema(current=None):
    current = current or {}
    return vol.Schema({
        vol.Required(CONF_USERNAME, default=current.get(CONF_USERNAME, "")): str,
        vol.Required(CONF_PASSWORD, default=current.get(CONF_PASSWORD, "")): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_ID, default=current.get(CONF_ID, "")): str,
    })


def _device_schema(devices):
    return vol.Schema({vol.Required(CONF_ID): vol.In({d.device_id: f"{d.name} ({d.device_id})" for d in devices})})


async def _fetch_devices(hass, credentials):
    client = SalusClient(
        async_get_clientsession(hass), credentials[CONF_USERNAME], credentials[CONF_PASSWORD]
    )
    devices = [d for d in await client.async_get_devices() if d.type_id == "1"]
    if not devices:
        raise SalusDeviceError("No iT500 devices on this account")
    return devices


class DeviceFlowMixin:
    """Share validation and device selection between initial setup and options."""

    async def _async_validate(self, user_input):
        self._devices = await _fetch_devices(self.hass, user_input)
        self._pending = dict(user_input)
        if not user_input.get(CONF_ID) and len(self._devices) > 1:
            return await self.async_step_device()
        return await self._async_finish(select_device(self._devices, user_input.get(CONF_ID)))

    async def async_step_device(self, user_input=None):
        if user_input is not None:
            return await self._async_finish(select_device(self._devices, user_input[CONF_ID]))
        return self.async_show_form(step_id="device", data_schema=_device_schema(self._devices))


class SalusConfigFlow(DeviceFlowMixin, config_entries.ConfigFlow, domain=DOMAIN):
    """Retain config entry version and existing username/password/id keys."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SalusOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                return await self._async_validate(user_input)
            except SalusAuthError:
                errors["base"] = "invalid_auth"
            except SalusDeviceError:
                errors["base"] = "invalid_device"
            except SalusError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", data_schema=_schema(user_input), errors=errors)

    async def _async_finish(self, device):
        await self.async_set_unique_id(device.device_id)
        self._abort_if_unique_id_configured()
        # Older entries have no unique_id. Avoid duplicating those too.
        for entry in self._async_current_entries():
            current = _merged_config(entry)
            if str(current.get(CONF_ID, "")) in (device.device_id, device.name):
                return self.async_abort(reason="already_configured")
        name = DEFAULT_NAME if not self._async_current_entries() else f"Salus {device.name}"
        return self.async_create_entry(
            title=name,
            data={**self._pending, CONF_ID: device.device_id, "name": name},
        )

    async def async_step_reauth(self, entry_data: Mapping):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        entry = self._get_reauth_entry()
        current = _merged_config(entry)
        if user_input is not None:
            credentials = {**user_input, CONF_ID: current.get(CONF_ID, "")}
            try:
                select_device(await _fetch_devices(self.hass, credentials), credentials[CONF_ID])
            except SalusAuthError:
                errors["base"] = "invalid_auth"
            except SalusDeviceError:
                errors["base"] = "invalid_device"
            except SalusError:
                errors["base"] = "cannot_connect"
            else:
                # Both data and options may hold credentials in older installations.
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=credentials,
                    options={**entry.options, **credentials},
                )
        schema = vol.Schema({
            vol.Required(CONF_USERNAME, default=current.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        })
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)


class SalusOptionsFlowHandler(DeviceFlowMixin, config_entries.OptionsFlowWithReload):
    """Keep the original Configure flow and validate changes before saving."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        current = _merged_config(self._config_entry)
        if user_input is not None:
            try:
                return await self._async_validate(user_input)
            except SalusAuthError:
                errors["base"] = "invalid_auth"
            except SalusDeviceError:
                errors["base"] = "invalid_device"
            except SalusError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="init", data_schema=_schema(user_input or current), errors=errors
        )

    async def _async_finish(self, device):
        return self.async_create_entry(
            title="", data={**self._config_entry.options, **self._pending, CONF_ID: device.device_id}
        )
