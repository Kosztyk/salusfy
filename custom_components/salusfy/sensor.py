import logging
import datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from . import DOMAIN
from datetime import timedelta

# Decrease poll interval to 15 seconds:
SCAN_INTERVAL = timedelta(seconds=15)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """
    Set up the sensor entities for the Salus integration from a config entry.
    This replicates the behavior of your YAML-based 'history_stats' & template sensors.
    """
    # We assume your climate is climate.salus_thermostat
    # and your "stare termostat" sensor is sensor.stare_termostat
    climate_entity_id = "climate.salus_thermostat"

    sensors = [
        StareTermostatSensor(climate_entity_id),
        StatisticaCentralaSensor(climate_entity_id),
        StatisticaCentralaIeriSensor(climate_entity_id),
        DurataIncalzireSensor("sensor.thermostat_state"),  # references the sensor above
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


class StatisticaCentralaSensor(SensorEntity):
    """
    Replaces:
      - platform: history_stats
        name: 'StatisticaCentrala'
        entity_id: climate.salus_thermostat
        state: "heating"
        type: time
        start: midnight
        end: now
    This just accumulates heating time in memory from midnight to current.
    Resets daily at midnight. Loses info on HA restart.
    """
    def __init__(self, climate_entity_id):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Heater History"
        self._attr_unique_id = f"{climate_entity_id}_.heater_history"
        self._hours_heating = 0.0
        self._last_update = datetime.datetime.now()
        self._last_state = STATE_UNKNOWN

    @property
    def state(self):
        return round(self._hours_heating, 2)

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


class StatisticaCentralaIeriSensor(SensorEntity):
    """
    Replaces:
      - platform: history_stats
        name: 'StatisticaCentralaIeri'
        entity_id: climate.salus_thermostat
        state: "heating"
        type: time
        start: now
        end: midnight
    But more accurately, it tries to store how much it heated *yesterday*.
    Resets at midnight, storing the *previous day's total*.

    This is a simplistic approach:
     - We'll track "today's" heating. At midnight, we set self._state = today's total,
       then reset today's to 0 for the new day.
    """
    def __init__(self, climate_entity_id):
        self._climate_entity_id = climate_entity_id
        self._attr_name = "Yesterday Heater History"
        self._attr_unique_id = f"{climate_entity_id}_yesterday_heater_history"
        self._state = 0.0  # yesterday's total
        self._today_heating = 0.0
        self._last_update = datetime.datetime.now()
        self._last_state = STATE_UNKNOWN

    @property
    def state(self):
        return round(self._state, 2)

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

    We look at the sensor.stare_termostat to see if it's "heating".
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