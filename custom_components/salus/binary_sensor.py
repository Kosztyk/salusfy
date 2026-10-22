import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .climate import DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)


def _resolve_climate_entity_id(hass: HomeAssistant, name: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("climate", DOMAIN, f"{name}_climate")
    return entity_id or "climate.salus_thermostat"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up binary_sensor entities for the Salus integration from a config entry."""
    config_data = hass.data[DOMAIN][entry.entry_id]
    climate_name = config_data.get("name", DEFAULT_NAME)
    climate_entity_id = _resolve_climate_entity_id(hass, climate_name)
    async_add_entities([SalusCh1HeatOnOffBinarySensor(climate_entity_id)], update_before_add=True)


class SalusCh1HeatOnOffBinarySensor(BinarySensorEntity):
    """Binary sensor reflecting the gateway heating output (CH1heatOnOffStatus)."""

    def __init__(self, climate_entity_id: str) -> None:
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Salus Heating Output"
        self._attr_unique_id = f"{climate_entity_id}_ch1_heat_on_off_status"
        self._attr_icon = "mdi:radiator"

        self._attr_is_on = None
        self._attr_available = False

    async def async_update(self) -> None:
        if not self.hass:
            return

        climate_state = self.hass.states.get(self._climate_entity_id)
        if not climate_state or climate_state.state in ("unavailable", "unknown"):
            self._attr_is_on = None
            self._attr_available = False
            return

        attrs = climate_state.attributes or {}

        is_heating = attrs.get("is_heating")
        if isinstance(is_heating, bool):
            self._attr_is_on = is_heating
            self._attr_available = True
            return

        raw = attrs.get("ch1_heat_on_off_status_raw")
        if raw is None:
            self._attr_is_on = None
            self._attr_available = False
            return

        self._attr_is_on = str(raw) == "1"
        self._attr_available = True
