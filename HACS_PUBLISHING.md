# HACS publishing checklist

1. Validate HACS, Hassfest and packaging checks on the preparation PR.
2. Merge to main only after checks pass, then validate main.
3. Publish GitHub Release v1.1.4, created after successful validation.
4. Add `"Kosztyk/salusfy"` to the alphabetical `integration` catalog in the Kosztyk/default fork of hacs/default.
5. Open a PR to hacs/default:master using the official template. Complete the checklist and provide all **three** links from **Kosztyk/salusfy**: the v1.1.4 release, successful HACS job, and successful Hassfest job.

Do not link releases from other integrations. Do not open duplicates.
