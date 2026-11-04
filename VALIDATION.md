# Validation notes — 1.2.3

Run these checks in the project root (Python 3.12+, aiohttp installed):

```sh
python3 tools/check_repository.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components/salus
```

The 90 tests exercise Arrayent authentication and token renewal, namespace-aware XML parsing, discovery without a device type whitelist (including SRT), device-specific `deviceTypeId` in read requests, account/device selection and reauth, iT500 and RT310i zone attributes, A93 manual setpoint display behavior, zone-two control routing, schedule override A88 behavior, server acknowledgment/readback, command failure, and safe refusal of unknown-device controls.

Attributes and command paths were cross-checked against the supplied **RT310i 2.2.1** and **iT500 Plus 2.2.1** Android APKs. The iT500 APK's `HeatZone.getDeviceRunningMode` and `SalusDevice.setDeviceMode` clarify mode precedence and state clearing. Both `HeatingActivity.sendF` methods use `F=1`. The iT500 constants identify S06 topology, S05 heating/cooling status, C42 hot-water values, and C43 0–3-hour boost. The new tests exercise these cases as well as the corrected state decoder. The Arrayent public API specifies `deviceTypeId` for `getDeviceAttributesWithValues`. The Android app's normal setpoint request writes A85 plus A88 in scheduled mode; it does not directly write A93 in that path.

**Offline testing limits:** All HTTP and Home Assistant behavior in the automated suite is simulated. The suite is **not** a live account test or firmware acceptance test. Separate successful real-device owner reports for RT310i and iT500 firmware 11.7 are documented below. Those reports are distinct from the automated suite. The published v1.2.2 release commit (`0801b96fa73881fcaa85f976db82375697070c2d`) passed the [HACS](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540056), [Hassfest](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540637), and [packaging/Python](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540616) GitHub jobs.

Security: Never include credentials or account/device identifiers in shared issue reports. The cloud API requires MD5 credentials for its legacy protocol; the integration keeps credentials in Home Assistant's config entry and does not log them.

## v1.2.3 release scope and prior validation

The v1.2.3 release includes the documentation corrections and source-provenance disclosure missing from the tagged v1.2.2 archive. Thermostat behavior remains unchanged. The historical v1.2.2 CI checks listed above are not a claim that the new commit has already passed CI; new release validation must be checked on GitHub Actions.

## v1.2.2 release validation

The 90 offline regression tests cover RT310i, iT500, battery indications, native device registry metadata, and runtime/history rollovers. These are simulated API checks, not an exhaustive hardware certification. GitHub Actions HACS and hassfest validations run on publication.

## Successful real-device test: RT310i

In [issue #8 — “Do not work with RT310i anymore”](https://github.com/Kosztyk/salusfy/issues/8), `bthamburg` reported a discovery regression, installed the supplied v1.2.2 build, and [confirmed on October 28, 2026](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410):

> Wow, thank you for the fast answer. Works perfect.

**This is a successful real-device RT310i report.** It is the independent owner's general confirmation of the supplied build. The separate iT500 confirmation below covers iT500 controls.

## Successful real-device test: iT500

- **Tester:** `Kosztyk`, repository maintainer and owner of the tested device.
- **Device:** iT500 by SALUS.
- **Firmware:** 11.7.
- **Confirmation recorded:** November 2, 2026.
- **Result:** the owner confirms that **all implemented controls were tested successfully on the real device**.

| Implemented control | Write attributes | Owner-confirmed result |
| --- | --- | --- |
| Zone-one setpoint, scheduled override and operating modes | `A85`, `A88`, `A89`, `A92` | Successful |
| Zone-two setpoint, scheduled override and operating modes | `B85`, `B88`, `B89`, `B92` | Successful |
| Hot-water Schedule / Once / On / Off | `C42` | Successful |
| Hot-water boost | `C43` | Successful |

This records the maintainer/device owner's explicit confirmation, including all write paths raised in the [HACS review](https://github.com/hacs/default/pull/12460#pullrequestreview-5737333271). It is real-device feedback in addition to APK analysis and offline tests. No raw protocol captures or per-command acknowledgment/readback logs are attached to this report; automated-test results are not presented as hardware tests. The confirmation applies to the owner's reported iT500 firmware 11.7 setup and is not a claim that every SALUS device or firmware has been tested.
