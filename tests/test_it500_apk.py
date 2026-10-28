"""Regression contract from iT500 Plus v2.2.1 APK and RT310i v2.2.1 APK.

Verified by inspecting Zone1Atr, Zone2Atr, HotWaterAtr, DevAtr, Constants,
HeatZone.getDeviceRunningMode, HeatingActivity.sendF, and HotWaterActivity
write routines. Tests are deterministic offline simulations, not device tests.
"""

import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from ha_stubs import HAError, HVACAction, HVACMode, interfaces
from support import load

api = load("api")
model = load("model")
with interfaces():
    coordination = load("coordinator")
    climate = load("climate")
    hot_water_select = load("select")
    hot_water_number = load("number")


def attrs(**data):
    return {key: api.Attribute(str(v), 10) for key, v in data.items()}


I500_SINGLE = attrs(S06="0", S05="0", A84="2100", A85="2200", A87="0",
                    A88="0", A89="0", A92="1", A93="2100", online="1")
I500_DUAL = {**I500_SINGLE, **attrs(S06="1", B84="2000", B85="2300", B87="1",
                                  B88="0", B89="0", B92="0", B93="2050")}
I500_WATER = {**I500_SINGLE, **attrs(S06="2", C42="0", C43="0", C45="0", C46="0")}


class TestAndroidAttributeContract(unittest.TestCase):
    def test_system_configuration_changes_exposed_zones(self):
        self.assertEqual(model.heating_zones(I500_SINGLE), ("A",))
        self.assertEqual(model.heating_zones(I500_DUAL), ("A", "B"))
        # Stale B measurements must not turn iT500 CH1+hot-water into dual-zone.
        self.assertEqual(model.heating_zones({**I500_WATER, **attrs(B84="2300", B85="2400")}), ("A",))
        self.assertTrue(model.has_hot_water(I500_WATER))
        self.assertFalse(model.has_hot_water({**I500_DUAL, **attrs(C42="2")}))

    def test_c42_values_match_it500_constants(self):
        self.assertEqual(model.HOT_WATER_MODES, {
            "0": "Schedule", "1": "Once", "2": "On", "3": "Off"
        })

    def test_i500_reading_sentinels_are_not_temperatures(self):
        for code in ("5000", "7000", "8000"):
            with self.subTest(code=code):
                state = model.decode({**I500_SINGLE, **attrs(A84=code)})
                self.assertIsNone(state.current_temperature)
        self.assertEqual(model.decode(I500_SINGLE).current_temperature, 21.0)

    def test_manual_mode_precedes_conflicting_running_option(self):
        state = model.decode({**I500_SINGLE, **attrs(A89="1", A92="1")})
        self.assertEqual(state.mode, model.Mode.HEAT)
        self.assertFalse(state.temporary_hold)
        state = model.decode({**I500_SINGLE, **attrs(A89="1", A92="0")})
        self.assertEqual(state.mode, model.Mode.OFF)

    def test_schedule_override_is_not_off_or_manual(self):
        state = model.decode({**I500_SINGLE, **attrs(A88="1", A89="0", A92="0")})
        self.assertEqual(state.mode, model.Mode.AUTO)
        self.assertTrue(state.temporary_hold)

    def test_off_resets_manual_flag_for_both_zones(self):
        self.assertEqual(model.mode_writes(model.Mode.OFF, "A"),
                         [("A92", "0"), ("A88", "0"), ("A89", "1")])
        self.assertEqual(model.mode_writes(model.Mode.OFF, "B"),
                         [("B92", "0"), ("B88", "0"), ("B89", "1")])

    def test_unverified_a85_only_does_not_enable_writes(self):
        self.assertFalse(model.can_set_temperature(attrs(A84="2100", A85="2200")))


class TestIT500Entities(unittest.TestCase):
    def setUp(self):
        self.coordinator = SimpleNamespace(
            attributes=dict(I500_WATER), device_id="123", zones=("A",),
            last_update_success=True, data=model.decode(I500_WATER),
            async_set_hot_water_mode=AsyncMock(), async_set_hot_water_boost=AsyncMock(),
        )
        self.coordinator.zone_state = lambda zone="A": model.decode(self.coordinator.attributes, zone)

    def test_hot_water_select_and_boost(self):
        selector = hot_water_select.SalusHotWaterModeSelect(self.coordinator)
        boost = hot_water_number.SalusHotWaterBoostNumber(self.coordinator)
        self.assertTrue(selector.available)
        self.assertEqual(selector.current_option, "Schedule")
        self.assertEqual(boost.native_value, 0)
        self.assertTrue(boost.available)
        self.coordinator.attributes["C42"] = api.Attribute("3", 10)
        self.coordinator.attributes["C43"] = api.Attribute("2", 10)
        self.assertEqual(selector.current_option, "Off")
        self.assertEqual(boost.native_value, 2)

    def test_i500_cooling_system_status_without_undocumented_s05_write(self):
        self.coordinator.attributes["S05"] = api.Attribute("1", 10)
        self.coordinator.attributes["A87"] = api.Attribute("1", 10)
        thermostat = climate.SalusThermostat(self.coordinator, "Salus")
        self.assertEqual(thermostat.hvac_mode, HVACMode.COOL)
        self.assertEqual(thermostat.hvac_action, HVACAction.COOLING)
        self.assertIn(HVACMode.COOL, thermostat.hvac_modes)
        self.assertNotIn(HVACMode.HEAT, thermostat.hvac_modes)


class TestIT500CloudCommands(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.attr = dict(I500_WATER)
        self.client = SimpleNamespace(async_get_attributes=AsyncMock(return_value=self.attr),
                                      async_set_attribute=AsyncMock())
        self.entry = SimpleNamespace(async_start_reauth=Mock())
        self.c = coordination.SalusCoordinator(object(), self.entry, self.client, "123", "1")
        await self.c.async_config_entry_first_refresh()

    async def test_correct_f_refresh_before_setpoint(self):
        now = int(time.time()*1000)
        self.client.async_get_attributes.return_value = {**self.attr, "A85": api.Attribute("2300", now)}
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.c.async_set_temperature(23)
        self.assertEqual([x.args for x in self.client.async_set_attribute.await_args_list],
                         [("123", "F", "1"), ("123", "A85", "2300")])

    async def test_off_from_manual_clears_a92(self):
        now = int(time.time()*1000)
        self.client.async_get_attributes.return_value = {
            **self.attr, "A92": api.Attribute("0", now), "A89": api.Attribute("1", now)
        }
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.c.async_set_mode(model.Mode.OFF)
        names = [x.args[1:] for x in self.client.async_set_attribute.await_args_list]
        self.assertEqual(names, [("F", "1"), ("A92", "0"), ("A89", "1")])
        self.assertEqual(self.c.zone_state().mode, model.Mode.OFF)

    async def test_c42_mode_write_matches_android_app(self):
        now = int(time.time()*1000)
        self.client.async_get_attributes.return_value = {**self.attr, "C42": api.Attribute("2", now)}
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.c.async_set_hot_water_mode("On")
        self.assertIn(("123", "C42", "2"), [x.args for x in self.client.async_set_attribute.await_args_list])

    async def test_c43_boost_write_matches_android_app(self):
        now = int(time.time()*1000)
        self.client.async_get_attributes.return_value = {**self.attr, "C43": api.Attribute("3", now)}
        with patch.object(coordination.asyncio, "sleep", new=AsyncMock()):
            await self.c.async_set_hot_water_boost(3)
        self.assertIn(("123", "C43", "3"), [x.args for x in self.client.async_set_attribute.await_args_list])

    async def test_c42_or_c43_missing_does_not_issue_command(self):
        self.c.attributes = {k:v for k,v in I500_SINGLE.items()}
        with self.assertRaises(HAError):
            await self.c.async_set_hot_water_mode("On")
        with self.assertRaises(HAError):
            await self.c.async_set_hot_water_boost(2)
        self.client.async_set_attribute.assert_not_awaited()

    async def test_bad_boost_hours_rejected(self):
        for invalid in (-1, 4, True, 1.5):
            with self.subTest(invalid=invalid):
                with self.assertRaises(HAError):
                    await self.c.async_set_hot_water_boost(invalid)

    async def test_cooling_mode_does_not_write_global_s05(self):
        self.c.attributes["S05"] = api.Attribute("1", 10)
        thermostat = climate.SalusThermostat(self.c, "Salus")
        with self.assertRaises(HAError):
            await thermostat.async_set_hvac_mode(HVACMode.HEAT)
        self.client.async_set_attribute.assert_not_awaited()
