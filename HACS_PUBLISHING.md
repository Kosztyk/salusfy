# HACS publishing status — Salusfy v1.2.4

- **New HACS domain:** `salus_cloud_native`, installation path `custom_components/salus_cloud_native/`, display name **Salus Cloud Native**.
- **Why:** [Frenck's domain collision review](https://github.com/hacs/default/pull/12460#pullrequestreview-5777744377) identified that the old domain `salus` conflicts with the separate default-catalog `homeassistant_salus` integration.
- **New release:** [v1.2.4](https://github.com/Kosztyk/salusfy/releases/tag/v1.2.4) (only after CI validates and publishes it). Validation URLs for v1.2.3 do **not** demonstrate that v1.2.4 passed.
- **Previous validated version:** [v1.2.3](https://github.com/Kosztyk/salusfy/releases/tag/v1.2.3), [HACS](https://github.com/Kosztyk/salusfy/actions/runs/41801908938/job/126479466012), [Hassfest](https://github.com/Kosztyk/salusfy/actions/runs/41801908938/job/126479465741), [packaging](https://github.com/Kosztyk/salusfy/actions/runs/41801908938/job/126479466066).
- **PR:** [hacs/default #12460](https://github.com/hacs/default/pull/12460). Update PR links once v1.2.4 checks and release exist, then mark the draft ready for review as requested.
- **Existing installations:** See [README migration instructions](README.md#existing-salus-installations--required-manual-migration). The new domain does not automatically migrate old `salus` entries or preserve registry associations.

## Real-device testing evidence

**RT310i operation with the supplied v1.2.2 build was successfully confirmed by a real device owner** in [issue #8](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410): “Wow, thank you for the fast answer. Works perfect.” The README, changelog, audit and validation notes now link this evidence explicitly.

**SALUS iT500, firmware 11.7:** repository maintainer and device owner `Kosztyk` confirmed successful real-device testing of **all implemented controls**, including zone-one and zone-two setpoints, operating modes and scheduled overrides, plus hot-water mode and boost. This confirmation was recorded on November 2, 2026. The [iT500 owner test report](VALIDATION.md#successful-real-device-test-it500) records successful `A85/A88/A89/A92`, `B85/B88/B89/B92`, `C42` and `C43` controls, including the paths specifically raised by the reviewer.

The documentation now records both real-device reports separately from static APK analysis and offline tests. No raw iT500 write trace has been supplied; the hardware evidence is an owner confirmation, not a published command capture. See [source provenance](SOURCE_PROVENANCE.md) for the original fork and MIT-client licensing scope. Reviewers can assess the linked confirmations for the retained controls. These reports do not claim universal coverage of other models/firmware; any newly added write path needs its own confirmation.

## For future releases

1. Update `custom_components/salus_cloud_native/manifest.json`, changelog, release notes and the release workflow's permitted version.
2. Validate locally (Python 3.12+ and `aiohttp`) and push the changes to `main`.
3. Confirm HACS, Hassfest, and the packaging/test jobs all succeed on the release commit, with no ignored checks.
4. Publish a GitHub release from that exact validated commit.
5. If the default HACS catalog request is still open, update the existing PR #12460 description with the current release and successful validation job URLs. **Do not open a duplicate PR or request a review.** Follow maintainer directions and avoid unsolicited PR comments.

The catalog pull request is not a release deployment mechanism; users can install from this repository as a HACS custom repository while catalog inclusion is pending.
