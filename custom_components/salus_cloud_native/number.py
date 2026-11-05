"""iT500-compatible hot-water boost control, discovered from cloud capabilities."""

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device import link_entity
from .model import value, flag, has_hot_water


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if has_hot_water(coordinator.attributes) and "C43" in coordinator.attributes:
        entity = SalusHotWaterBoostNumber(coordinator)
        link_entity(entity, coordinator)
        async_add_entities([entity])


class SalusHotWaterBoostNumber(CoordinatorEntity, NumberEntity):
    """iT500 Plus C43: 0=Off, 1-3 hours (may count down while active)."""

    _attr_has_entity_name = True
    _attr_name = "Hot water boost"
    _attr_icon = "mdi:timer-plus"
    _attr_native_min_value = 0
    _attr_native_max_value = 3
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_hot_water_boost_hours"

    @property
    def available(self):
        return (super().available and flag(self.coordinator.attributes, "online") is not False
                and self.native_value is not None)

    @property
    def native_value(self):
        raw = value(self.coordinator.attributes, "C43")
        return int(raw) if raw in ("0", "1", "2", "3") else None

    async def async_set_native_value(self, value):
        # Do not silently round invalid fractional inputs to other commands.
        if not 0 <= value <= 3 or not float(value).is_integer():
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError("Hot water boost must be 0, 1, 2, or 3 hours")
        await self.coordinator.async_set_hot_water_boost(int(value))
