# Salusfy v1.2.4 — Manual installation / domain migration

This guide covers **Salusfy v1.2.4**, retaining v1.2.3 controls but changing its integration domain to avoid another HACS integration. The change requires explicit reconfiguration for previous `salus` installations. Download the [latest GitHub release](https://github.com/Kosztyk/salusfy/releases/latest); the default HACS catalog listing is still pending review of [PR #12460](https://github.com/hacs/default/pull/12460).

## 1. Back up your installation

1. Make a full backup under **Settings → System → Backups**.
2. Record your current Salusfy `salus` config-entry devices, entity IDs, custom names, dashboards, automations and statistics consumers; preserve a copy of the old folder if it is owned by Salusfy.
3. Download the [v1.2.4 release](https://github.com/Kosztyk/salusfy/releases/tag/v1.2.4). **Do not use the standalone v1.2.2 ZIP** for this migration: it installs the conflicting legacy `salus` folder.

## 2. Install the new domain

The package to install is **`custom_components/salus_cloud_native/`**. In Home Assistant the destination must be:

```text
/config/custom_components/salus_cloud_native/
    __init__.py
    api.py
    climate.py
    config_flow.py
    const.py
    manifest.json
    sensor.py
    ...
```

Either update this repository through HACS (custom repository until approved) or extract its GitHub release source ZIP and copy the entire `custom_components/salus_cloud_native` directory to `/config/custom_components/`. **Do not** nest `custom_components` inside itself. Restart Home Assistant to load the new Python package.

## 3. Existing `salus` to `salus_cloud_native` migration

Changing an integration's domain is a breaking configuration change: Home Assistant does not automatically rewrite existing `salus` entries. The existing `custom_components/salus` directory also collides with the independently published `homeassistant_salus` integration.

1. Before making changes, keep your Home Assistant backup. Note the existing entity IDs and the dashboards, automations and long-term statistics that rely on them.
2. Install `salus_cloud_native` as above and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → Salus Cloud Native**. Enter the same SALUS mobile-cloud credentials and choose the same physical device; repeat for each device/account previously configured.
4. Verify the new climate, sensor, binary sensor, hot-water controls (where supported) and device grouping. Do not run both sets of thermostat-control automations simultaneously.
5. Delete the **old Salusfy `salus` config entry** from Devices & services after confirming the new entry works. Remove only an old `salus` integration folder known to belong to Salusfy. **Never delete another integration's `custom_components/salus` folder.** Restart Home Assistant.
6. Review/rename the new entity IDs after the old IDs are freed, then update dashboard cards, scripts, automation actions, history/recorder queries and energy/statistics references as needed.

**ID compatibility:** the code retains the device's cloud ID and the existing `unique_id` string formulas; however, the platform/integration domain and config entry are new. The device registry identifiers change from `("salus", device_id)` to `("salus_cloud_native", device_id)`, so Home Assistant creates a distinct device registry identity. The generated entity IDs can acquire `_2` suffixes while old entities remain. Previous entity ID assignments and historical statistics are not automatically migrated. Do **not** edit `.storage/core.config_entries` or `.storage/core.entity_registry` manually.

For entirely new installations, just install the new folder, restart Home Assistant, and add **Salus Cloud Native** once per cloud device.

## 4. What you should see

Depending on the attributes actually returned by your particular thermostat:

| Entity | Source | Meaning |
| --- | --- | --- |
| Climate | A84/A85/A88/A89/A92 | Room temperature, active setpoint and supported operating modes |
| Current temperature | A84 | Actual reported room temperature |
| Target temperature | A85 | Active target (not saved manual target) |
| Saved manual temperature | A93 | Manual-mode saved setpoint, read-only |
| Heating output | A87 | Actual heating relay status; not estimated from temperature difference |
| Frost protection active | A90 | Reported frost-protection state, if present |
| Operating mode | A88/A89/A92 | Schedule, manual, off, or temporary override |
| Battery status | S03 | `0` Normal, `1` Low, `2` Very low |
| Battery low | S03 | On for Low/Very low; off for Normal |
| Zone 2 | Bxx | Independent second heating zone, if configured |
| Hot-water mode/boost/output | C42/C43/C45 | For compatible iT500 hot-water configurations |
| Cloud status | Online/presence | Cloud connectivity and diagnostic capabilities |
| Heating runtime | A87 | Approximate heating hours based on samples |

**Battery percentage is not available** from the verified mobile-app attribute set. The integration intentionally does not fabricate a percentage. Battery entities are created only if `S03` is reported.

**Heating-runtime warning:** The app reports a relay state, not a precise timestamped heating event history. Runtime totals are therefore *sample-based estimates*. They skip long missing/offline intervals and cannot reconstruct pre-installation history. When migrating from the older inaccurate history code, the new history tracker starts fresh unless a valid new-format snapshot exists. Historical energy use is not measured.

## 5. RT310i missing or controls unavailable?

- Confirm the thermostat is still visible in the official SALUS mobile app and in the account used for Home Assistant.
- Open **Salus Cloud Native** integration's **Configure** / **Reconfigure** flow and select the correct device if several are registered.
- Confirm Internet connectivity and try **Reload** under the integration's three-dot menu.
- Look at **Settings → System → Logs** for messages containing `salus`.
- Only devices using the supported SALUS/Arrayent mobile cloud are discoverable; unknown control attribute sets remain read-only for safety.

## 6. Rollback

To roll back, restore your full Home Assistant backup and previous Salusfy `salus` package/config entry together, or reinstall a known working older release and re-add its legacy entry. **Do not overwrite or delete another integration that uses `custom_components/salus/`.** Undo any entity-ID/dashboard changes separately if required. When reporting issues, include model and Home Assistant versions and redacted logs; never share account passwords, tokens or device identifiers.

## Scope of validation

The v1.2.4 release retains the v1.2.3 control implementation, which was checked statically against the uploaded **iT500 Plus 2.2.1** and **RT310i 2.2.1** Android apps, and with offline integration regression tests. **A real RT310i owner also confirmed successful operation:** after installing the supplied v1.2.2 build for [issue #8](https://github.com/Kosztyk/salusfy/issues/8), `bthamburg` [reported on October 28, 2026](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410): “Wow, thank you for the fast answer. Works perfect.”

**SALUS iT500, firmware 11.7:** repository maintainer and device owner `Kosztyk` confirmed successful real-device testing of **all implemented controls**, including zone-one and zone-two setpoints, operating modes and scheduled overrides, plus hot-water mode and boost. This confirmation was recorded on November 2, 2026. The [validation notes](VALIDATION.md#successful-real-device-test-it500) record the successful setpoint/mode/override, zone-two, hot-water mode and boost paths explicitly. The RT310i and iT500 reports are separate real-device evidence in addition to the offline tests. Existing basic controls and historical entity identifiers have been kept; these confirmations do not imply that every SALUS model or firmware has been tested.
