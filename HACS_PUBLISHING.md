# HACS publishing status — Salusfy v1.2.2

- Latest published integration release: [v1.2.2](https://github.com/Kosztyk/salusfy/releases/tag/v1.2.2), released October 28, 2026.
- Default HACS catalog request: [hacs/default PR #12460](https://github.com/hacs/default/pull/12460), open as a draft after [changes requested on November 2, 2026](https://github.com/hacs/default/pull/12460#pullrequestreview-5737333271).
- Validated release commit: `0801b96fa73881fcaa85f976db82375697070c2d`.
- [HACS Validation](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540056): passed.
- [Hassfest Validation](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540637): passed.
- [Packaging and Python checks](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540616): passed (90 offline tests).

## Real-device testing evidence and remaining review requirement

**RT310i operation with the supplied v1.2.2 build was successfully confirmed by a real device owner** in [issue #8](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410): “Wow, thank you for the fast answer. Works perfect.” The README, changelog, audit and validation notes now link this evidence explicitly.

This report covers RT310i operation, not iT500 hardware or every individual command. The review already accepts the RT310i setpoint/mode scope; the outstanding requirement is to remove every unconfirmed write path from the submitted release or link the relevant iT500 owner confirmation. This includes iT500 zone-two writes and hot-water mode/boost controls. The documentation correction alone does not satisfy that requirement; the PR remains a draft pending the required evidence or code changes and a new release.

## For future releases

1. Update `custom_components/salus/manifest.json`, changelog, release notes and the release workflow's permitted version.
2. Validate locally (Python 3.12+ and `aiohttp`) and push the changes to `main`.
3. Confirm HACS, Hassfest, and the packaging/test jobs all succeed on the release commit, with no ignored checks.
4. Publish a GitHub release from that exact validated commit.
5. If the default HACS catalog request is still open, update the existing PR #12460 description with the current release and successful validation job URLs. **Do not open a duplicate PR or request a review.** Follow maintainer directions and avoid unsolicited PR comments.

The catalog pull request is not a release deployment mechanism; users can install from this repository as a HACS custom repository while catalog inclusion is pending.
