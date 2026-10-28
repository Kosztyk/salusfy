# Salusfy v1.2.2 — multi-model compatibility and device UI

- Fixed RT310i discovery regression by eliminating `typeId == "1"` filtering in both setup and existing entry selection.
- Device type IDs discovered from Arrayent are included as `deviceTypeId` in attribute requests, matching the RT310i Android SDK.
- `SRT` RT310i and `STA` iT500 device-name selection supported without whitelisting either prefix; any registered Arrayent device can be selected.
- Zone-one and zone-two thermostats are discovered by their actual A/B attribute families. Existing zone-one entity unique IDs and credentials are preserved. Separate B-zone climate, temperature, and relay entities are created when supported.
- Temperature changes in schedule mode activate temporary override via A88/B88, and manual/schedule/off mode writes use the expected A92/A88/A89 (or B equivalents) attributes.
- A93 manual-mode target is now read, surfaced through climate attributes and a dedicated sensor, and used as a fallback only in manual mode. The Android app uses A85 for normal setpoint commands; no speculative A93 write was introduced.
- Adds C42/C45 hot-water status plus iT500 APK-verified C42 Schedule/Once/On/Off selection and C43 0–3-hour boost control when present; unknown device types remain visible without inferred controls.
- Preserves cloud auth renewal, request timeouts, serialized writes, server acknowledgments, and non-optimistic confirmation.
- Set maximum target temperature to 35°C according to iT500 and RT310i product documentation.
- Cross-checked against the iT500 Plus 2.2.1 APK: correct both apps' refresh from F=60 to F=1; correct A92/A89 Manual-to-Off state transitions and A88 scheduled-override decoding; use S06 gateway topology, exclude A84/B84 nonnumeric marker values, and report S05 cooling action.
- Expanded offline regression suite from 44 to 90 tests for mobile-API compatibility, device registration, batteries, relay-based histories, and unknown models.

**Device UI and sensor audit (revised local v1.2.2 build):** All entities use native Home Assistant device metadata based on the stable Arrayent device ID. The climate entity is the main feature, additional entities use concise device-relative names, and the same device groups temperature, mode, relay, optional hot water and diagnostics. Both APKs define battery status `S03`; confirmed app image mapping is `0 = full/normal`, `1 = low`, `2 = very low`. A battery status sensor and low-battery binary sensor are added conditionally, with no fabricated percentage. Zone frost flags `A90/B90` are conditionally exposed. Corrected the hot-water mode sensor to return decoded names rather than raw C42 integers; corrected cloud presence to be unknown when the cloud does not report it. Replaced incorrect independent heater-history timers with a shared, bounded, restored sample-based A87 relay runtime estimator that resets at local day/month boundaries and does not extrapolate through offline gaps. Previous unique IDs are preserved wherever possible. See `HOW_TO_MANUAL_INSTALL.md`.

**Compatibility:** A user has confirmed that the updated integration works with their previously missing RT310i. Other device models and firmware variants may have additional unverified cloud capabilities; unfamiliar models remain read-only until their controls are verified.
