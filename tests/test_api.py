"""Exercise the mobile authentication protocol with deterministic HTTP responses."""

import json
import unittest
from unittest.mock import AsyncMock, patch

from support import load

api = load("api")
model = load("model")
LOGIN = json.dumps({"userId": 73, "securityToken": "token-one"})
DEVICES = """<getDeviceListResponse xmlns="http://arrayent.com/zamapi/">
<devList><devId>1234</devId><devName>STA1234</devName><typeId>1</typeId></devList>
</getDeviceListResponse>"""
ATTRIBUTES = """<getDeviceAttributesWithValuesResponse xmlns="http://arrayent.com/zamapi/">
<attrList><name>A84</name><value>2050</value><updTime>1000</updTime></attrList>
<attrList><name>A85</name><value>2200</value><updTime>1001</updTime></attrList>
<attrList><name>A87</name><value>0</value><updTime>1002</updTime></attrList>
<attrList><name>A88</name><value>0</value><updTime>1003</updTime></attrList>
<attrList><name>A89</name><value>0</value></attrList>
<attrList><name>A92</name><value>1</value></attrList>
<attrList><name>online</name><value>1</value></attrList>
</getDeviceAttributesWithValuesResponse>"""


def fault(code):
    return f"<requestFault><errorCode>{code}</errorCode><errorMsg>Rejected</errorMsg></requestFault>"


class Response:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    async def __aenter__(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self

    async def __aexit__(self, *args):
        pass

    async def text(self):
        return self.body


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def _request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected extra HTTP request")
        return Response(*self.responses.pop(0))

    def post(self, url, **kwargs):
        return self._request("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)


class TestAuthentication(unittest.IsolatedAsyncioTestCase):
    async def test_mobile_login_digest_and_token_are_used_without_website(self):
        session = Session((200, LOGIN), (200, DEVICES))
        devices = await api.SalusClient(session, "user@example.test", "secret").async_get_devices()
        self.assertEqual(devices[0].device_id, "1234")
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://sal-emea-p01-api.arrayent.com/acc/applications/SalusService/sessions")
        self.assertEqual(kwargs["json"], {"username": "user@example.test", "password": "5ebe2294ecd0e0f08eab7690d2a6ee69"})
        self.assertNotIn("secret", repr(session.calls))
        self.assertEqual(session.calls[1][2]["data"], {"secToken": "token-one", "userId": "73"})
        for _, _, kwargs in session.calls:
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(kwargs["timeout"].total, 20)

    async def test_fault_inside_http_200_renews_token(self):
        session = Session((200, LOGIN), (200, fault(106)), (200, json.dumps({"userId": 73, "securityToken": "token-two"})), (200, ATTRIBUTES))
        attrs = await api.SalusClient(session, "u", "p").async_get_attributes("1234")
        self.assertEqual(attrs["A84"].value, "2050")
        self.assertEqual(session.calls[1][2]["data"]["secToken"], "token-one")
        self.assertEqual(session.calls[3][2]["data"]["secToken"], "token-two")

    async def test_http_401_renews_token(self):
        session = Session((200, LOGIN), (401, ""), (200, LOGIN), (200, DEVICES))
        self.assertEqual(len(await api.SalusClient(session, "u", "p").async_get_devices()), 1)

    async def test_rejected_fresh_token_stops_instead_of_looping(self):
        session = Session((200, LOGIN), (200, fault(106)), (200, LOGIN), (200, fault(106)))
        with self.assertRaises(api.SalusAuthError):
            await api.SalusClient(session, "u", "p").async_get_devices()
        self.assertEqual(len(session.calls), 4)

    async def test_credentials_rejected_without_retry(self):
        session = Session((403, "{}"))
        with self.assertRaises(api.SalusAuthError):
            await api.SalusClient(session, "u", "p").async_get_devices()
        self.assertEqual(len(session.calls), 1)

    async def test_malformed_login_is_connection_failure(self):
        for body in ("[]", "null", "not json", '{"securityToken":"token"}'):
            with self.subTest(body=body):
                with self.assertRaises(api.SalusConnectionError):
                    await api.SalusClient(Session((200, body)), "u", "p").async_get_devices()

    async def test_transient_failures_retry_without_relogging(self):
        session = Session((200, LOGIN), (503, ""), (200, DEVICES))
        with patch.object(api.asyncio, "sleep", new=AsyncMock()) as sleep:
            await api.SalusClient(session, "u", "p").async_get_devices()
        self.assertEqual(len(session.calls), 3)
        sleep.assert_awaited_once_with(1)

    async def test_timeouts_are_bounded(self):
        session = Session((200, LOGIN), *((0, TimeoutError()) for _ in range(3)))
        with patch.object(api.asyncio, "sleep", new=AsyncMock()):
            with self.assertRaises(api.SalusConnectionError):
                await api.SalusClient(session, "u", "p").async_get_devices()
        self.assertEqual(len(session.calls), 4)

    async def test_api_error_inside_http_200_is_not_success(self):
        session = Session((200, LOGIN), (200, fault(109)))
        with self.assertRaises(api.SalusApiError) as raised:
            await api.SalusClient(session, "u", "p").async_get_devices()
        self.assertEqual(raised.exception.code, 109)

    async def test_command_must_be_acknowledged(self):
        for code in (0, 7):
            with self.subTest(code=code):
                body = f"<setMultiDeviceAttributes2Response><retCode>{code}</retCode></setMultiDeviceAttributes2Response>"
                session = Session((200, LOGIN), (200, body))
                client = api.SalusClient(session, "u", "p")
                if code:
                    with self.assertRaises(api.SalusApiError):
                        await client.async_set_attribute("1234", "A85", "2100")
                else:
                    await client.async_set_attribute("1234", "A85", "2100")
                self.assertEqual(session.calls[1][0], "GET")
                self.assertEqual(session.calls[1][2]["params"]["name1"], "A85")


class TestDeviceAndState(unittest.TestCase):
    def test_saved_numeric_and_sta_ids_resolve_to_same_device(self):
        devices = api.parse_device_list(DEVICES)
        for requested in ("1234", "STA1234", "sta1234", None):
            self.assertEqual(api.select_device(devices, requested).device_id, "1234")

    def test_explicit_missing_id_never_switches_to_another_thermostat(self):
        with self.assertRaises(api.SalusDeviceError):
            api.select_device(api.parse_device_list(DEVICES), "9999")

    def test_multiple_devices_require_selection(self):
        devices = api.parse_device_list(DEVICES) + [api.DeviceInfo("5678", "STA5678", "1")]
        with self.assertRaises(api.SalusDeviceError):
            api.select_device(devices, "")

    def test_other_salus_device_is_discoverable(self):
        device = api.DeviceInfo("2", "other", "2")
        self.assertEqual(api.select_device([device], "2"), device)

    def test_relay_is_not_guessed_from_temperature_difference(self):
        state = model.decode(api.parse_attributes(ATTRIBUTES))
        self.assertEqual(state.current_temperature, 20.5)
        self.assertEqual(state.target_temperature, 22)
        self.assertFalse(state.heating)
        self.assertEqual(state.mode, model.Mode.HEAT)

    def test_missing_values_and_flags_remain_unknown(self):
        state = model.decode({})
        self.assertIsNone(state.current_temperature)
        self.assertIsNone(state.target_temperature)
        self.assertIsNone(state.heating)
        self.assertIsNone(state.mode)

    def test_invalid_temperatures_do_not_become_sensor_strings(self):
        for raw in ("", "unavailable", "unknown", "NaN", "Infinity"):
            with self.subTest(raw=raw):
                self.assertIsNone(model.decode({"A84": api.Attribute(raw, 0)}).current_temperature)

    def test_invalid_xml_is_controlled_failure(self):
        for text in ("not xml", "<html/>", "<getDeviceListResponse/>"):
            with self.subTest(text=text):
                with self.assertRaises(api.SalusConnectionError):
                    api.parse_attributes(text)

    def test_heat_and_auto_clear_hold_before_leaving_off(self):
        self.assertEqual(model.mode_writes(model.Mode.OFF), [("A92", "0"), ("A88", "0"), ("A89", "1")])
        self.assertEqual(model.mode_writes(model.Mode.HEAT), [("A92", "1"), ("A88", "0"), ("A89", "0")])
        self.assertEqual(model.mode_writes(model.Mode.AUTO), [("A92", "0"), ("A88", "0"), ("A89", "0")])
