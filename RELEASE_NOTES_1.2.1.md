# Salusfy 1.2.1

Includes the iT500 Plus authentication and mobile API migration from 1.2.0.

- Explicitly reload the integration after successful reauthentication, including when startup failed before entities were created.
- Use Home Assistant's automatic options reload so saving corrected credentials or device selection also recovers an entry that was not loaded.
- Add regression coverage for both recovery paths. All 44 offline regression and packaging tests pass.

Update **Salus thermostat** through HACS and restart Home Assistant. Existing settings and entity identities are retained. If prompted to authenticate, use the same email and password as iT500 Plus.

Protocol and migration tests use simulated API responses and Home Assistant interfaces; live account login and thermostat control require verification after installing the update.
