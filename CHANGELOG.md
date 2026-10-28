## 1.2.2 — local device-UI/sensor-audited build (2026-10-28)

- Register one native Home Assistant SALUS device per configured cloud device; group its controls and readings, and use concise entity names.
- Add mobile-APK-verified `S03` battery status and low-battery binary entities, without claiming percentage.
- Add conditional frost-state binary sensors (A90/B90), raw RF status and per-zone target/mode readings; keep relay-based HVAC state and decode C42 hot-water mode labels.
- Replace unreliable standalone heating-history time accumulation with one bounded, time-zone-aware, restart-restorable *estimate* based on A87 heating output.
- Preserve established unique IDs and existing device selection/authentication.
- All 90 offline tests pass; physical-device acceptance testing is still necessary.

# Changelog

## v1.2.1 — Authentication recovery
- Reload explicitly after reauthentication following a failed initial setup.
- Use native automatic reload for saved options without requiring a loaded integration listener.
- Add tests for both recovery paths.

## v1.2.0 — iT500 mobile API
- Replace website scraping with app authentication, token renewal and mobile API reads/writes.
- Discover devices from the account without a working web portal; retain saved configuration and existing entity unique IDs.
- Share asynchronous polling and use the reported relay status for heating output.
- Fix unavailable numeric sensor values and restored heating-history values.
- Add bounded timeouts/retries, reauthentication, command acknowledgement checks and protocol regression tests.

## v1.1.4 — HACS readiness
- HACS and Hassfest CI validation; packaging checks and release automation.
- Standard MIT license recognized by GitHub; original Romanian translation preserved.
- Correct integration manifest codeowner, dependencies and field ordering.
- Update HACS installation and UI configuration guidance.
- No changes to thermostat authentication, Salus cloud operations or entity state behavior.

## 1.2.2 — multi-model Arrayent device discovery, iT500/RT310i APK audit

- Remove numeric iT500 type-ID filter; use each account device's real type ID in attribute requests.
- Add dynamic zone-two climate, RT310i A93 manual target reading, A88 scheduled override control, hot-water read-only entities and generic status for other models.
- Add offline multimodel and iT500 APK regression tests (75 total); preserve existing iT500/HA identities and history sensors.
- Correct `F=1`, Off/Manual/Auto mode transition flags and override interpretation, iT500 S06 zone configuration, invalid iT500 temperature markers and S05 cooling display.
- Add hot-water select (C42) and 0–3 hour boost control (C43), gated by reported capabilities and topology.
