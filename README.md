# Salus Thermostat (Salusfy)

Unofficial Home Assistant integration for **SALUS iT500, heating zone 1**, using the same cloud authentication and API as **iT500 Plus**. It provides the existing thermostat, heating output, temperature and heating-history entities.

Version **1.2.1** connects directly to the mobile service. The `salus-it500.com` web portal is no longer required for login, device discovery, readings or commands. Internet access to the SALUS service is still required.

Requires Home Assistant 2025.8 or later.

## Update an existing installation

Update **Salus thermostat** in HACS and restart Home Assistant. The existing integration entry, saved credentials and entity unique IDs are reused; retain your current entry.

If Home Assistant requests authentication, enter the same email and password that work in iT500 Plus. Credentials and thermostat selection can also be changed under **Settings → Devices & services → Salus thermostat → Configure**.

## Installation

In **HACS → Custom repositories**, add `https://github.com/Kosztyk/salusfy` with category **Integration**, download **Salus thermostat**, and restart Home Assistant. Once this repository is accepted into the default HACS catalog, it can also be found through HACS search.

For manual installation, copy the complete **`custom_components/salus`** directory to `/config/custom_components/salus/` and restart. The Home Assistant domain remains **`salus`**.

Open **Settings → Devices & services → Add integration → Salus thermostat**. Enter the iT500 Plus account email and password. Leave Device ID empty to discover the account's iT500 devices; choose a thermostat if there is more than one. Existing numeric device IDs and matching STA numbers are accepted without using the website.

## Behavior

- **Heat** selects manual operation, **Auto** follows the thermostat's schedule, and **Off** selects the thermostat's off mode.
- Temperature changes and mode changes use the mobile API, check the server acknowledgement, and wait briefly for a fresh matching attribute report. If confirmation does not arrive, Home Assistant reports that the command is pending rather than declaring success.
- Heating output comes from the reported **relay status**, independently of the difference between room temperature and setpoint.
- Thermostat, temperature and output entities share a cloud poll every 60 seconds. Ordinary polling does not wake the battery-powered thermostat; control commands request a brief refresh.
- Expired security tokens are renewed automatically. Network requests have timeouts and limited retries. Missing numeric readings are unavailable instead of text values or invented zeros.

## Scope and limitations

This version exposes the original single heating zone. A second heating zone, hot water and other SALUS product families are not implemented or validated by this integration.

The cloud can retain old readings while the battery thermostat sleeps. `last_report_ms` on the climate entity shows the reported timestamp. Existing heating-history sensors remain approximate calculations from HA observations; they are not boiler energy meters.

Offline protocol and migration tests cannot establish whether authentication and controls work with every account or thermostat firmware. Verify the installed update with your own system. Tests never require account credentials.

## Validation and license

See [VALIDATION.md](VALIDATION.md) for test coverage and commands. Licensed under [MIT](LICENSE.txt); the [original Romanian translation](docs/licenta-originala-ro.md) is retained. The mobile client is adapted from [ZaBug/salus-it500](https://github.com/ZaBug/salus-it500), with its [MIT license notice](custom_components/salus/third_party/ZaBug-LICENSE.txt) included.
