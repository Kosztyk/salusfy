"""Resolve renamed entities while retaining their legacy unique IDs."""

from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import DOMAIN


def climate_entity_id(hass, name):
    registry = er.async_get(hass)
    return registry.async_get_entity_id("climate", DOMAIN, f"{name}_climate") or f"climate.{slugify(name)}"


def legacy_unique_id(hass, entry, domain, suffix, fallback):
    for entity in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if entity.entity_id.startswith(f"{domain}.") and entity.unique_id.endswith(suffix):
            return entity.unique_id
    return fallback
