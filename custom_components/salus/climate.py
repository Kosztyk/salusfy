"""Thermostat entities for every recognized SALUS heating zone."""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN, MAX_TEMP, MIN_TEMP, TEMP_STEP
from .device import link_entity
from .coordinator import SalusCoordinator
from .model import Mode, can_set_mode, can_set_temperature, value


async def async_setup_entry(hass, entry, async_add_entities):
    config = hass.data[DOMAIN][entry.entry_id]
    coordinator = config["coordinator"]
    name = config.get("name", DEFAULT_NAME)
    entities = [SalusThermostat(coordinator, name, zone) for zone in coordinator.zones]
    for entity in entities:
        link_entity(entity, coordinator)
    async_add_entities(entities)


class SalusThermostat(CoordinatorEntity[SalusCoordinator], ClimateEntity):
    """Zone 1 retains the exact legacy name/unique ID; zone 2 has its own ID."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = TEMP_STEP
    _attr_icon = "mdi:thermostat"

    def __init__(self, coordinator: SalusCoordinator, name: str, zone: str = "A") -> None:
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = None if zone == "A" else "Zone 2"
        self._attr_unique_id = f"{name}_climate" if zone == "A" else f"{name}_zone_2_climate"

    @property
    def available(self):
        state = self.coordinator.zone_state(self.zone)
        return super().available and self.coordinator.data is not None and state.online is not False and (
            state.current_temperature is not None or state.target_temperature is not None
        )

    @property
    def supported_features(self):
        flags = ClimateEntityFeature(0)
        if can_set_temperature(self.coordinator.attributes, self.zone):
            flags |= ClimateEntityFeature.TARGET_TEMPERATURE
        if can_set_mode(self.coordinator.attributes, self.zone):
            flags |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        return flags

    @property
    def hvac_modes(self):
        manual = HVACMode.COOL if value(self.coordinator.attributes, "S05") == "1" else HVACMode.HEAT
        if can_set_mode(self.coordinator.attributes, self.zone):
            return [manual, HVACMode.OFF, HVACMode.AUTO]
        # A read-only thermostat should not advertise unsupported modes.
        return [manual] if self.coordinator.zone_state(self.zone).mode != Mode.OFF else [HVACMode.OFF]

    @property
    def current_temperature(self):
        return self.coordinator.zone_state(self.zone).current_temperature

    @property
    def target_temperature(self):
        return self.coordinator.zone_state(self.zone).target_temperature

    @property
    def hvac_mode(self):
        mode = self.coordinator.zone_state(self.zone).mode
        if mode == Mode.HEAT and value(self.coordinator.attributes, "S05") == "1":
            return HVACMode.COOL
        return HVACMode(mode.value) if mode is not None else None

    @property
    def hvac_action(self):
        state = self.coordinator.zone_state(self.zone)
        if state.heating is None:
            return None
        if state.heating:
            return HVACAction.COOLING if value(self.coordinator.attributes, "S05") == "1" else HVACAction.HEATING
        return HVACAction.OFF if state.mode == Mode.OFF else HVACAction.IDLE

    @property
    def extra_state_attributes(self):
        state = self.coordinator.zone_state(self.zone)
        heating = state.heating
        attributes = {
            "is_heating": heating,
            "temporary_hold": state.temporary_hold,
            "manual_target_temperature": state.manual_target_temperature,
            "frost_protection": state.frost_protection,
            "last_report_ms": state.last_report_ms,
            "zone": self.zone,
            "state_source": "salus_mobile_api",
            "system_mode": {"0": "heating", "1": "cooling"}.get(value(self.coordinator.attributes, "S05")),
        }
        if self.zone == "A":
            attributes["ch1_heat_on_off_status_raw"] = None if heating is None else "1" if heating else "0"
        return attributes

    async def async_set_temperature(self, **kwargs):
        if (mode := kwargs.get("hvac_mode")) is not None:
            await self.async_set_hvac_mode(mode)
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.async_set_temperature(float(temperature), zone=self.zone)

    async def async_set_hvac_mode(self, hvac_mode):
        # The iT500 switches heating/cooling using S05 in Settings; mode controls
        # cannot silently switch this global system configuration.
        is_cooling = value(self.coordinator.attributes, "S05") == "1"
        if hvac_mode == HVACMode.COOL:
            if not is_cooling:
                raise HomeAssistantError("The SALUS gateway is not configured for cooling")
            requested = Mode.HEAT  # manual operation of the already-configured system
        elif hvac_mode == HVACMode.HEAT:
            if is_cooling:
                raise HomeAssistantError("The SALUS gateway is configured for cooling")
            requested = Mode.HEAT
        else:
            requested = Mode(hvac_mode)
        await self.coordinator.async_set_mode(requested, zone=self.zone)

    async def async_turn_on(self):
        await self.coordinator.async_set_mode(Mode.HEAT, zone=self.zone)

    async def async_turn_off(self):
        await self.coordinator.async_set_mode(Mode.OFF, zone=self.zone)
