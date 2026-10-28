# Validation notes — 1.2.2

Run these checks in the project root (Python 3.12+, aiohttp installed):

```sh
python3 tools/check_repository.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components/salus
```

The 90 tests exercise Arrayent authentication and token renewal, namespace-aware XML parsing, discovery without a device type whitelist (including SRT), device-specific `deviceTypeId` in read requests, account/device selection and reauth, iT500 and RT310i zone attributes, A93 manual setpoint display behavior, zone-two control routing, schedule override A88 behavior, server acknowledgment/readback, command failure, and safe refusal of unknown-device controls.

Attributes and command paths were cross-checked against the supplied **RT310i 2.2.1** and **iT500 Plus 2.2.1** Android APKs. The iT500 APK's `HeatZone.getDeviceRunningMode` and `SalusDevice.setDeviceMode` clarify mode precedence and state clearing. Both `HeatingActivity.sendF` methods use `F=1`. The iT500 constants identify S06 topology, S05 heating/cooling status, C42 hot-water values, and C43 0–3-hour boost. The new tests exercise these cases as well as the corrected state decoder. The Arrayent public API specifies `deviceTypeId` for `getDeviceAttributesWithValues`. The Android app's normal setpoint request writes A85 plus A88 in scheduled mode; it does not directly write A93 in that path.

**Testing limits:** All HTTP and Home Assistant behavior here is simulated. This is **not** a live account test, a firmware acceptance test or a substitute for validation on physical RT310i and iT500 devices. HACS/hassfest validation workflows have not been run on GitHub for this local build.

Security: Never include credentials or account/device identifiers in shared issue reports. The cloud API requires MD5 credentials for its legacy protocol; the integration keeps credentials in Home Assistant's config entry and does not log them.

## v1.2.2 release validation

The 90 offline regression tests cover RT310i, iT500, battery indications, native device registry metadata, and runtime/history rollovers. These are simulated API checks, not an exhaustive hardware certification. RT310i compatibility has been confirmed by at least one integration user. GitHub Actions HACS and hassfest validations run on publication.
