"""Offline contracts for the v1.2.2 device UX, battery and sensor correctness.

Battery S03 decode is grounded in both Android APKs' DevAtr.DEVICE_BATTERY
and DeviceDetail.getBatteryLevelResId, which select dev_battery_full/low/very_low.
"""

from datetime import datetime, timedelta, timezone
import unittest
from types import SimpleNamespace

from ha_stubs import interfaces
from support import load

api = load("api")
model = load("model")
runtime = load("runtime")
device = load("device")
with interfaces():
    sensor = load("sensor")
    binary = load("binary_sensor")


def attributes(**pairs):
    return {k: api.Attribute(str(v), 1) for k, v in pairs.items()}


def coordinator(**pairs):
    data = {"A84": "2150", "A85": "2200", "A87": "0", "A88": "0", "A89": "0", "A92": "1", "online": "1", **pairs}
    attr = attributes(**data)
    c = SimpleNamespace(attributes=attr, device_id="STA123", device_type_id="1",
                        zones=model.heating_zones(attr), last_update_success=True,
                        device=api.DeviceInfo("STA123", "Living Room", "1"),
                        data=model.decode(attr), runtime=runtime.HeatingRuntime())
    c.zone_state = lambda zone="A": model.decode(c.attributes, zone)
    return c


class TestDeviceRegistry(unittest.TestCase):
    def test_stable_identifiers_and_cloud_name(self):
        c = coordinator()
        info = device.salus_device_info(c)
        self.assertEqual(info["identifiers"], {("salus", "STA123")})
        self.assertEqual(info["name"], "Living Room")
        self.assertEqual(info["manufacturer"], "SALUS Controls")
        self.assertEqual(info["model"], "iT500 family")
        self.assertNotIn("user", str(info).lower())

    def test_rt310_and_unknown_devices_not_mislabeled(self):
        c = coordinator()
        c.device_id = "SRT999"
        self.assertEqual(device.salus_device_info(c)["model"], "RT310 family")
        c.device_id = "opaque99"
        self.assertEqual(device.salus_device_info(c)["model"], "SALUS cloud device")

    def test_same_device_info_for_every_entity(self):
        c = coordinator(S03="1", A93="2100")
        entities = [sensor.SalusCurrentTempSensor(c, "existing"),
                    binary.SalusCh1HeatOnOffBinarySensor(c, "existing"),
                    sensor.SalusBatteryStatusSensor(c), binary.SalusBatteryLowBinarySensor(c)]
        for entity in entities:
            device.link_entity(entity, c)
            self.assertEqual(entity._attr_device_info["identifiers"], {("salus", "STA123")})


class TestBatteryFromAPK(unittest.TestCase):
    def test_full_low_very_low_no_invented_percentage(self):
        c = coordinator(S03="0")
        status = sensor.SalusBatteryStatusSensor(c)
        warning = binary.SalusBatteryLowBinarySensor(c)
        for raw, result, low in (("0", "Normal", False), ("1", "Low", True), ("2", "Very low", True)):
            c.attributes["S03"] = api.Attribute(raw, 1)
            self.assertTrue(status.available)
            self.assertEqual(status.native_value, result)
            self.assertTrue(warning.available)
            self.assertIs(warning.is_on, low)
        self.assertFalse(hasattr(status, "_attr_native_unit_of_measurement"))

    def test_unknown_and_offline_battery_are_unavailable(self):
        c = coordinator(S03="91")
        self.assertFalse(sensor.SalusBatteryStatusSensor(c).available)
        self.assertFalse(binary.SalusBatteryLowBinarySensor(c).available)
        c.attributes["S03"] = api.Attribute("0", 1)
        c.attributes["online"] = api.Attribute("0", 1)
        self.assertFalse(sensor.SalusBatteryStatusSensor(c).available)
        self.assertFalse(binary.SalusBatteryLowBinarySensor(c).available)


class TestSensorTruth(unittest.TestCase):
    def test_real_relay_not_setpoint_guesses(self):
        c = coordinator(A84="1900", A85="2300", A87="0")
        self.assertEqual(sensor.SalusThermostatState(c, "legacy").native_value, "idle")
        c.attributes["A87"] = api.Attribute("1", 1)
        self.assertEqual(sensor.SalusThermostatState(c, "legacy").native_value, "heating")
        c.attributes["S05"] = api.Attribute("1", 1)
        self.assertEqual(sensor.SalusThermostatState(c, "legacy").native_value, "cooling")

    def test_saved_manual_is_not_active_target(self):
        c = coordinator(A85="2300", A93="1950")
        self.assertEqual(sensor.SalusTargetTempSensor(c).native_value, 23)
        self.assertEqual(sensor.SalusManualSetpointSensor(c).native_value, 19.5)

    def test_invalid_temperature_and_unknown_hot_water_code(self):
        c = coordinator(A84="7000", C42="9")
        self.assertIsNone(sensor.SalusCurrentTempSensor(c, "legacy").native_value)
        self.assertIsNone(sensor.SalusHotWaterModeSensor(c).native_value)

    def test_runtime_uses_actual_a87_only_and_skips_cooling(self):
        c = coordinator(A87="1", S05="1")
        # Used by coordinator when polling: cooling status is intentionally excluded.
        self.assertEqual(model.decode(c.attributes).heating, True)
        self.assertEqual(c.attributes["S05"].value, "1")


class TestRuntimeAccounting(unittest.TestCase):
    def test_crosses_midnight_and_month_exactly(self):
        t = runtime.HeatingRuntime()
        before = datetime(2026, 10, 31, 23, 59, 30, tzinfo=timezone.utc)
        t.observe(before, True)
        t.observe(before + timedelta(seconds=60), True)
        self.assertEqual(t.today_s, 30)
        self.assertEqual(t.yesterday_s, 30)
        self.assertEqual(t.month_s, 30)
        self.assertEqual(t.previous_month_s, 30)

    def test_no_extrapolation_through_offline_or_restarts(self):
        t = runtime.HeatingRuntime()
        begin = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        t.observe(begin, True)
        t.observe(begin + timedelta(hours=1), True)
        self.assertEqual(t.today_s, 0)
        t.observe(begin + timedelta(hours=1, seconds=60), False)
        self.assertEqual(t.today_s, 60)
        t.observe(begin + timedelta(hours=2), None)
        self.assertEqual(t.today_s, 60)
        t.observe(begin + timedelta(hours=2, seconds=60), True)
        self.assertEqual(t.today_s, 60)

    def test_restore_snapshot_and_new_day(self):
        t = runtime.HeatingRuntime()
        before = datetime(2026, 10, 23, 15, tzinfo=timezone.utc)
        t.observe(before, True)
        t.observe(before + timedelta(seconds=60), True)
        snapshot = t.snapshot()
        restored = runtime.HeatingRuntime()
        next_day = before + timedelta(days=1)
        self.assertTrue(restored.restore(snapshot, next_day))
        self.assertEqual(restored.today_s, 0)
        self.assertEqual(restored.yesterday_s, 60)
        self.assertEqual(restored.month_s, 60)
        self.assertFalse(restored.restore(snapshot, next_day))

    def test_bad_or_legacy_snapshot_is_not_trusted(self):
        t = runtime.HeatingRuntime()
        self.assertFalse(t.restore({"last_update": "2026-01-01", "last_state": "heating"},
                                   datetime(2026, 10, 20, tzinfo=timezone.utc)))
        self.assertEqual(t.today_s, 0)


class TestEntitySetup(unittest.IsolatedAsyncioTestCase):
    async def test_all_platform_entities_share_device_identifier(self):
        c = coordinator(S03="1", A93="2100", A90="1", rfrssi="17")
        root = SimpleNamespace(entries=[], async_get_entity_id=lambda *args: None)
        hass = SimpleNamespace(
            registry=root,
            data={"salus": {"entry": {"coordinator": c, "device": c.device, "name": "Salus Thermostat"}}},
        )
        entry = SimpleNamespace(entry_id="entry")
        for platform in (sensor, binary):
            created = []
            await platform.async_setup_entry(hass, entry, lambda entities: created.extend(entities))
            self.assertGreaterEqual(len(created), 3)
            for entity in created:
                self.assertEqual(entity._attr_device_info["identifiers"], {("salus", "STA123")})
                self.assertTrue(getattr(entity, "_attr_has_entity_name", False))
        self.assertEqual(binary.SalusFrostProtectionBinarySensor(c).is_on, True)

    async def test_status_only_unknown_device_still_forms_a_device(self):
        c = coordinator()
        c.device_id = "unknown999"
        c.attributes = attributes(online="1", generic="value")
        c.zones = ()
        hass = SimpleNamespace(
            registry=SimpleNamespace(entries=[], async_get_entity_id=lambda *args: None),
            data={"salus": {"entry": {"coordinator": c, "device": c.device, "name": "Salus Thermostat"}}},
        )
        created = []
        await sensor.async_setup_entry(hass, SimpleNamespace(entry_id="entry"),
                                       lambda entities: created.extend(entities))
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].native_value, "online")
        self.assertEqual(created[0]._attr_device_info["identifiers"], {("salus", "unknown999")})
