"""Async client for SALUS devices registered with the Arrayent mobile cloud.

No Home Assistant imports: the session is injected, so the module is testable on
its own. Adapted from ZaBug/salus-it500 (MIT), based on RichyA/pyit500.
See third_party/ZaBug-LICENSE.txt for the upstream license notice.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_HOST = "https://sal-emea-p01-api.arrayent.com"
LOGIN_URL = f"{API_HOST}/acc/applications/SalusService/sessions"
ZAMAPI_URL = f"{API_HOST}/zdk/services/zamapi"

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20, connect=10)
RETRY_DELAYS = (1, 3)

# requestFault error codes seen on the live API.
ERROR_INVALID_TOKEN = 106
ERROR_DEVICE_NOT_FOUND = 109
AUTH_ERROR_CODES = {ERROR_INVALID_TOKEN}


class SalusError(Exception):
    """Base error."""


class SalusAuthError(SalusError):
    """Credentials rejected."""


class SalusDeviceError(SalusError):
    """A device must be selected from the authenticated account."""


class SalusConnectionError(SalusError):
    """Network problem or server error after retries."""


class SalusApiError(SalusError):
    """The API answered with an error code."""

    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(f"{message} (code {code})")
        self.code = code


@dataclass(frozen=True, slots=True)
class Attribute:
    """One device attribute as reported by the cloud."""

    value: str
    updated_ms: int  # epoch milliseconds of the last device report, 0 if never


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Device from the account's device list."""

    device_id: str
    name: str
    type_id: str


def hash_password(password: str) -> str:
    """The API expects the MD5 hex digest of the password."""
    return hashlib.md5(password.encode()).hexdigest()  # noqa: S324 - protocol requirement


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip()
    return ""


def parse_document(text: str, expected: str) -> ET.Element:
    """Reject malformed XML and unexpected documents without exposing their body."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as err:
        raise SalusConnectionError("SALUS returned invalid XML") from err
    if _local(root.tag) != expected:
        raise SalusConnectionError("SALUS returned an unexpected XML document")
    return root


def select_device(devices: list[DeviceInfo], device_id: str | None) -> DeviceInfo:
    """Resolve any account device; never assume a fixed numeric device type.

    Preserve the existing numeric-ID and device-name selections across upgrades.
    Do not silently select another device if the saved device disappears.
    """
    requested = str(device_id or "").strip()
    if requested and requested.casefold() != "auto":
        for device in devices:
            if requested == device.device_id or requested.casefold() == device.name.casefold():
                return device
        raise SalusDeviceError("The selected SALUS device is not on this account")
    if len(devices) == 1:
        return devices[0]
    if not devices:
        raise SalusDeviceError("No devices were returned by the SALUS mobile cloud")
    raise SalusDeviceError("Select a SALUS device from this account")


def parse_fault(text: str) -> SalusApiError | None:
    """Return the error carried by a requestFault document, if any."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    if _local(root.tag) != "requestFault":
        return None
    code = _child_text(root, "errorCode")
    return SalusApiError(int(code) if code.isdigit() else None, _child_text(root, "errorMsg"))


def parse_attributes(text: str) -> dict[str, Attribute]:
    """Parse a getDeviceAttributesWithValues response."""
    root = parse_document(text, "getDeviceAttributesWithValuesResponse")
    attributes: dict[str, Attribute] = {}
    for element in root:
        if _local(element.tag) != "attrList":
            continue
        name = _child_text(element, "name")
        if not name:
            continue
        updated = _child_text(element, "updTime")
        attributes[name] = Attribute(
            value=_child_text(element, "value"),
            updated_ms=int(updated) if updated.isdigit() else 0,
        )
    # Arrayent includes device presence in the response, not necessarily in attrList.
    presence = _child_text(root, "presenceInfo")
    if "online" not in attributes and presence in ("0", "1"):
        attributes["online"] = Attribute(value=presence, updated_ms=0)
    return attributes


def parse_device_list(text: str) -> list[DeviceInfo]:
    """Parse every account device regardless of its model, name or type ID."""
    root = parse_document(text, "getDeviceListResponse")
    devices = []
    for element in root:
        if _local(element.tag) != "devList":
            continue
        dev_id = _child_text(element, "devId") or _child_text(element, "deviceId")
        if not dev_id:
            continue
        devices.append(DeviceInfo(
            device_id=dev_id,
            name=_child_text(element, "devName") or _child_text(element, "deviceName") or dev_id,
            type_id=_child_text(element, "typeId") or _child_text(element, "deviceTypeId"),
        ))
    return devices


def parse_ret_code(text: str) -> int:
    """Return retCode of a setMultiDeviceAttributes2 response."""
    root = parse_document(text, "setMultiDeviceAttributes2Response")
    code = _child_text(root, "retCode")
    if not code.lstrip("-").isdigit():
        raise SalusConnectionError("SALUS returned an invalid command acknowledgement")
    return int(code)


class SalusClient:
    """Session against the Salus cloud. One instance per account."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password_hash = hash_password(password)
        self._user_id: str | None = None
        self._token: str | None = None
        self._lock = asyncio.Lock()

    @property
    def user_id(self) -> str | None:
        """User id of the logged-in account."""
        return self._user_id

    def reset_session(self) -> None:
        """Drop the token; the next call logs in again."""
        self._token = None

    async def login(self) -> None:
        """Get a new security token."""
        try:
            async with self._session.post(
                LOGIN_URL,
                json={"username": self._username, "password": self._password_hash},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
            ) as resp:
                text = await resp.text()
                status = resp.status
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SalusConnectionError("Could not reach the SALUS login service") from err
        try:
            data: dict[str, Any] = json.loads(text)
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if status in (401, 403) or (status in (200, 400) and "errorCode" in data):
            raise SalusAuthError(f"SALUS rejected the email or password (HTTP {status})")
        if status != 200 or not data.get("securityToken") or not data.get("userId"):
            raise SalusConnectionError(f"Unexpected login response (HTTP {status})")
        self._user_id = str(data["userId"])
        self._token = str(data["securityToken"])

    async def _call(self, method: str, path: str, params: dict[str, str]) -> str:
        """Renew a rejected token once, and bound transient retries."""
        renewed = False
        for attempt in range(len(RETRY_DELAYS) + 1):
            if attempt:
                await asyncio.sleep(RETRY_DELAYS[attempt - 1])
            while True:
                if self._token is None:
                    await self.login()
                query = {**params, "secToken": self._token, "userId": self._user_id}
                try:
                    url = f"{ZAMAPI_URL}/{path}"
                    if method == "get":
                        request = self._session.get(url, params=query, timeout=REQUEST_TIMEOUT, allow_redirects=False)
                    else:
                        request = self._session.post(url, data=query, timeout=REQUEST_TIMEOUT, allow_redirects=False)
                    async with request as response:
                        text, status = await response.text(), response.status
                except (aiohttp.ClientError, TimeoutError):
                    break
                fault = parse_fault(text)
                if status in (401, 403) or (fault and fault.code == ERROR_INVALID_TOKEN):
                    self._token = None
                    if renewed:
                        raise SalusAuthError("SALUS rejected a renewed security token")
                    renewed = True
                    continue
                if status == 429 or status >= 500:
                    break
                if fault:
                    raise fault
                if status != 200:
                    raise SalusConnectionError(f"SALUS returned HTTP {status}")
                return text
        raise SalusConnectionError("SALUS is unavailable after bounded retries")

    async def async_get_devices(self) -> list[DeviceInfo]:
        """Devices registered on the account."""
        async with self._lock:
            return parse_device_list(await self._call("post", "getDeviceList", {}))

    async def async_get_attributes(self, device_id: str, device_type_id: str | None = None) -> dict[str, Attribute]:
        """All attributes of a device, as last reported to the cloud."""
        async with self._lock:
            params = {"devId": device_id}
            if device_type_id:
                params["deviceTypeId"] = str(device_type_id)
            text = await self._call("post", "getDeviceAttributesWithValues", params)
        return parse_attributes(text)

    async def async_set_attribute(self, device_id: str, name: str, value: str | int) -> None:
        """Set one attribute per call for devices without multi-attribute support."""
        async with self._lock:
            text = await self._call(
                "get",
                "setMultiDeviceAttributes2",
                {"devId": device_id, "name1": name, "value1": str(value)},
            )
        code = parse_ret_code(text)
        if code != 0:
            raise SalusApiError(code, f"Setting {name}={value} was refused")
