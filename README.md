# Salusfy — SALUS Cloud integration for Home Assistant

Unofficial Home Assistant integration for SALUS devices registered with the **SALUS/Arrayent mobile cloud**, including **iT500** and **RT310i**. Version **1.2.2** removes the old hard-coded iT500 device-type filter and uses the device's actual numeric type ID when retrieving its attributes. The retired `salus-it500.com` website is not used.

Requires Home Assistant 2025.8 or later. **v1.2.2 is published on [GitHub Releases](https://github.com/Kosztyk/salusfy/releases/tag/v1.2.2).** Inclusion in the default HACS catalog is pending review of [PR #12460](https://github.com/hacs/default/pull/12460); until it is merged, install it using a HACS custom repository or the manual instructions below.

## Installation or upgrade

For manual installation, extract this package and copy **`custom_components/salus`** to `/config/custom_components/salus/` in Home Assistant, replacing the previous integration files, then restart Home Assistant. The domain remains `salus`, and existing configured entries/zone-one unique IDs are preserved. A backup is recommended before updating.

For new accounts, go to **Settings → Devices & services → Add integration → Salus thermostat**, then enter the login used for the relevant SALUS mobile app. Leave **Device ID** empty for discovery, or enter the numeric cloud ID or displayed device name (such as `SRT…` or `STA…`). When multiple devices are registered, a selection screen is shown. Configure each additional device separately.

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
| Other Arrayent attribute sets | Cloud-device status and capability metadata; **no unverified write controls** |

The current setpoint `A85` and the saved manual-mode setpoint `A93` are *different attributes*. Normal setpoint commands write `A85` (and `A88` when activating a scheduled override), matching the provided RT310i 2.2.1 Android app. `A93` is **read and exposed**, and is used as a manual-mode display fallback when `A85` is absent. Writing to `A93` is not supported because the app's normal setpoint command does not write it. The active schedule is not overwritten when switching modes.

For both model families, the documented setpoint range reaches **35°C**; the integration accepts that maximum. Setpoint precision can depend on thermostat configuration (0.1/0.5°C). The iT500 APK uses special A84/B84 values `5000`, `7000`, `8000` as invalid/under-range/over-range display markers: these do not become 50°C/70°C/80°C HA readings. Both APKs refresh devices with `F=1` (the earlier v1.2.2 draft incorrectly used `F=60`).

Polling is every 60 seconds. Temperature and mode commands check acknowledgment and require updated device reports. A relay value is never guessed from the room/target temperature difference. Auth failures trigger reauthentication; transient network failures are retried with limits.

## Compatibility limits

**Universal SALUS compatibility is not guaranteed.** The integration discovers every device returned by this **specific Arrayent mobile account**. Devices using other SALUS ecosystems, gateways, local protocols, or cloud services will not appear through this API. Unknown models have read-only status unless they expose the complete verified A/B thermostat control contract; a lone setpoint attribute is not sufficient to permit writing. iT500/RT310i readings and main climate controls are checked against both bundled Android apps and offline protocol tests, **not verified with live accounts or physical gateways**. iT500 hot-water modes and boost are implemented only when the observed Cxx attributes are reported. The Android apps have additional features that this integration does **not** implement, including editing weekly schedules, holiday settings, frost threshold, energy saving, and changing the gateway's global heat/cool setting. This is not a claim of complete mobile-app feature parity.

The legacy heating-history entity IDs are retained for zone one, but their old inconsistent timers are replaced by a shared **estimated relay runtime** tracker. Readings cannot reconstruct historic heating from before the new tracker was installed. For unknown devices with no heating-zone attributes, only the cloud status/capability entity is created. This prevents unrelated products from being misrepresented as thermostats.

## Validation

Run `PYTHONPATH=tests python3 -m unittest discover -s tests -v` and `python3 tools/check_repository.py`. For test methodology see [VALIDATION.md](VALIDATION.md). The package includes its original MIT license and attribution to the upstream Arrayent client.
