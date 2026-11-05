## 1.2.4 — unique integration domain and migration guidance (2026-11-05)

- Rename the **Home Assistant integration domain** from `salus` to **`salus_cloud_native`** and relocate the complete integration package to `custom_components/salus_cloud_native/`, resolving the HACS catalog collision with `homeassistant_salus`.
- Change the UI integration display name to **Salus Cloud Native** and update the manifest, constants, HACS metadata, packaging/test helpers and release workflow together.
- Document the breaking config-entry domain migration, the new device-registry namespace, legacy unique-ID string behavior and possible entity-ID changes. No automatic migration of entity registrations, dashboards, automations or historic statistics is claimed.
- Preserve the same Arrayent client, setpoint/mode/hot-water controls and real-device evidence from v1.2.3. No thermostat write payloads changed.

## 1.2.3 — release synchronization and source provenance (2026-11-04)

- Ship the real-device iT500 firmware 11.7 confirmation already documented on `main` after v1.2.2 was tagged; include zone-one (`A85/A88/A89/A92`), zone-two (`B85/B88/B89/B92`), hot-water mode (`C42`) and boost (`C43`). The RT310i owner report remains separately linked.
- Distinguish successful owner-reported hardware operation from automated offline tests, APK research and unavailable raw protocol captures.
- Audit current source against the unlicensed original `floringhimie/salusfy` repository. Document that no substantive original implementation remains in the installable integration and clarify MIT-licensed `ZaBug/salus-it500` client attribution.
- Update HACS release/validation guidance to match what new installs download. No functional thermostat behavior is changed from v1.2.2.

## 1.2.2 — device UI, multi-model compatibility and sensor audit (2026-10-28)

- Register one native Home Assistant SALUS device per configured cloud device; group its controls and readings, and use concise entity names.
- Add mobile-APK-verified `S03` battery status and low-battery binary entities, without claiming percentage.
- Add conditional frost-state binary sensors (A90/B90), raw RF status and per-zone target/mode readings; keep relay-based HVAC state and decode C42 hot-water mode labels.
- Replace unreliable standalone heating-history time accumulation with one bounded, time-zone-aware, restart-restorable *estimate* based on A87 heating output.
- Preserve established unique IDs and existing device selection/authentication.
- All 90 offline tests pass.
- **RT310i successfully tested by a real device owner:** after installing the supplied v1.2.2 build for the discovery regression in [issue #8](https://github.com/Kosztyk/salusfy/issues/8), `bthamburg` [reported on October 28, 2026](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410): “Wow, thank you for the fast answer. Works perfect.”
- **iT500 real-device confirmation recorded November 2, 2026:** maintainer/device owner `Kosztyk` confirmed successful testing of all implemented controls on **SALUS iT500 firmware 11.7**, including zone-one and zone-two setpoints/modes/overrides, hot-water mode (`C42`) and boost (`C43`). See the [owner test report](VALIDATION.md#successful-real-device-test-it500). APK analysis/offline tests and real-device owner reports are separate evidence.

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
