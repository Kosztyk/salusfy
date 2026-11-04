# Salusfy v1.2.3 — HACS review follow-up: test evidence and licensing clarity

This release ships the corrected documentation that was merged to `main` after v1.2.2 had already been published. **There are no functional thermostat control changes** from v1.2.2.

- **Physical-device evidence:** Records the owner's successful SALUS iT500 firmware 11.7 test of zone-one `A85/A88/A89/A92`, zone-two `B85/B88/B89/B92`, hot-water modes `C42`, and boost `C43`. The separate independent RT310i confirmation is also linked. These are owner-reported results, not attached raw network/acknowledgment captures.
- **Release consistency:** Updated README, changelog, validation notes, APK audit, installation guide and HACS publishing instructions are included in this release archive; the contradictory text in the older v1.2.2 release is superseded.
- **Licensing/source provenance:** [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md) documents the line/implementation comparison with the unlicensed GitHub parent `floringhimie/salusfy`. No substantive parent implementation is retained in the installable integration. The independently MIT-licensed [ZaBug/salus-it500](https://github.com/ZaBug/salus-it500) cloud-client adaptation and its preserved notice are clearly attributed. The project's MIT license is not a relicensing of historical upstream code.
- **Testing:** Offline tests and HACS/hassfest CI should be checked on the validated v1.2.3 commit; hardware test reports remain distinct from CI.

For full documentation, see [README](README.md), [VALIDATION](VALIDATION.md), and [HACS publishing status](HACS_PUBLISHING.md).
