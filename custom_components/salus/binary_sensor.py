"""Heating output directly from the SALUS relay attribute."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .entity import climate_entity_id, legacy_unique_id


async def async_setup_entry(hass, entry, async_add_entities):
    config = hass.data[DOMAIN][entry.entry_id]
    entity_id = climate_entity_id(hass, config.get("name", DEFAULT_NAME))
    unique_id = legacy_unique_id(
        hass, entry, "binary_sensor", "_ch1_heat_on_off_status", f"{entity_id}_ch1_heat_on_off_status"
    )
    async_add_entities([SalusCh1HeatOnOffBinarySensor(config["coordinator"], unique_id)])


class SalusCh1HeatOnOffBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Expose the actual relay, including unavailable when the flag is missing."""

    _attr_name = "Salus Heating Output"
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator, unique_id):
        super().__init__(coordinator)
        self._attr_unique_id = unique_id

    @property
    def available(self):
        state = self.coordinator.data
        return super().available and state is not None and state.online is not False and state.heating is not None

    @property
    def is_on(self):
        return self.coordinator.data.heating
