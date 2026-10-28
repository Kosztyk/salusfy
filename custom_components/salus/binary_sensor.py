"""Relay and hot-water state entities discovered from SALUS cloud attributes."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .device import link_entity
from .entity import climate_entity_id, legacy_unique_id
from .model import flag, has_hot_water


async def async_setup_entry(hass, entry, async_add_entities):
    config = hass.data[DOMAIN][entry.entry_id]
    coordinator = config["coordinator"]
    entity_id = climate_entity_id(hass, config.get("name", DEFAULT_NAME))
    sensors = []
    if "A" in coordinator.zones and "A87" in coordinator.attributes:
        unique_id = legacy_unique_id(
            hass, entry, "binary_sensor", "_ch1_heat_on_off_status", f"{entity_id}_ch1_heat_on_off_status"
        )
        sensors.append(SalusCh1HeatOnOffBinarySensor(coordinator, unique_id))
    if "B" in coordinator.zones and "B87" in coordinator.attributes:
        sensors.append(SalusCh1HeatOnOffBinarySensor(coordinator, f"{coordinator.device_id}_ch2_heat_on_off_status", "B"))
    if has_hot_water(coordinator.attributes) and "C45" in coordinator.attributes:
        sensors.append(SalusHotWaterBinarySensor(coordinator))
    for zone in coordinator.zones:
        if f"{zone}90" in coordinator.attributes:
            sensors.append(SalusFrostProtectionBinarySensor(coordinator, zone))
    if "S03" in coordinator.attributes:
        sensors.append(SalusBatteryLowBinarySensor(coordinator))
    for entity in sensors:
        link_entity(entity, coordinator)
    async_add_entities(sensors)


class SalusCh1HeatOnOffBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Reported heating relay; no temperature-difference guessing."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator, unique_id, zone="A"):
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = "Heating output" if zone == "A" else "Zone 2 heating output"
        self._attr_unique_id = unique_id

    @property
    def available(self):
        state = self.coordinator.zone_state(self.zone)
        return super().available and state.online is not False and state.heating is not None

    @property
    def is_on(self):
        return self.coordinator.zone_state(self.zone).heating


class SalusHotWaterBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Read-only hot-water output (C45); mode controls use C42 separately."""

    _attr_has_entity_name = True
    _attr_name = "Hot water output"
    _attr_icon = "mdi:water-boiler"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_hot_water_output"

    @property
    def available(self):
        return (super().available and flag(self.coordinator.attributes, "online") is not False
                and flag(self.coordinator.attributes, "C45") is not None)

    @property
    def is_on(self):
        return flag(self.coordinator.attributes, "C45")


class SalusBatteryLowBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """S03=0 full/normal, 1 low, 2 very low per both mobile apps."""

    _attr_has_entity_name = True
    _attr_name = "Battery low"
    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_battery_low"

    @property
    def available(self):
        raw = self.coordinator.attributes.get("S03")
        return (super().available and flag(self.coordinator.attributes, "online") is not False
                and raw is not None and raw.value in ("0", "1", "2"))

    @property
    def is_on(self):
        raw = self.coordinator.attributes.get("S03")
        if raw is None or raw.value not in ("0", "1", "2"):
            return None
        return raw.value in ("1", "2")


class SalusFrostProtectionBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Zone A90/B90 reports the thermostat frost-protection state."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:snowflake-thermometer"

    def __init__(self, coordinator, zone="A"):
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = "Frost protection active" if zone == "A" else "Zone 2 frost protection active"
        self._attr_unique_id = f"{coordinator.device_id}_zone_{zone.lower()}_frost_protection"

    @property
    def available(self):
        return (super().available and flag(self.coordinator.attributes, "online") is not False
                and flag(self.coordinator.attributes, f"{self.zone}90") is not None)

    @property
    def is_on(self):
        return flag(self.coordinator.attributes, f"{self.zone}90")
