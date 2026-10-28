"""iT500-compatible hot-water mode selection, discovered from cloud capabilities."""

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device import link_entity
from .model import HOT_WATER_MODES, value, flag, has_hot_water


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if has_hot_water(coordinator.attributes) and "C42" in coordinator.attributes:
        entity = SalusHotWaterModeSelect(coordinator)
        link_entity(entity, coordinator)
        async_add_entities([entity])


class SalusHotWaterModeSelect(CoordinatorEntity, SelectEntity):
    """iT500 Plus: C42 is 0 Schedule, 1 Once, 2 On, 3 Off."""

    _attr_has_entity_name = True
    _attr_name = "Hot water mode"
    _attr_icon = "mdi:water-boiler"
    _attr_options = ["Schedule", "Once", "On", "Off"]

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_hot_water_mode_select"

    @property
    def available(self):
        return (super().available and flag(self.coordinator.attributes, "online") is not False
                and value(self.coordinator.attributes, "C42") in HOT_WATER_MODES)

    @property
    def current_option(self):
        return HOT_WATER_MODES.get(value(self.coordinator.attributes, "C42"))

    async def async_select_option(self, option):
        await self.coordinator.async_set_hot_water_mode(option)
