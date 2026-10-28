# HACS publishing status — Salusfy v1.2.2

- Latest published integration release: [v1.2.2](https://github.com/Kosztyk/salusfy/releases/tag/v1.2.2), released October 28, 2026.
- Default HACS catalog request: [hacs/default PR #12460](https://github.com/hacs/default/pull/12460), open and awaiting maintainer review.
- Validated release commit: `0801b96fa73881fcaa85f976db82375697070c2d`.
- [HACS Validation](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540056): passed.
- [Hassfest Validation](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540637): passed.
- [Packaging and Python checks](https://github.com/Kosztyk/salusfy/actions/runs/40739951685/job/122998540616): passed (90 offline tests).

## For future releases

1. Update `custom_components/salus/manifest.json`, changelog, release notes and the release workflow's permitted version.
2. Validate locally (Python 3.12+ and `aiohttp`) and push the changes to `main`.
3. Confirm HACS, Hassfest, and the packaging/test jobs all succeed on the release commit, with no ignored checks.
4. Publish a GitHub release from that exact validated commit.
5. If the default HACS catalog request is still open, update the existing PR #12460 description with the current release and successful validation job URLs. **Do not open a duplicate PR or request a review.** Follow maintainer directions and avoid unsolicited PR comments.

The catalog pull request is not a release deployment mechanism; users can install from this repository as a HACS custom repository while catalog inclusion is pending.
