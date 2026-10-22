import logging
import datetime
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import (
    STATE_UNAVAILABLE, 
    STATE_UNKNOWN
)

from . import DOMAIN

# Decrease poll interval to 15 seconds:
SCAN_INTERVAL = timedelta(seconds=15)



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """
    Set up the sensor entities for the Salus integration from a config entry.
    This replicates the behavior of your YAML-based 'history_stats' & template sensors.
    """
    # We assume your climate entity is called climate.salus_thermostat
    climate_entity_id = "climate.salus_thermostat"

    sensors = [
        StareTermostatSensor(climate_entity_id),
        StatisticaCentralaSensor(climate_entity_id),
        StatisticaCentralaIeriSensor(climate_entity_id),
        StatisticaCentralaLunaCurentaSensor(climate_entity_id),
        StatisticaCentralaLunaTrecutaSensor(climate_entity_id),
        DurataIncalzireSensor("sensor.thermostat_state"),  # references the sensor above
        SalusCurrentTempSensor(climate_entity_id)          # <-- Your new temperature sensor
    ]
    async_add_entities(sensors, update_before_add=True)


class StareTermostatSensor(SensorEntity):
    """
    Replaces:
      template:
        - sensor:
            - name: "stare termostat"
              state: "{{ state_attr('climate.salus_thermostat','hvac_action') }}"
    """
    def __init__(self, climate_entity_id):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Thermostat State"
        self._attr_unique_id = f"{climate_entity_id}_thermostat_state"
        self._state = STATE_UNKNOWN

    @property
    def state(self):
        return self._state

    def update(self):
        climate_state = self.hass.states.get(self._climate_entity_id)
        if not climate_state:
            self._state = STATE_UNAVAILABLE
            return
        # mirror hvac_action
        self._state = climate_state.attributes.get("hvac_action", STATE_UNKNOWN)


class StatisticaCentralaSensor(SensorEntity, RestoreEntity):
    """
    Replaces:
      - platform: history_stats
        name: 'StatisticaCentrala'
        entity_id: climate.salus_thermostat
        state: "heating"
        type: time
        start: midnight
        end: now

    Accumulates heating time in memory from midnight to current.
    Resets daily at midnight. Loses info on HA restart.
    """
    def __init__(self, climate_entity_id):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Heater History"
        self._attr_unique_id = f"{climate_entity_id}_.heater_history"
        self._hours_heating = 0.0
        self._last_update = datetime.datetime.now()
        self._last_state = STATE_UNKNOWN

    async def async_added_to_hass(self):
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._hours_heating = float(last_state.state)
            attributes = last_state.attributes
            if "last_update" in attributes:
                self._last_update = datetime.datetime.fromisoformat(attributes["last_update"])
            if "last_state" in attributes:
                self._last_state = attributes["last_state"]

    @property
    def state(self):
        return round(self._hours_heating, 2)

    @property
    def extra_state_attributes(self):
        return {
            "last_update": self._last_update.isoformat(),
            "last_state": self._last_state,
        }

    def update(self):
        now = datetime.datetime.now()
        climate_state = self.hass.states.get(self._climate_entity_id)
        if climate_state:
            hvac_action = climate_state.attributes.get("hvac_action", STATE_UNKNOWN)
        else:
            hvac_action = STATE_UNAVAILABLE

        # reset if day changed
        if now.date() != self._last_update.date():
            self._hours_heating = 0.0

        # accumulate if last state was "heating"
        time_diff = (now - self._last_update).total_seconds() / 3600.0
        if self._last_state == "heating":
            self._hours_heating += time_diff

        self._last_state = hvac_action
        self._last_update = now


class StatisticaCentralaIeriSensor(SensorEntity, RestoreEntity):
    """
    Tracks yesterday's heating time.
    Resets at midnight, storing the previous day's total.
    """
    def __init__(self, climate_entity_id):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Yesterday Heater History"
        self._attr_unique_id = f"{climate_entity_id}_yesterday_heater_history"
        self._state = 0.0  # yesterday's total
        self._today_heating = 0.0
        self._last_update = datetime.datetime.now()
        self._last_state = STATE_UNKNOWN

    async def async_added_to_hass(self):
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = float(last_state.state)
            attributes = last_state.attributes
            if "today_heating" in attributes:
                self._today_heating = float(attributes["today_heating"])
            if "last_update" in attributes:
                self._last_update = datetime.datetime.fromisoformat(attributes["last_update"])
            if "last_state" in attributes:
                self._last_state = attributes["last_state"]

    @property
    def state(self):
        return round(self._state, 2)

    @property
    def extra_state_attributes(self):
        return {
            "today_heating": round(self._today_heating, 2),
            "last_update": self._last_update.isoformat(),
            "last_state": self._last_state,
        }

    def update(self):
        now = datetime.datetime.now()
        climate_state = self.hass.states.get(self._climate_entity_id)
        hvac_action = STATE_UNKNOWN
        if climate_state:
            hvac_action = climate_state.attributes.get("hvac_action", STATE_UNKNOWN)

        time_diff = (now - self._last_update).total_seconds() / 3600.0
        if self._last_state == "heating":
            self._today_heating += time_diff

        # if new day => move today's total to "yesterday"
        if now.date() != self._last_update.date():
            self._state = self._today_heating
            self._today_heating = 0.0

        self._last_state = hvac_action
        self._last_update = now


class StatisticaCentralaLunaCurentaSensor(SensorEntity, RestoreEntity):
    """
    Tracks heating time for the current month.
    Resets at the start of each month.
    """
    def __init__(self, climate_entity_id):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "This Month Heater History"
        self._attr_unique_id = f"{climate_entity_id}_this_month_heater_history"
        self._state = 0.0  # This month's total heating hours
        self._monthly_heating = 0.0
        self._last_update = datetime.datetime.now()
        self._last_state = STATE_UNKNOWN

    async def async_added_to_hass(self):
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            # restore to _monthly_heating
            self._monthly_heating = float(last_state.state)
            attributes = last_state.attributes
            if "last_update" in attributes:
                self._last_update = datetime.datetime.fromisoformat(attributes["last_update"])
            if "last_state" in attributes:
                self._last_state = attributes["last_state"]

        # initialize _state to _monthly_heating on restore
        self._state = self._monthly_heating

    @property
    def state(self):
        return round(self._monthly_heating, 2)  # display _monthly_heating as state

    @property
    def extra_state_attributes(self):
        return {
            "last_update": self._last_update.isoformat(),
            "last_state": self._last_state,
        }

    def update(self):
        now = datetime.datetime.now()
        climate_state = self.hass.states.get(self._climate_entity_id)
        hvac_action = STATE_UNKNOWN
        if climate_state:
            hvac_action = climate_state.attributes.get("hvac_action", STATE_UNKNOWN)

        time_diff = (now - self._last_update).total_seconds() / 3600.0
        if self._last_state == "heating":
            self._monthly_heating += time_diff

        # if new month => reset this month's heating
        if now.month != self._last_update.month:
            self._monthly_heating = 0.0

        self._last_state = hvac_action
        self._last_update = now


class StatisticaCentralaLunaTrecutaSensor(SensorEntity, RestoreEntity):
    """
    Tracks heating time for the last month.
    Updates at the start of each month.
    """
    def __init__(self, climate_entity_id):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Last Month Heater History"
        self._attr_unique_id = f"{climate_entity_id}_last_month_heater_history"
        self._state = 0.0  # Last month's total heating hours
        self._this_month_heating = 0.0
        self._last_update = datetime.datetime.now()
        self._last_state = STATE_UNKNOWN

    async def async_added_to_hass(self):
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = float(last_state.state)  # restore last month's history
            attributes = last_state.attributes
            if "this_month_heating" in attributes:
                self._this_month_heating = float(attributes["this_month_heating"])
            if "last_update" in attributes:
                self._last_update = datetime.datetime.fromisoformat(attributes["last_update"])
            if "last_state" in attributes:
                self._last_state = attributes["last_state"]

    @property
    def state(self):
        return round(self._state, 2)  # display last month's history

    @property
    def extra_state_attributes(self):
        return {
            "this_month_heating": round(self._this_month_heating, 2),
            "last_update": self._last_update.isoformat(),
            "last_state": self._last_state,
        }

    def update(self):
        now = datetime.datetime.now()
        climate_state = self.hass.states.get(self._climate_entity_id)
        hvac_action = STATE_UNKNOWN
        if climate_state:
            hvac_action = climate_state.attributes.get("hvac_action", STATE_UNKNOWN)

        time_diff = (now - self._last_update).total_seconds() / 3600.0
        if self._last_state == "heating":
            self._this_month_heating += time_diff

        # if new month => move this month's total to "last month"
        if now.month != self._last_update.month:
            self._state = self._this_month_heating  # current month becomes last month
            self._this_month_heating = 0.0          # reset current month counter

        self._last_state = hvac_action
        self._last_update = now


class DurataIncalzireSensor(SensorEntity):
    """
    Replaces:
      - platform: history_stats
        name: 'durata incalzire'
        entity_id: sensor.stare_termostat
        state: "heating"
        type: time
        start: midnight
        end: now

    We look at sensor.stare_termostat to see if it's "heating".
    """
    def __init__(self, stare_termostat_entity_id):
        self._stare_termostat_entity_id = stare_termostat_entity_id
        self._attr_name = "Heating Time"
        self._attr_unique_id = f"{stare_termostat_entity_id}_heating_time"
        self._hours_heating = 0.0
        self._last_update = datetime.datetime.now()
        self._last_state = STATE_UNKNOWN

    @property
    def state(self):
        return round(self._hours_heating, 2)

    def update(self):
        now = datetime.datetime.now()
        stare_state = self.hass.states.get(self._stare_termostat_entity_id)
        if stare_state:
            hvac_action = stare_state.state  # i.e. "heating" or "idle"
        else:
            hvac_action = STATE_UNKNOWN

        # Reset if new day
        if now.date() != self._last_update.date():
            self._hours_heating = 0.0

        # If last state was "heating," accumulate
        time_diff = (now - self._last_update).total_seconds() / 3600.0
        if self._last_state == "heating":
            self._hours_heating += time_diff

        self._last_state = hvac_action
        self._last_update = now


# --------------------------------------------------------------------------
# Below is the NEW sensor for Current Temperature from your Salus climate.
# --------------------------------------------------------------------------
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
)

class SalusCurrentTempSensor(SensorEntity):
    """Sensor to expose the current temperature from the Salus climate entity."""

    def __init__(self, climate_entity_id: str):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Salus Current Temperature"
        self._attr_unique_id = f"{climate_entity_id}_current_temperature"
        # Provide device_class & state_class for improved UI
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._state = STATE_UNKNOWN

    @property
    def native_value(self):
        """Return the current temperature as a float or Unknown/Unavailable."""
        return self._state

    def update(self):
        """Fetch the current temperature from the Salus climate entity."""
        climate_state = self.hass.states.get(self._climate_entity_id)
        if not climate_state:
            self._state = STATE_UNAVAILABLE
            return

        # The climate entity's 'current_temperature' attribute is the key
        temperature = climate_state.attributes.get("current_temperature", STATE_UNKNOWN)
        self._state = temperature
