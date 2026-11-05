"""Native Home Assistant device registry metadata for SALUS Arrayent devices."""

from __future__ import annotations

from .const import DOMAIN


def salus_device_info(coordinator) -> dict:
    """Group all discovered features under the same stable cloud device ID.

    Do not derive identifiers from mutable display names, email or local IPs.
    SALUS gateway details differ by family; report only known model prefixes.
    """
    cloud = getattr(coordinator, "device", None)
    dev_id = str(coordinator.device_id)
    model = None
    if dev_id.upper().startswith("STA"):
        model = "iT500 family"
    elif dev_id.upper().startswith("SRT"):
        model = "RT310 family"
    return {
        "identifiers": {(DOMAIN, dev_id)},
        "manufacturer": "SALUS Controls",
        "model": model or "SALUS cloud device",
        "name": getattr(cloud, "name", None) or "SALUS Thermostat",
    }


def link_entity(entity, coordinator) -> None:
    """Attach an entity without changing its existing unique ID."""
    entity._attr_device_info = salus_device_info(coordinator)
