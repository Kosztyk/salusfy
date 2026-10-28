# Salusfy v1.2.2 — Manual installation / upgrade

This guide is for the **local device-UI and battery-status build** of the unofficial SALUS integration for Home Assistant. It is not a new HACS release. No GitHub publication is required.

## 1. Back up your existing installation

1. In Home Assistant, create a backup under **Settings → System → Backups**.
2. If you already use Salusfy, optionally copy `/config/custom_components/salus/` somewhere safe.
3. Do **not** remove the Salus integration from **Settings → Devices & services**: doing so can remove entity registrations and break existing dashboards/automations.

## 2. Copy the integration files

1. Download `salusfy-1.2.2-device-ui-integration.zip` and extract it on your computer.
2. Find the folder `custom_components/salus` inside the extracted archive.
3. In Home Assistant, open File Editor, Studio Code Server, Samba, or the SSH terminal.
4. Copy the entire **`salus`** folder to `/config/custom_components/salus/`, overwriting the old files. The final path must look like this:

   ```text
   /config/
   └── custom_components/
       └── salus/
           ├── __init__.py
           ├── manifest.json
           ├── api.py
           ├── climate.py
           ├── sensor.py
           ├── binary_sensor.py
           ├── device.py
           ├── runtime.py
           ├── coordinator.py
           └── ...
   ```

   **Do not** put the extracted `custom_components` folder inside another `custom_components` folder.

5. Restart **Home Assistant** from **Settings → System → Restart**. A simple integration reload may not reload modified Python modules.

### Optional SSH installation

After uploading the ZIP to `/config/`, run:

```sh
cd /config
unzip -o salusfy-1.2.2-device-ui-integration.zip 'custom_components/salus/*'
```

Restart Home Assistant afterward. Do not run `unzip` in the ZIP archive's own folder unless the extraction path is correct.

## 3. Verify the devices and entities

1. Open **Settings → Devices & services → Integrations**.
2. Open **Salus thermostat**, then select the **device** named in your SALUS mobile app. The integration now registers a Home Assistant device for the selected cloud device.
3. The device page should group its **Controls**, **Sensors**, **Binary sensors**, and supported hot-water entities. The primary climate entity uses the cloud device name; other entity names are concise.
4. Existing entity IDs/unique IDs are retained where possible. If a previously configured entity was manually renamed, Home Assistant normally keeps your custom entity ID and name.
5. If your account contains multiple SALUS cloud devices, use **Add integration → Salus thermostat** again for each additional physical device. This version creates one Home Assistant device per configured SALUS cloud device; it does not automatically add all devices in a single account entry.

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
- Open the integration's **Configure** / **Reconfigure** flow and select the correct device if several are registered.
- Confirm Internet connectivity and try **Reload** under the integration's three-dot menu.
- Look at **Settings → System → Logs** for messages containing `salus`.
- Only devices using the supported SALUS/Arrayent mobile cloud are discoverable; unknown control attribute sets remain read-only for safety.

## 6. Rollback

Restore the old `/config/custom_components/salus/` folder from the backup and restart Home Assistant. Do not delete the integration entry unless you intentionally want to reconfigure it. If you need to verify a bug report, include the model family, Home Assistant version, the integration logs with credentials removed, and the observed entity states. Never publish your SALUS account password, security tokens, or device identifiers publicly.

## Scope of validation

This v1.2.2 build was checked statically against the uploaded **iT500 Plus 2.2.1** and **RT310i 2.2.1** Android apps, and with offline integration regression tests. A live SALUS cloud account and physical thermostat were not available for end-to-end verification. Existing basic controls and historical entity identifiers have been kept, but broad SALUS hardware parity cannot be guaranteed.
