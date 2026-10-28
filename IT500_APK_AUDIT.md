# iT500 Plus APK compatibility audit — Salusfy v1.2.2

Date: 2026-10-28. Compared `iT500+Plus_2.2.1_APKPure.xapk` and `RT310i_2.2.1_APKPure.xapk` against the integration's Arrayent client and HA entities. Analysis is static APK/DEX inspection, not a live API or device acceptance test.

## Evidence extracted from Android application code

- Both apps embed Arrayent and use `https://sal-emea-p01-api.arrayent.com/zdk/services/zamapi/`.
- `Zone1Atr` and `Zone2Atr` define `A84/B84` current temperature, `A85/B85` target, `A87/B87` output, `A88/B88` running/override, `A89/B89` option, `A92/B92` manual flag, and `A93/B93` saved manual setpoint.
- `HeatZone.getDeviceRunningMode` inspects the combination of A88, A89 and A92, with manual mode taking precedence over running option when conflicting. `SalusDevice.setDeviceMode` sends multiple attribute changes when changing modes; the previous one-attribute Off write did not reset A92 and could leave the unit in Manual mode.
- Both apps' `HeatingActivity.sendF` call uses `DevAtr.DEVICE_REFRESH` (`F`) with `value1=1`, not 60.
- iT500 `Constants`: S06 `0` single heating zone, `1` dual heating zones, `2` heating and hot water. S05 `0` heating and `1` cooling.
- iT500 `HotWaterAtr`: C42 hot-water mode, C43 boost remaining hours, C45 actual hot-water status and C46 running mode; `Constants` map C42 values 0 Schedule, 1 Once, 2 On, 3 Off, and C43 0–3 hours.
- iT500 `HotWaterActivity.setHotWaterModeCloud` sends C42; `setHotWaterBoostRemainCloud` sends C43. C45 remains read-only.
- iT500 `HeatingActivity.setDeviceZoneUI` treats A84/B84 values 5000, 7000 and 8000 as special screen placeholders, not normal temperatures.

## Corrections and safeguards

1. Keep unrestricted Arrayent account-device discovery and send each device's actual `deviceTypeId` when requesting its attributes.
2. Send F=1 on recognized heating commands; preserve serial writes and wait for a new server report.
3. Fix A92 / A89 manual-versus-off precedence and clear manual/override flags when switching Off.
4. Derive A/B heating zones from attributes, constrained by S06 when present, without a device model whitelist.
5. Treat special iT500 temperature values as unavailable, rather than publishing false high temperatures.
6. Display cooling action if S05 indicates cooling, without writing S05 automatically.
7. Add hot-water select (C42) and boost number (C43), only where supported. Existing C45 binary output is retained.
8. Prevent control writes for devices that only expose an unfamiliar A85 setpoint without the complete verified operating-mode contract.
9. Keep A93/B93 read-only: the supplied APK's ordinary set-temperature requests send A85/B85, plus A88/B88 in scheduled mode, not A93/B93 directly.

## Limitations

The added tests use controlled API responses and HA interface stubs. The apps provide further capabilities (weekly schedules, holiday settings, frost/energy controls and global heating/cooling configuration), which are not claimed as implemented. Other SALUS cloud ecosystems and devices lacking the verified Arrayent attribute contract cannot be automatically controlled. Before public HACS release, test one RT310i and representative iT500 configurations (single heating, dual zone and heating + hot water), including actual write acknowledgments and readback.

## Battery status, Home Assistant devices, and sensor consistency audit

Both APKs have `DevAtr.DEVICE_BATTERY = S03`. Static disassembly of `DeviceDetail.getBatteryLevelResId` and its `R$drawable` constants confirms that raw `0` maps to `dev_battery_full`, `1` to `dev_battery_low`, and `2` to `dev_battery_very_low`. The UI exposes only categories, **not a percent charge**. Other values are treated as unavailable. The same app constants define `A90/B90` as frost-state flags.

Device registration is purely a Home Assistant presentation layer: entities in one configured cloud device share `(salus, device_id)` identifiers, a SALUS manufacturer field, and the cloud device name. Existing entity unique IDs are preserved. No credential data is included.

The legacy `heater_history` family previously sampled other HA entity states on separate timers, depended on a hard-coded name, and did not properly handle midnight/month rollover or restart continuity. The revised implementation uses a shared relay-based tracker driven by the successful coordinator polls, capped to 150-second intervals, split at local midnight, with valid new-format snapshots only. Its values are **estimates**, not exact run-time statistics or kWh. Offline/unknown periods are not inferred. Heating time is not counted in cooling mode (`S05=1`).
