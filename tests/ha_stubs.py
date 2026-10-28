"""Small HA interface stubs for offline flow/entity/coordinator behavior tests.

These do not emulate Home Assistant's runtime; cloud protocol tests use actual
client code, while these stubs cover migration and error-handling contracts.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from enum import IntFlag, StrEnum
import re
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class HAError(Exception):
    pass


class AuthFailed(HAError):
    pass


class NotReady(HAError):
    pass


class UpdateFailed(HAError):
    pass


class Entity:
    pass


class Restore:
    pass


class Coordinator:
    @classmethod
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, *, config_entry, name, update_interval):
        self.hass = hass
        self.config_entry = config_entry
        self.data = None
        self.last_update_success = True

    def async_set_updated_data(self, data):
        self.data = data
        self.last_update_success = True

    async def async_config_entry_first_refresh(self):
        self.async_set_updated_data(await self._async_update_data())


class CoordinatorEntity:
    @classmethod
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def available(self):
        return self.coordinator.last_update_success


class HVACMode(StrEnum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    AUTO = "auto"


class HVACAction(StrEnum):
    OFF = "off"
    IDLE = "idle"
    HEATING = "heating"
    COOLING = "cooling"


class Features(IntFlag):
    TARGET_TEMPERATURE = 1
    TURN_ON = 2
    TURN_OFF = 4


class Flow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass

    def _async_current_entries(self):
        return getattr(self, "entries", [])

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}

    def _get_reauth_entry(self):
        return self.reauth_entry

    # Match the real HA helper signature: unknown options_updates must fail.
    def async_update_reload_and_abort(self, entry, *, data_updates, options):
        entry.data = {**entry.data, **data_updates}
        entry.options = options
        self.reload_requested = True
        return self.async_abort(reason="reauth_successful")


class OptionsFlowWithReload(Flow):
    automatic_reload = True


@contextmanager
def interfaces():
    modules = {}

    def module(name, **attributes):
        result = ModuleType(name)
        result.__path__ = []
        result.__dict__.update(attributes)
        modules[name] = result
        if "." in name:
            parent, child = name.rsplit(".", 1)
            if parent not in modules:
                module(parent)
            setattr(modules[parent], child, result)
        return result

    module("homeassistant.config_entries", ConfigEntry=object, ConfigFlow=Flow, OptionsFlow=Flow, OptionsFlowWithReload=OptionsFlowWithReload)
    module("homeassistant.core", HomeAssistant=object, callback=lambda f: f)
    module("homeassistant.exceptions", ConfigEntryAuthFailed=AuthFailed, ConfigEntryNotReady=NotReady, HomeAssistantError=HAError)
    module("homeassistant.const", CONF_ID="id", CONF_USERNAME="username", CONF_PASSWORD="password", ATTR_TEMPERATURE="temperature", UnitOfTemperature=SimpleNamespace(CELSIUS="°C"), STATE_UNAVAILABLE="unavailable", STATE_UNKNOWN="unknown")
    module("homeassistant.helpers.update_coordinator", CoordinatorEntity=CoordinatorEntity, DataUpdateCoordinator=Coordinator, UpdateFailed=UpdateFailed)
    module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
    module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry, async_entries_for_config_entry=lambda registry, entry_id: registry.entries)
    module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    module("homeassistant.helpers.entity", EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic", CONFIG="config"))
    module("homeassistant.helpers.restore_state", RestoreEntity=Restore)
    module("homeassistant.helpers.selector", TextSelector=lambda config: config, TextSelectorConfig=lambda **kwargs: kwargs, TextSelectorType=SimpleNamespace(PASSWORD="password"))
    module("homeassistant.components.climate", ClimateEntity=Entity)
    module("homeassistant.components.climate.const", ClimateEntityFeature=Features, HVACAction=HVACAction, HVACMode=HVACMode)
    module("homeassistant.components.sensor", SensorEntity=Entity, SensorDeviceClass=SimpleNamespace(TEMPERATURE="temperature", DURATION="duration", BATTERY="battery"), SensorStateClass=SimpleNamespace(MEASUREMENT="measurement"))
    module("homeassistant.components.binary_sensor", BinarySensorEntity=Entity, BinarySensorDeviceClass=SimpleNamespace(BATTERY="battery"))
    module("homeassistant.components.select", SelectEntity=Entity)
    module("homeassistant.components.number", NumberEntity=Entity)
    module("homeassistant.util.dt", now=lambda: datetime.now(timezone.utc))
    module("homeassistant.util", slugify=lambda text: re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_"))
    module("voluptuous", Schema=lambda schema: schema, Required=lambda key, **kwargs: key, Optional=lambda key, **kwargs: key, In=lambda values: values)
    with patch.dict(sys.modules, modules):
        yield
