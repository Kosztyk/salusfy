"""Capability-driven decoding of SALUS heating zones and generic Arrayent devices.

The bundled iT500 Plus and RT310i apps define Axx/Bxx heating-zone
attributes and Cxx hot-water attributes. A93 is the *saved manual setpoint*, not the active
A85 setpoint. It is read and surfaced but never blindly written: the Android
app's temperature-change operation writes A85 and (in schedule) A88.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .api import Attribute


class Mode(StrEnum):
    OFF = "off"
    HEAT = "heat"
    AUTO = "auto"


ZONE_PREFIXES = ("A", "B")
# iT500 Plus Android v2.2.1: DevAtr.S06 system types.
# 0 = single heating zone, 1 = two heating zones, 2 = heating + hot water.
IT500_ZONE_SYSTEM_TYPES = {"0": ("A",), "1": ("A", "B"), "2": ("A",)}
HOT_WATER_MODES = {"0": "Schedule", "1": "Once", "2": "On", "3": "Off"}
HOT_WATER_MODE_VALUES = {label: code for code, label in HOT_WATER_MODES.items()}


def has_hot_water(attrs: dict[str, Attribute]) -> bool:
    """Apply the iT500 S06 topology if reported, otherwise infer from Cxx."""
    return (value(attrs, "S06") in (None, "2")
            and any(code in attrs for code in ("C42", "C43", "C45")))



def value(attrs: dict[str, Attribute], name: str) -> str | None:
    attr = attrs.get(name)
    return attr.value if attr and attr.value != "" else None


def flag(attrs: dict[str, Attribute], name: str) -> bool | None:
    """Avoid treating a missing value as an explicit off/false."""
    return {"0": False, "1": True}.get(value(attrs, name))


def temperature(attrs: dict[str, Attribute], name: str) -> float | None:
    raw = value(attrs, name)
    if raw is None:
        return None
    try:
        result = float(raw) / 100
    except (ValueError, TypeError):
        return None
    # iT500 heating UI treats the following sensor encodings as non-numeric
    # placeholders (no reading / too low / too high), not as temperatures.
    if name.endswith("84") and raw in ("5000", "7000", "8000"):
        return None
    return result if math.isfinite(result) else None


def heating_zones(attrs: dict[str, Attribute]) -> tuple[str, ...]:
    """Infer actual zone presence from measurements; no model/type whitelist."""
    present = tuple(prefix for prefix in ZONE_PREFIXES if
                    f"{prefix}84" in attrs or f"{prefix}85" in attrs or
                    f"{prefix}87" in attrs or f"{prefix}93" in attrs)
    # The app determines zone topology using S06; stale Bxx values must not
    # create a second zone on an iT500 gateway configured for hot water.
    supported = IT500_ZONE_SYSTEM_TYPES.get(value(attrs, "S06"))
    if supported is not None:
        return tuple(prefix for prefix in present if prefix in supported)
    return present


def can_set_temperature(attrs: dict[str, Attribute], zone: str = "A") -> bool:
    # Same A/B control contract as the two supplied SALUS applications.
    # An unfamiliar device exposing just an A85 reading is not proven writable.
    return (f"{zone}85" in attrs and can_set_mode(attrs, zone))


def can_set_mode(attrs: dict[str, Attribute], zone: str = "A") -> bool:
    # Do not issue unexplained mode commands to other SALUS/Arrayent models.
    return all(f"{zone}{code}" in attrs for code in ("88", "89", "92")) and zone in heating_zones(attrs)


@dataclass(frozen=True, slots=True)
class ThermostatState:
    current_temperature: float | None
    target_temperature: float | None
    heating: bool | None
    mode: Mode | None
    temporary_hold: bool | None
    online: bool | None
    last_report_ms: int
    manual_target_temperature: float | None = None
    frost_protection: bool | None = None
    zone: str = "A"


def decode(attrs: dict[str, Attribute], zone: str = "A") -> ThermostatState:
    """Decode a zone using the RT310i/iT500 attribute convention."""
    if zone not in ZONE_PREFIXES:
        raise ValueError("Unknown thermostat zone")
    off, manual = flag(attrs, f"{zone}89"), flag(attrs, f"{zone}92")
    run_mode = flag(attrs, f"{zone}88")
    # iT500's HeatZone.getDeviceRunningMode(): manual A92 takes precedence
    # over A89; A88=1 with both 89/92=0 means schedule override, not Off.
    if manual is None or off is None:
        mode = None
    elif manual:
        mode = Mode.HEAT
    elif off:
        mode = Mode.OFF
    else:
        mode = Mode.AUTO
    manual_target = temperature(attrs, f"{zone}93")
    # A85/B85 is the active setpoint. A93 is a saved manual-mode setpoint;
    # use it as fallback only when a device does not report its active value.
    active = temperature(attrs, f"{zone}85")
    if active is None and mode == Mode.HEAT:
        active = manual_target
    return ThermostatState(
        current_temperature=temperature(attrs, f"{zone}84"),
        target_temperature=active,
        heating=flag(attrs, f"{zone}87"),
        mode=mode,
        temporary_hold=(run_mode if mode == Mode.AUTO else False if mode is not None else None),
        online=flag(attrs, "online"),
        last_report_ms=max((attrs[n].updated_ms for n in
                            (f"{zone}84", f"{zone}85", f"{zone}87", f"{zone}88", f"{zone}89", f"{zone}92", f"{zone}93")
                            if n in attrs), default=0),
        manual_target_temperature=manual_target,
        frost_protection=flag(attrs, f"{zone}90"),
        zone=zone,
    )


def mode_writes(mode: Mode, zone: str = "A") -> list[tuple[str, str]]:
    """Match the app's manual/schedule/off field pairs for each heating zone."""
    if zone not in ZONE_PREFIXES:
        raise ValueError("Unknown thermostat zone")
    if mode == Mode.OFF:
        # Clearing manual mode is essential: the iT500 decoder prioritizes
        # A92/B92 over A89/B89, so changing only 89 does NOT reliably turn off.
        return [(f"{zone}92", "0"), (f"{zone}88", "0"), (f"{zone}89", "1")]
    return [(f"{zone}92", "1" if mode == Mode.HEAT else "0"),
            (f"{zone}88", "0"), (f"{zone}89", "0")]
