# Salusfy — SALUS Cloud integration for Home Assistant

Unofficial Home Assistant integration for SALUS devices registered with the **SALUS/Arrayent mobile cloud**, including **iT500** and **RT310i**. Version **1.2.4** retains the tested v1.2.3 functionality while using the distinct Home Assistant integration domain `salus_cloud_native` (display name **Salus Cloud Native**). The v1.2.2 implementation removes the old hard-coded iT500 device-type filter and uses the device's actual numeric type ID when retrieving its attributes. The retired `salus-it500.com` website is not used.

Requires Home Assistant 2025.8 or later. **Installation builds are published on [GitHub Releases](https://github.com/Kosztyk/salusfy/releases/latest); v1.2.4 is the HACS domain-collision correction release.** Inclusion in the default HACS catalog is pending review of [PR #12460](https://github.com/hacs/default/pull/12460); until it is merged, install it using a HACS custom repository or the manual instructions below.

## Confirmed real-device testing

**RT310i: tested successfully by a device owner with the supplied v1.2.2 build.** In [issue #8 — “Do not work with RT310i anymore”](https://github.com/Kosztyk/salusfy/issues/8), `bthamburg` reported that their RT310i was no longer discovered after an update. After installing the supplied v1.2.2 build, they [confirmed on October 28, 2026](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410):

> Wow, thank you for the fast answer. Works perfect.

**SALUS iT500, firmware 11.7:** repository maintainer and device owner `Kosztyk` confirmed successful real-device testing of **all implemented controls**, including zone-one and zone-two setpoints, operating modes and scheduled overrides, plus hot-water mode and boost. This confirmation was recorded on November 2, 2026. See the [iT500 owner test report](VALIDATION.md#successful-real-device-test-it500).

| Device / capability | Successful real-device confirmation |
| --- | --- |
| RT310i operation with the supplied v1.2.2 build | Independent owner `bthamburg`; [issue #8](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410) |
| iT500 zone-one setpoint, scheduled override and operating modes (`A85`, `A88`, `A89`, `A92`) | Owner `Kosztyk`; firmware 11.7 |
| iT500 zone-two setpoint, scheduled override and operating modes (`B85`, `B88`, `B89`, `B92`) | Owner `Kosztyk`; firmware 11.7 |
| iT500 hot-water Schedule / Once / On / Off (`C42`) and boost (`C43`) | Owner `Kosztyk`; firmware 11.7 |

These are real-device owner confirmations, recorded separately from APK analysis and offline automated tests. The iT500 confirmation covers all implemented controls, including the write paths raised in the HACS review. These results apply to the reported devices; other models and firmware are not automatically covered.

## Installation or upgrade

**New integration domain:** `salus_cloud_native` (with underscores, as required for Home Assistant integration identifiers). The new integration folder is `custom_components/salus_cloud_native/`, and the name shown in Home Assistant is **Salus Cloud Native**. The repository name remains `Kosztyk/salusfy`. This avoids overwriting the unrelated `homeassistant_salus` integration, which also uses `custom_components/salus/`.

For a fresh manual installation, copy the entire `custom_components/salus_cloud_native/` directory from this repository into `/config/custom_components/salus_cloud_native/`, then restart Home Assistant. In HACS, install or update this repository, restart Home Assistant and add **Salus Cloud Native** under **Settings → Devices & services → Add integration**. For new accounts, use the login for the relevant SALUS mobile app. Leave **Device ID** blank for discovery or select a registered device.

### Existing `salus` installations — required manual migration

**The domain change is a breaking configuration migration.** Home Assistant stores the integration domain with each configuration entry; an entry created under `salus` is **not automatically converted** to `salus_cloud_native`. Updating only the Python files is insufficient. To migrate safely:

1. Make a full Home Assistant backup and note/export your current Salusfy devices, entity IDs, custom names, dashboards, automations and any recorder/energy-history dependencies. Keep credentials available.
2. Install or update Salusfy to v1.2.4 through HACS (or manually copy `custom_components/salus_cloud_native/`), then restart Home Assistant. The old `salus` integration folder may remain until explicitly removed.
3. Add a **new** **Salus Cloud Native** config entry for each SALUS cloud device using your account credentials and device selection. Check that the new climate and sensor entities have accurate state. While both entries exist, avoid using automations to send competing commands to the same device.
4. Once the new entry works, remove **only the old Salusfy config entry** created under `salus` in **Settings → Devices & services**. If the `salus` folder belongs exclusively to the old Salusfy installation, remove or uninstall that *old copy* after backing it up. **Do not remove `custom_components/salus/` if it belongs to the unrelated `homeassistant_salus` integration.** Restart Home Assistant.
5. Compare the old and new entity IDs in **Settings → Devices & services → Entities**; use the entity rename UI to restore desired names/IDs once old registrations have been removed. Update automations, scripts, dashboards, notifications and statistics consumers that reference changed entity IDs. Do not edit `.storage` or rename a domain in configuration records manually.

The code retains the old device-specific unique-ID strings for compatibility where possible (e.g. `Salus Thermostat_climate` and device ID based sensor IDs), **but they are scoped to the new integration platform and a new config entry**. Home Assistant may assign different entity IDs (such as `_2` suffixes) or create separate device-registry entries. Automatically preserving previous entity IDs, entity history, dashboard bindings and statistics is **not guaranteed**. See [detailed migration steps](HOW_TO_MANUAL_INSTALL.md#existing-salus-to-salus_cloud_native-migration).

## Native device page and battery status

Every configured Arrayent device now appears as a native Home Assistant **SALUS Controls device**. The same stable cloud device identifier groups its main climate control, optional second zone, diagnostic and operating sensors, hot-water controls, heating-output binary sensors, and conditional battery sensors. Concise entity names use Home Assistant `has_entity_name` semantics. Users with several physical devices can add separate integration entries for each; a single account entry still selects one device.

Both supplied Android apps define `S03` as battery status and map its values to full (0), low (1), very low (2) battery icons. If `S03` appears, the integration creates a **Battery status** sensor and **Battery low** binary sensor. The APK does not provide a verified percentage, so no battery-level percentage entity is created. Optional A90/B90 frost state and raw RF signal appear only if present. Read the [manual installation guide](HOW_TO_MANUAL_INSTALL.md).

## Discovered capabilities

This integration **does not restrict discovery to two model names or a fixed `typeId`**. Every device returned by the account's Arrayent `getDeviceList` is selectable. The response is then inspected for supported capabilities:

| Reported attributes | Home Assistant support |
| --- | --- |
| `A84`, `A85`, `A87` | Zone-one current and target temperatures and heating output |
| `A88`, `A89`, `A92` | Zone-one temporary override and schedule/manual/off commands, *only if all are reported* |
| `A90`, `A93` | Zone-one frost status and saved manual setpoint; `A93` is shown as a separate sensor and climate attribute |
| `B84`, `B85`, `B87`, `B88`, `B89`, `B92`, `B93` | Independent zone-two climate/heating output where present; analogous modes and saved manual setpoint |
| `S06` | iT500 gateway configuration: 0 one zone, 1 two zones, 2 one zone + hot water; avoids ghost zones |
| `S05` | iT500 heating/cooling configuration: correct readout and HVAC action; global configuration is not changed automatically |
| `C42`, `C45` | Hot-water Schedule/Once/On/Off select and actual hot-water output (when present) |
| `C43` | Hot-water boost 0–3 hours (when present) |
| Other Arrayent attribute sets | Cloud-device status and capability metadata; read-only when the complete known control attribute set is absent |

The current setpoint `A85` and the saved manual-mode setpoint `A93` are *different attributes*. Normal setpoint commands write `A85` (and `A88` when activating a scheduled override), matching the provided RT310i 2.2.1 Android app. `A93` is **read and exposed**, and is used as a manual-mode display fallback when `A85` is absent. Writing to `A93` is not supported because the app's normal setpoint command does not write it. The active schedule is not overwritten when switching modes.

For both model families, the documented setpoint range reaches **35°C**; the integration accepts that maximum. Setpoint precision can depend on thermostat configuration (0.1/0.5°C). The iT500 APK uses special A84/B84 values `5000`, `7000`, `8000` as invalid/under-range/over-range display markers: these do not become 50°C/70°C/80°C HA readings. Both APKs refresh devices with `F=1` (the earlier v1.2.2 draft incorrectly used `F=60`).

Polling is every 60 seconds. Temperature and mode commands check acknowledgment and require updated device reports. A relay value is never guessed from the room/target temperature difference. Auth failures trigger reauthentication; transient network failures are retried with limits.

## Compatibility limits

**Universal SALUS compatibility is not guaranteed.** The integration discovers every device returned by this **specific Arrayent mobile account**. Devices using other SALUS ecosystems, gateways, local protocols, or cloud services will not appear through this API. Unknown models have read-only status unless they expose the complete A/B thermostat attribute contract checked against the Android apps; a lone setpoint attribute is not sufficient to permit writing. These attribute checks are not proof of physical-device compatibility. **RT310i operation was successfully confirmed by an independent owner, and all implemented iT500 controls were successfully tested by the maintainer on their SALUS iT500 with firmware 11.7**, as documented above. APK analysis and offline protocol tests provide additional checks. iT500 hot-water modes and boost are exposed only when the relevant Cxx attributes are reported. The Android apps have additional features that this integration does **not** implement, including editing weekly schedules, holiday settings, frost threshold, energy saving, and changing the gateway's global heat/cool setting. This is not a claim of complete mobile-app feature parity.

The legacy heating-history entity IDs are retained for zone one, but their old inconsistent timers are replaced by a shared **estimated relay runtime** tracker. Readings cannot reconstruct historic heating from before the new tracker was installed. For unknown devices with no heating-zone attributes, only the cloud status/capability entity is created. This prevents unrelated products from being misrepresented as thermostats.

## Code provenance, upstream relationship, and licensing

This GitHub repository is historically a **fork of [floringhimie/salusfy](https://github.com/floringhimie/salusfy)**. That upstream repository has **no declared software license**, so its source code cannot simply be treated as MIT-licensed. The old upstream integration used the `salus-it500.com` PHP website and a YAML `climate: - platform: salusfy` implementation. **No substantive source code from its original `custom_components/salusfy/climate.py`, nor its old website login/parsing/write implementation, is retained in the current installable `custom_components/salus_cloud_native/` integration.** Short generic Home Assistant property/method names, configuration terms, and the display name are common interface conventions, not retained upstream logic. The upstream `README.md` and manifest are also not shipped unchanged.

The current integration uses an async Arrayent mobile-cloud implementation. Its `custom_components/salus_cloud_native/api.py` is **adapted from [ZaBug/salus-it500](https://github.com/ZaBug/salus-it500)**, which is MIT-licensed; the original ZaBug notice is bundled in [`custom_components/salus_cloud_native/third_party/ZaBug-LICENSE.txt`](custom_components/salus_cloud_native/third_party/ZaBug-LICENSE.txt). The other shipped integration implementation, capability logic, Home Assistant entities, tests and documentation were developed/reworked for this project, rather than copied from the unlicensed `floringhimie` implementation. The project's MIT license applies to the current project's contribution and the separately MIT-licensed client; **it is not a retroactive license grant for upstream `floringhimie` commits or code**. GitHub retains the fork ancestry as historical attribution.

See [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md) for a file-by-file comparison and the precise licensing boundary.

## Validation

Run `PYTHONPATH=tests python3 -m unittest discover -s tests -v` and `python3 tools/check_repository.py`. For test methodology see [VALIDATION.md](VALIDATION.md). The repository contains an MIT license for the current implementation and retains the MIT notice from the Arrayent client used by `api.py`. The original `floringhimie/salusfy` repository has no declared license; see the [source comparison and licensing scope](SOURCE_PROVENANCE.md).
