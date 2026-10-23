"""Decode the zone-one iT500 attributes used by the existing Salus entities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .api import Attribute


class Mode(StrEnum):
    """Modes reported by the thermostat."""

    OFF = "off"
    HEAT = "heat"
    AUTO = "auto"


def value(attrs: dict[str, Attribute], name: str) -> str | None:
    attr = attrs.get(name)
    return attr.value if attr and attr.value else None


def flag(attrs: dict[str, Attribute], name: str) -> bool | None:
    """Distinguish a missing flag from an explicitly off flag."""
    return {"0": False, "1": True}.get(value(attrs, name))


def temperature(attrs: dict[str, Attribute], name: str) -> float | None:
    raw = value(attrs, name)
    if raw is None:
        return None
    try:
        result = float(raw) / 100
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


@dataclass(frozen=True, slots=True)
class ThermostatState:
    """Missing readings remain None instead of false or zero."""

    current_temperature: float | None
    target_temperature: float | None
    heating: bool | None
    mode: Mode | None
    temporary_hold: bool | None
    online: bool | None
    last_report_ms: int


def decode(attrs: dict[str, Attribute]) -> ThermostatState:
    off, manual = flag(attrs, "A89"), flag(attrs, "A92")
    mode = Mode.OFF if off else Mode.HEAT if manual else Mode.AUTO
    if off is None or (not off and manual is None):
        mode = None
    return ThermostatState(
        current_temperature=temperature(attrs, "A84"),
        target_temperature=temperature(attrs, "A85"),
        heating=flag(attrs, "A87"),
        mode=mode,
        temporary_hold=flag(attrs, "A88"),
        online=flag(attrs, "online"),
        last_report_ms=max(
            (attrs[n].updated_ms for n in ("A84", "A85", "A87", "A89", "A92") if n in attrs), default=0
        ),
    )


def mode_writes(mode: Mode) -> list[tuple[str, str]]:
    """Clear hold flags before leaving off; off preserves the saved program."""
    if mode == Mode.OFF:
        return [("A89", "1")]
    return [("A92", "1" if mode == Mode.HEAT else "0"), ("A88", "0"), ("A89", "0")]
