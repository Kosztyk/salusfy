"""Offline regression tests for saved configuration, identities and commands."""

import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ha_stubs import AuthFailed, HAError, UpdateFailed, interfaces
from support import load
from test_api import ATTRIBUTES

api = load("api")
model = load("model")
with interfaces():
    coordinator_module = load("coordinator")
    climate = load("climate")
    sensor = load("sensor")
    binary = load("binary_sensor")
    entity = load("entity")
    flow_module = load("config_flow")


class TestCoordinator(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.attrs = api.parse_attributes(ATTRIBUTES)
        self.client = SimpleNamespace(async_get_attributes=AsyncMock(return_value=self.attrs), async_set_attribute=AsyncMock())
        self.entry = SimpleNamespace(async_start_reauth=Mock())
        self.coordinator = coordinator_module.SalusCoordinator(object(), self.entry, self.client, "1234")
        await self.coordinator.async_config_entry_first_refresh()

    async def test_write_is_woken_and_confirmed_from_a_fresh_report(self):
        updated = {**self.attrs, "A85": api.Attribute("2120", int(time.time() * 1000))}
        self.client.async_get_attributes.return_value = updated
        with patch.object(coordinator_module.asyncio, "sleep", new=AsyncMock()):
            await self.coordinator.async_set_temperature(21.2)
        self.assertEqual(self.client.async_set_attribute.await_args_list[0].args, ("1234", "F", "60"))
        self.assertEqual(self.client.async_set_attribute.await_args_list[1].args, ("1234", "A85", "2120"))
        self.assertEqual(self.coordinator.data.target_temperature, 21.2)

    async def test_failed_write_does_not_publish_an_optimistic_value(self):
        self.client.async_set_attribute.side_effect = api.SalusApiError(7, "refused")
        with self.assertRaises(HAError):
            await self.coordinator.async_set_temperature(21)
        self.assertEqual(self.coordinator.data.target_temperature, 22)

    async def test_stale_matching_value_is_not_command_confirmation(self):
        self.client.async_get_attributes.return_value = {**self.attrs, "A85": api.Attribute("2120", 1)}
        with patch.object(coordinator_module.asyncio, "sleep", new=AsyncMock()):
            with self.assertRaisesRegex(HAError, "not confirmed"):
                await self.coordinator.async_set_temperature(21.2)

    async def test_unchanged_cloud_copy_does_not_confirm(self):
        with patch.object(coordinator_module.asyncio, "sleep", new=AsyncMock()):
            with self.assertRaisesRegex(HAError, "not confirmed"):
                await self.coordinator.async_set_temperature(21)
        self.assertEqual(self.coordinator.data.target_temperature, 22)

    async def test_auth_failure_during_command_requests_reauthentication(self):
        self.client.async_set_attribute.side_effect = api.SalusAuthError("rejected")
        with self.assertRaises(HAError):
            await self.coordinator.async_set_temperature(21)
        self.entry.async_start_reauth.assert_called_once()

    async def test_auth_failure_during_poll_is_auth_failure(self):
        self.client.async_get_attributes.side_effect = api.SalusAuthError("rejected")
        with self.assertRaises(AuthFailed):
            await self.coordinator._async_update_data()

    async def test_empty_response_is_not_a_valid_zero_reading(self):
        self.client.async_get_attributes.return_value = {}
        with self.assertRaises(UpdateFailed):
            await self.coordinator._async_update_data()

    async def test_invalid_setpoints_never_reach_the_cloud(self):
        for temperature in (float("nan"), float("inf"), -1, 100):
            with self.subTest(temperature=temperature):
                with self.assertRaises(HAError):
                    await self.coordinator.async_set_temperature(temperature)
        self.client.async_set_attribute.assert_not_awaited()


class TestEntities(unittest.TestCase):
    def setUp(self):
        self.attrs = api.parse_attributes(ATTRIBUTES)
        self.coordinator = SimpleNamespace(data=model.decode(self.attrs), last_update_success=True)

    def test_climate_unique_id_is_unchanged(self):
        thermostat = climate.SalusThermostat(self.coordinator, "Salus Thermostat")
        self.assertEqual(thermostat._attr_unique_id, "Salus Thermostat_climate")
        self.assertEqual(thermostat.current_temperature, 20.5)

    def test_missing_temperature_returns_none_and_is_unavailable(self):
        self.coordinator.data = model.decode({})
        temperature = sensor.SalusCurrentTempSensor(self.coordinator, "climate.salus_thermostat_current_temperature")
        self.assertIsNone(temperature.native_value)
        self.assertFalse(temperature.available)

    def test_reported_off_relay_overrides_temperature_difference(self):
        heating = binary.SalusCh1HeatOnOffBinarySensor(self.coordinator, "legacy")
        self.assertFalse(heating.is_on)
        self.assertTrue(heating.available)
        self.coordinator.data = model.decode({})
        self.assertIsNone(heating.is_on)
        self.assertFalse(heating.available)

    def test_offline_gateway_makes_entities_unavailable(self):
        self.coordinator.data = model.decode({**self.attrs, "online": api.Attribute("0", 0)})
        for item in (climate.SalusThermostat(self.coordinator, "Salus Thermostat"), sensor.SalusCurrentTempSensor(self.coordinator, "legacy"), binary.SalusCh1HeatOnOffBinarySensor(self.coordinator, "legacy")):
            self.assertFalse(item.available)

    def test_existing_unique_id_survives_climate_entity_rename(self):
        unique_id = "climate.salus_thermostat_current_temperature"
        registry = SimpleNamespace(entries=[SimpleNamespace(entity_id="sensor.renamed_temperature", unique_id=unique_id)])
        self.assertEqual(entity.legacy_unique_id(SimpleNamespace(registry=registry), SimpleNamespace(entry_id="old"), "sensor", "_current_temperature", "climate.renamed_current_temperature"), unique_id)

    def test_unavailable_restored_history_is_tolerated(self):
        self.assertEqual(sensor._restore_float("unavailable"), 0)
        self.assertEqual(sensor._restore_float("unknown"), 0)
        self.assertEqual(sensor._restore_float("NaN"), 0)
        self.assertEqual(sensor._restore_float("1.25"), 1.25)


class TestFlows(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.device = api.DeviceInfo("1234", "STA1234", "1")
        self.credentials = {"username": "user@example.test", "password": "new-password"}
        self.flow = flow_module.SalusConfigFlow()
        self.flow.hass = object()

    async def test_setup_discovers_id_from_app_credentials(self):
        with patch.object(flow_module, "_fetch_devices", new=AsyncMock(return_value=[self.device])):
            result = await self.flow.async_step_user(self.credentials)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"]["id"], "1234")
        self.assertEqual(result["data"]["name"], "Salus Thermostat")

    async def test_multiple_devices_show_selection(self):
        devices = [self.device, api.DeviceInfo("5678", "STA5678", "1")]
        with patch.object(flow_module, "_fetch_devices", new=AsyncMock(return_value=devices)):
            result = await self.flow.async_step_user(self.credentials)
            self.assertEqual(result["step_id"], "device")
            result = await self.flow.async_step_device({"id": "5678"})
        self.assertEqual(result["data"]["id"], "5678")

    async def test_invalid_credentials_show_auth_error(self):
        with patch.object(flow_module, "_fetch_devices", new=AsyncMock(side_effect=api.SalusAuthError("rejected"))):
            result = await self.flow.async_step_user(self.credentials)
        self.assertEqual(result["errors"], {"base": "invalid_auth"})

    async def test_existing_entry_without_unique_id_is_not_duplicated(self):
        self.flow.entries = [SimpleNamespace(data={"id": "1234"}, options={})]
        with patch.object(flow_module, "_fetch_devices", new=AsyncMock(return_value=[self.device])):
            result = await self.flow.async_step_user(self.credentials)
        self.assertEqual(result["reason"], "already_configured")

    async def test_options_validate_credentials_and_preserve_existing_options(self):
        entry = SimpleNamespace(data={"id": "1234", "username": "old", "password": "old"}, options={"name": "Existing name"})
        flow = flow_module.SalusOptionsFlowHandler(entry)
        flow.hass = object()
        with patch.object(flow_module, "_fetch_devices", new=AsyncMock(return_value=[self.device])):
            result = await flow.async_step_init({**self.credentials, "id": "1234"})
        self.assertEqual(result["data"]["name"], "Existing name")
        self.assertEqual(result["data"]["password"], "new-password")
        self.assertEqual(entry.data["password"], "old")

    async def test_reauth_updates_credentials_in_both_old_storage_locations(self):
        self.flow.reauth_entry = SimpleNamespace(data={"id": "1234", "password": "old"}, options={"password": "overridden-old"})
        with patch.object(flow_module, "_fetch_devices", new=AsyncMock(return_value=[self.device])):
            result = await self.flow.async_step_reauth_confirm(self.credentials)
        self.assertEqual(result["reason"], "reauth_successful")
        self.assertEqual(self.flow.reauth_entry.data["password"], "new-password")
        self.assertEqual(self.flow.reauth_entry.options["password"], "new-password")

    async def test_reauth_rejects_a_different_account_without_modifying_entry(self):
        self.flow.reauth_entry = SimpleNamespace(data={"id": "9999", "password": "old"}, options={})
        with patch.object(flow_module, "_fetch_devices", new=AsyncMock(return_value=[self.device])):
            result = await self.flow.async_step_reauth_confirm(self.credentials)
        self.assertEqual(result["errors"], {"base": "invalid_device"})
        self.assertEqual(self.flow.reauth_entry.data["password"], "old")
