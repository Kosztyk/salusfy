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
