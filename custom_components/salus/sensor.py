"""Capability-based, device-grouped SALUS cloud sensors.

Battery codes and heating/hot-water codes are taken from both supplied
Android v2.2.1 APKs. In particular, S03 is a *status*, never a battery %.
Heating-duration entities are estimates based on successful A87 relay polls.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
import math
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DEFAULT_NAME, DOMAIN
from .device import link_entity
from .entity import climate_entity_id, legacy_unique_id
from .model import HOT_WATER_MODES, Mode, has_hot_water, value


async def async_setup_entry(hass, entry, async_add_entities):
    config = hass.data[DOMAIN][entry.entry_id]
    coordinator = config["coordinator"]
    climate_id = climate_entity_id(hass, config.get("name", DEFAULT_NAME))
    entities: list = []
    if "A" in coordinator.zones:
        entities.extend([
            SalusThermostatState(coordinator, legacy_unique_id(
                hass, entry, "sensor", "_thermostat_state", f"{climate_id}_thermostat_state")),
            SalusCurrentTempSensor(coordinator, legacy_unique_id(
                hass, entry, "sensor", "_current_temperature", f"{climate_id}_current_temperature")),
        ])
        history = [
            ("today", "Heater History", "_.heater_history", f"{climate_id}_.heater_history"),
            ("yesterday", "Yesterday Heater History", "_yesterday_heater_history", f"{climate_id}_yesterday_heater_history"),
            ("month", "This Month Heater History", "_this_month_heater_history", f"{climate_id}_this_month_heater_history"),
            ("previous_month", "Last Month Heater History", "_last_month_heater_history", f"{climate_id}_last_month_heater_history"),
            ("heating_time", "Heating Time", "_heating_time", "sensor.thermostat_state_heating_time"),
        ]
        for kind, name, suffix, fallback in history:
            entities.append(SalusRuntimeSensor(coordinator, kind, name, legacy_unique_id(
                hass, entry, "sensor", suffix, fallback)))

    for zone in coordinator.zones:
        if zone == "B" and f"{zone}84" in coordinator.attributes:
            entities.append(SalusCurrentTempSensor(
                coordinator, f"{coordinator.device_id}_zone_2_current_temperature", zone))
        if f"{zone}85" in coordinator.attributes:
            entities.append(SalusTargetTempSensor(coordinator, zone))
        if f"{zone}93" in coordinator.attributes:
            entities.append(SalusManualSetpointSensor(coordinator, zone))
        if f"{zone}88" in coordinator.attributes:
            entities.append(SalusOperatingModeSensor(coordinator, zone))

    if has_hot_water(coordinator.attributes) and "C42" in coordinator.attributes:
        entities.append(SalusHotWaterModeSensor(coordinator))
    if "S03" in coordinator.attributes:
        entities.append(SalusBatteryStatusSensor(coordinator))
    if "rfrssi" in coordinator.attributes:
        entities.append(SalusRFRawSensor(coordinator))
    entities.append(SalusDeviceStatusSensor(coordinator, config.get("device")))
    for entity in entities:
        link_entity(entity, coordinator)
    async_add_entities(entities)


class SalusSensor(CoordinatorEntity, SensorEntity):
    """Shared availability rule for explicitly reported cloud data."""

    _attr_has_entity_name = True

    @property
    def available(self):
        device_offline = (getattr(getattr(self.coordinator, "data", None), "online", None) is False)
        return (super().available and not device_offline
                and value(self.coordinator.attributes, "online") != "0"
                and self.native_value is not None)


class SalusCurrentTempSensor(SalusSensor):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, unique_id: str, zone: str = "A") -> None:
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = "Current temperature" if zone == "A" else "Zone 2 current temperature"
        self._attr_unique_id = unique_id

    @property
    def native_value(self):
        return self.coordinator.zone_state(self.zone).current_temperature


class SalusTargetTempSensor(SalusSensor):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, zone="A") -> None:
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = "Target temperature" if zone == "A" else "Zone 2 target temperature"
        self._attr_unique_id = f"{coordinator.device_id}_zone_{zone.lower()}_target_temperature"

    @property
    def native_value(self):
        return self.coordinator.zone_state(self.zone).target_temperature


class SalusManualSetpointSensor(SalusSensor):
    _attr_name = "Saved manual temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, zone="A") -> None:
        super().__init__(coordinator)
        self.zone = zone
        if zone == "B":
            self._attr_name = "Zone 2 saved manual temperature"
        self._attr_unique_id = (f"{coordinator.device_id}_saved_manual_temperature" if zone == "A"
                                else f"{coordinator.device_id}_zone_2_saved_manual_temperature")

    @property
    def native_value(self):
        return self.coordinator.zone_state(self.zone).manual_target_temperature


class SalusThermostatState(SalusSensor):
    """Legacy thermostat-state entity now reads the actual zone relay."""

    _attr_name = "Thermostat state"
    _attr_icon = "mdi:thermostat"

    def __init__(self, coordinator, unique_id):
        super().__init__(coordinator)
        self._attr_unique_id = unique_id

    @property
    def native_value(self):
        state = self.coordinator.zone_state()
        if state.heating is None:
            return None
        if state.heating:
            return "cooling" if value(self.coordinator.attributes, "S05") == "1" else "heating"
        return "off" if state.mode == Mode.OFF else "idle"


class SalusOperatingModeSensor(SalusSensor):
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, zone="A"):
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = "Operating mode" if zone == "A" else "Zone 2 operating mode"
        self._attr_unique_id = f"{coordinator.device_id}_zone_{zone.lower()}_operating_mode"

    @property
    def native_value(self):
        state = self.coordinator.zone_state(self.zone)
        if state.mode is None:
            return None
        if state.mode == Mode.AUTO and state.temporary_hold:
            return "Temporary override"
        if state.mode == Mode.HEAT and value(self.coordinator.attributes, "S05") == "1":
            return "Manual (cooling)"
        return {Mode.OFF: "Off", Mode.HEAT: "Manual", Mode.AUTO: "Schedule"}[state.mode]


class SalusRuntimeSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """Estimated heating duration from sampled relay, not guessed from setpoint."""

    _attr_has_entity_name = True

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, kind, name, unique_id):
        super().__init__(coordinator)
        self.kind = kind
        self._attr_name = name
        self._attr_unique_id = unique_id

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        # One authoritative snapshot prevents five sensors counting separately.
        if self.kind == "today":
            previous = await self.async_get_last_state()
            if previous is not None:
                self.coordinator.runtime.restore(dict(previous.attributes), dt_util.now())

    @property
    def native_value(self):
        return self.coordinator.runtime.read_hours(self.kind)

    @property
    def available(self):
        return super().available and "A" in self.coordinator.zones

    @property
    def extra_state_attributes(self):
        if self.kind == "today":
            return self.coordinator.runtime.snapshot()
        return {"calculation": "sampled heating relay; not a metered energy value"}


class SalusBatteryStatusSensor(SalusSensor):
    """iT500+/RT310i APK DeviceDetail.getBatteryLevelResId maps S03 0/1/2."""

    _attr_name = "Battery status"
    _attr_icon = "mdi:battery"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_battery_status"

    @property
    def native_value(self):
        return {"0": "Normal", "1": "Low", "2": "Very low"}.get(value(self.coordinator.attributes, "S03"))


class SalusRFRawSensor(SalusSensor):
    """Show RF signal as the raw app-reported value, without inventing a dBm scale."""

    _attr_name = "RF signal (raw)"
    _attr_icon = "mdi:signal"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_rf_signal_raw"

    @property
    def native_value(self):
        return value(self.coordinator.attributes, "rfrssi")


class SalusHotWaterModeSensor(SalusSensor):
    _attr_name = "Hot water mode"
    _attr_icon = "mdi:water-boiler"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_hot_water_mode"

    @property
    def native_value(self):
        return HOT_WATER_MODES.get(value(self.coordinator.attributes, "C42"))


class SalusDeviceStatusSensor(CoordinatorEntity, SensorEntity):
    """Keep unsupported SALUS models visible as a device with diagnostics."""

    _attr_has_entity_name = True

    _attr_name = "Cloud status"
    _attr_icon = "mdi:cloud-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device=None):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_cloud_status"
        self.device = device

    @property
    def native_value(self):
        raw = value(self.coordinator.attributes, "online")
        return {"0": "offline", "1": "online"}.get(raw, "presence unknown")

    @property
    def extra_state_attributes(self):
        return {
            "device_id": self.coordinator.device_id,
            "device_type_id": self.coordinator.device_type_id,
            "heating_zones": list(self.coordinator.zones),
            "hot_water_detected": has_hot_water(self.coordinator.attributes),
            "attribute_count": len(self.coordinator.attributes),
            "available_attribute_names": sorted(self.coordinator.attributes),
        }


def _restore_float(value):
    """Legacy compatibility helper; old history totals are not restored as facts."""
    try:
        numeric = float(value)
        return numeric if math.isfinite(numeric) else 0.0
    except (TypeError, ValueError):
        return 0.0
