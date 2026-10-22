"""The existing Salus climate entity, backed by the iT500 mobile API."""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN, MAX_TEMP, MIN_TEMP, TEMP_STEP
from .coordinator import SalusCoordinator
from .model import Mode


async def async_setup_entry(hass, entry, async_add_entities):
    config = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SalusThermostat(config["coordinator"], config.get("name", DEFAULT_NAME))])


class SalusThermostat(CoordinatorEntity[SalusCoordinator], ClimateEntity):
    """Keep the original name-based unique ID and entity registry entry."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = TEMP_STEP
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_icon = "mdi:thermostat"

    def __init__(self, coordinator: SalusCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{name}_climate"

    @property
    def available(self):
        return super().available and self.coordinator.data is not None and self.coordinator.data.online is not False

    @property
    def current_temperature(self):
        return self.coordinator.data.current_temperature

    @property
    def target_temperature(self):
        return self.coordinator.data.target_temperature

    @property
    def hvac_mode(self):
        mode = self.coordinator.data.mode
        return HVACMode(mode.value) if mode is not None else None

    @property
    def hvac_action(self):
        state = self.coordinator.data
        if state.heating is None:
            return None
        if state.heating:
            return HVACAction.HEATING
        return HVACAction.OFF if state.mode == Mode.OFF else HVACAction.IDLE

    @property
    def extra_state_attributes(self):
        state = self.coordinator.data
        heating = state.heating
        return {
            "is_heating": heating,
            "ch1_heat_on_off_status_raw": None if heating is None else "1" if heating else "0",
            "temporary_hold": state.temporary_hold,
            "last_report_ms": state.last_report_ms,
            "state_source": "salus_mobile_api",
        }

    async def async_set_temperature(self, **kwargs):
        if (mode := kwargs.get("hvac_mode")) is not None:
            await self.async_set_hvac_mode(mode)
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.async_set_temperature(float(temperature))

    async def async_set_hvac_mode(self, hvac_mode):
        await self.coordinator.async_set_mode(Mode(hvac_mode))

    async def async_turn_on(self):
        await self.coordinator.async_set_mode(Mode.HEAT)

    async def async_turn_off(self):
        await self.coordinator.async_set_mode(Mode.OFF)
