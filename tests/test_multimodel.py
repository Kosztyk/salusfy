"""Regression cases based on RT310i Android 2.2.1 attribute definitions.

No claims of live hardware validation: the fixtures model its static contract.
"""

import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ha_stubs import HAError, interfaces
from support import load
from test_api import LOGIN, Response, Session

api = load("api")
model = load("model")
with interfaces():
    coordination = load("coordinator")
    climate = load("climate")
    binary = load("binary_sensor")
    sensor = load("sensor")
    flow = load("config_flow")


def attrs(**values):
    return {name: api.Attribute(str(value), 1234567) for name, value in values.items()}


RT310 = attrs(A84="2080", A85="2200", A87="1", A88="0", A89="0",
              A90="0", A92="1", A93="1950", online="1")
IT500_DUAL = {**RT310, **attrs(B84="2130", B85="2240", B87="0", B88="0",
                              B89="0", B92="0", C42="1", C45="1")}


class TestMultiModelProtocol(unittest.IsolatedAsyncioTestCase):
    async def test_rt310i_devices_are_not_filtered_by_numeric_type_id(self):
        devices = """<getDeviceListResponse>
        <devList><devId>99</devId><devName>SRT123456</devName><typeId>42</typeId></devList>
        <devList><devId>111</devId><devName>STA765432</devName><typeId>1</typeId></devList>
        <devList><devId>222</devId><devName>Other SALUS</devName><typeId>200</typeId></devList>
        </getDeviceListResponse>"""
        session = Session((200, LOGIN), (200, devices))
        client = api.SalusClient(session, "email", "password")
        discovered = await client.async_get_devices()
        self.assertEqual([d.type_id for d in discovered], ["42", "1", "200"])
        self.assertEqual(api.select_device(discovered, "srt123456").device_id, "99")
        self.assertEqual(api.select_device(discovered, "222").name, "Other SALUS")

    async def test_rt310i_attribute_request_carries_the_real_device_type(self):
        response = """<getDeviceAttributesWithValuesResponse><typeId>42</typeId><presenceInfo>1</presenceInfo>
        <attrList><name>A93</name><value>1950</value><updTime>123</updTime></attrList>
        </getDeviceAttributesWithValuesResponse>"""
        session = Session((200, LOGIN), (200, response))
        retrieved = await api.SalusClient(session, "u", "p").async_get_attributes("99", "42")
        self.assertEqual(session.calls[1][2]["data"]["deviceTypeId"], "42")
        self.assertEqual(session.calls[1][2]["data"]["devId"], "99")
        self.assertTrue(retrieved["online"].value == "1")
        self.assertEqual(retrieved["A93"].value, "1950")

    async def test_flow_accepts_an_rt310_device_type(self):
        entry_flow = flow.SalusConfigFlow()
        entry_flow.hass = object()
        target = api.DeviceInfo("99", "SRT123456", "42")
        with patch.object(flow, "_fetch_devices", new=AsyncMock(return_value=[target])):
            selected = await entry_flow.async_step_user({"username": "u", "password": "p"})
        self.assertEqual(selected["data"]["id"], "99")


class TestZoneCapability(unittest.TestCase):
    def test_rt310i_all_seven_attributes_and_manual_setpoint(self):
        state = model.decode(RT310)
        self.assertEqual(model.heating_zones(RT310), ("A",))
        self.assertEqual(state.current_temperature, 20.8)  # A84
        self.assertEqual(state.target_temperature, 22.0)   # A85
        self.assertTrue(state.heating)                      # A87
        self.assertFalse(state.temporary_hold)              # A88
        self.assertEqual(state.mode, model.Mode.HEAT)       # A89+A92
        self.assertEqual(state.manual_target_temperature, 19.5)  # A93
        self.assertFalse(state.frost_protection)            # A90
        self.assertTrue(model.can_set_mode(RT310))
        self.assertTrue(model.can_set_temperature(RT310))

    def test_a93_fallback_uses_manual_setpoint_only_in_manual_mode(self):
        a85_missing = {k: v for k, v in RT310.items() if k != "A85"}
        self.assertEqual(model.decode(a85_missing).target_temperature, 19.5)
        auto = {**a85_missing, "A92": api.Attribute("0", 10)}
        self.assertIsNone(model.decode(auto).target_temperature)

    def test_off_and_schedule_modes(self):
        off = {**RT310, "A89": api.Attribute("1", 10), "A92": api.Attribute("0", 10)}
        self.assertEqual(model.decode(off).mode, model.Mode.OFF)
        automatic = {**RT310, "A92": api.Attribute("0", 10), "A88": api.Attribute("1", 10)}
        self.assertEqual(model.decode(automatic).mode, model.Mode.AUTO)
        self.assertTrue(model.decode(automatic).temporary_hold)
        self.assertEqual(model.mode_writes(model.Mode.HEAT), [("A92", "1"), ("A88", "0"), ("A89", "0")])
        self.assertEqual(model.mode_writes(model.Mode.OFF), [("A92", "0"), ("A88", "0"), ("A89", "1")])

    def test_it500_multiple_zones_have_independent_readings_and_modes(self):
        self.assertEqual(model.heating_zones(IT500_DUAL), ("A", "B"))
        a, b = model.decode(IT500_DUAL, "A"), model.decode(IT500_DUAL, "B")
        self.assertEqual(a.target_temperature, 22)
        self.assertEqual(b.target_temperature, 22.4)
        self.assertEqual(b.current_temperature, 21.3)
        self.assertFalse(b.heating)
        self.assertEqual(b.mode, model.Mode.AUTO)
        self.assertEqual(model.mode_writes(model.Mode.OFF, "B"), [("B92", "0"), ("B88", "0"), ("B89", "1")])

    def test_other_models_do_not_get_thermostat_controls(self):
        unknown = attrs(Humidity=65, Alarm=0, online=1)
        self.assertEqual(model.heating_zones(unknown), ())
        self.assertFalse(model.can_set_temperature(unknown))
        self.assertFalse(model.can_set_mode(unknown))
        self.assertIsNone(model.decode(unknown).current_temperature)


class TestMultiModelCoordinator(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.readings = dict(RT310)
        self.client = SimpleNamespace(async_get_attributes=AsyncMock(return_value=self.readings),
                                      async_set_attribute=AsyncMock())
        self.entry = SimpleNamespace(async_start_reauth=Mock())
        self.coordinator = coordination.SalusCoordinator(object(), self.entry, self.client, "99", "42")
        await self.coordinator.async_config_entry_first_refresh()

    async def test_rt310i_type_is_preserved_during_polls(self):
        self.client.async_get_attributes.assert_awaited_with("99", "42")
        self.assertEqual(self.coordinator.zones, ("A",))

    async def test_rt310i_supports_documented_35_c_setpoint(self):
        now = int(time.time() * 1000)
        self.client.async_get_attributes.return_value = {
            **RT310, "A85": api.Attribute("3500", now)
        }
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.coordinator.async_set_temperature(35.0)
        self.assertEqual(self.coordinator.zone_state().target_temperature, 35)

    async def test_manual_temperature_writes_a85_not_a93(self):
        new_time = int(time.time() * 1000)
        self.client.async_get_attributes.return_value = {
            **RT310, "A85": api.Attribute("2150", new_time)
        }
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.coordinator.async_set_temperature(21.5)
        commands = [c.args[1:] for c in self.client.async_set_attribute.await_args_list]
        self.assertEqual(commands, [("F", "1"), ("A85", "2150")])
        self.assertEqual(self.coordinator.zone_state().manual_target_temperature, 19.5)

    async def test_schedule_temperature_change_sets_override_attribute(self):
        self.readings = {**RT310, "A92": api.Attribute("0", 10)}
        self.client.async_get_attributes.return_value = self.readings
        await self.coordinator.async_config_entry_first_refresh()
        now = int(time.time() * 1000)
        self.client.async_get_attributes.return_value = {
            **self.readings, "A85": api.Attribute("2100", now), "A88": api.Attribute("1", now)
        }
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.coordinator.async_set_temperature(21)
        writes = [c.args[1:] for c in self.client.async_set_attribute.await_args_list]
        self.assertIn(("A85", "2100"), writes)
        self.assertIn(("A88", "1"), writes)

    async def test_unknown_model_loads_readonly_and_refuses_commands(self):
        self.client.async_get_attributes.return_value = attrs(Alarm="ok", online="1")
        await self.coordinator.async_config_entry_first_refresh()
        self.assertEqual(self.coordinator.zones, ())
        with self.assertRaises(HAError):
            await self.coordinator.async_set_temperature(20)
        with self.assertRaises(HAError):
            await self.coordinator.async_set_mode(model.Mode.HEAT)
        self.client.async_set_attribute.assert_not_awaited()
        status = sensor.SalusDeviceStatusSensor(self.coordinator, api.DeviceInfo("99", "Other SALUS", "42"))
        self.assertEqual(status.native_value, "online")
        self.assertEqual(status.extra_state_attributes["heating_zones"], [])
        self.assertEqual(status.extra_state_attributes["device_type_id"], "42")

    async def test_it500_zone_two_commands_are_targeted_at_b_prefix(self):
        self.client.async_get_attributes.return_value = IT500_DUAL
        await self.coordinator.async_config_entry_first_refresh()
        now = int(time.time() * 1000)
        self.client.async_get_attributes.return_value = {
            **IT500_DUAL, "B89": api.Attribute("1", now)
        }
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.coordinator.async_set_mode(model.Mode.OFF, zone="B")
        self.assertEqual(self.client.async_set_attribute.await_args_list[-1].args, ("99", "B89", "1"))
        self.assertEqual(self.coordinator.zone_state("B").mode, model.Mode.OFF)

    async def test_extra_zone_entities_have_unique_ids(self):
        self.client.async_get_attributes.return_value = IT500_DUAL
        await self.coordinator.async_config_entry_first_refresh()
        a = climate.SalusThermostat(self.coordinator, "Salus Thermostat")
        b = climate.SalusThermostat(self.coordinator, "Salus Thermostat", "B")
        self.assertEqual(a._attr_unique_id, "Salus Thermostat_climate")
        self.assertNotEqual(b._attr_unique_id, a._attr_unique_id)
        self.assertTrue(binary.SalusHotWaterBinarySensor(self.coordinator).is_on)
        self.assertEqual(sensor.SalusManualSetpointSensor(self.coordinator).native_value, 19.5)
