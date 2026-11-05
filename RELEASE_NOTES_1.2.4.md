# Salusfy v1.2.4 — Salus Cloud Native domain migration

**HACS review fix:** Home Assistant integration domain has changed from `salus` to **`salus_cloud_native`** (display name **Salus Cloud Native**). The entire integration now installs in `custom_components/salus_cloud_native/`, avoiding the name and folder collision with `homeassistant_salus` in the HACS default catalog.

This is a **breaking configuration-entry migration** for existing `salus` users. A Home Assistant entry for the old domain is *not* automatically migrated. Read the [README migration guide](README.md#existing-salus-installations--required-manual-migration) and [step-by-step installation instructions](HOW_TO_MANUAL_INSTALL.md#3-existing-salus-to-salus_cloud_native-migration) before updating: back up, install the new integration, add a new **Salus Cloud Native** config entry per device, verify its entities, remove only the old Salusfy entry, and reassign entity IDs/automations as needed. Device identifiers are now namespaced to the new integration; historical statistics and entity IDs are not automatically migrated.

**Functionality:** No Arrayent protocol changes, no change to previously tested iT500 and RT310i thermostat controls. The earlier test confirmation and licensing provenance statements remain applicable. The repository remains named `Kosztyk/salusfy`.

**Validation:** The GitHub Actions HACS, Hassfest and packaging/Python jobs must succeed for the v1.2.4 commit before publishing this release. This note does not assert any new physical-device testing.
