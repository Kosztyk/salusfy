# Source provenance and licensing audit — Salusfy v1.2.4

**Original source audit:** November 4, 2026; domain-rename update November 5, 2026. This document identifies the source of code in the **current installable integration**. It is not a claim about all historical commits in this GitHub fork, nor an assertion of permission from any unrelated upstream author.

## What was compared

- Unlicensed original: [`floringhimie/salusfy`](https://github.com/floringhimie/salusfy), `main` at [`91bc890`](https://github.com/floringhimie/salusfy/commit/91bc89010b62f05995209ce621432518f17d810b), with `README.md`, `custom_components/salusfy/__init__.py`, `climate.py` and `manifest.json`.
- Current fork before this audit: [`Kosztyk/salusfy`](https://github.com/Kosztyk/salusfy), `main` at [`9f60a39`](https://github.com/Kosztyk/salusfy/commit/9f60a39a9eb4676876a1b63f776b1cb23a15a98d). The v1.2.3 installable integration was `custom_components/salus/`; in v1.2.4 it is `custom_components/salus_cloud_native/`, not the unlicensed upstream `custom_components/salusfy/`.
- The comparison examined the entire original `climate.py` against every Python module in `custom_components/salus_cloud_native/`, including exact source matches, identical nonblank lines and contiguous matches, and inspected protocol and entity implementations. Matching common Home Assistant method/property names does not establish source derivation.

## File and functionality comparison

| Original source | Current v1.2.4 package | Finding |
| --- | --- | --- |
| `custom_components/salusfy/climate.py` | `custom_components/salus_cloud_native/climate.py`, `coordinator.py`, `model.py`, `api.py` | Original synchronous `requests` and legacy `salus-it500.com` web-login/session-token, HTML scraping, PHP form payloads and thermostat control logic are absent. Modern Home Assistant coordinator, climate entities and Arrayent XML/attribute protocols replace them. Some standard Home Assistant methods (`current_temperature`, `hvac_mode`, etc.) and short statements have the same names; no substantial contiguous original implementation was found. |
| `custom_components/salusfy/__init__.py` | `custom_components/salus_cloud_native/__init__.py` | The original is only the generic docstring `The Salus component.`; the new file contains a different config-entry setup and authentication lifecycle. That short docstring remains identical, but not original executable logic. |
| `custom_components/salusfy/manifest.json` | `custom_components/salus_cloud_native/manifest.json` | Different integration domain, code owner, config flow, version and dependencies; generic metadata such as the product name and `cloud_polling` describes the same product/service category. |
| `README.md` | `README.md` and current documentation | Original legacy YAML and retired web-portal instructions are not used. Current documentation describes the separate Arrayent implementation and HA config flow. |

**Conclusion for the current shipped files:** no substantive or distinctive implementation from `floringhimie/salusfy` is retained in the current installable integration. Shared generic labels, framework API names, and the one-line `__init__.py` docstring are explicitly acknowledged. The repository remains a GitHub fork because of its historical ancestry; its past unlicensed upstream commits have **not** been relicensed.

## What is MIT-licensed and what is not

1. **Current project contribution:** The installation modules apart from the separately credited cloud-client adaptation, Home Assistant entity/capability logic, tests, docs and workflows were implemented/reworked in this project. They are offered under this repository's [`LICENSE.txt`](LICENSE.txt) MIT terms.
2. **MIT-licensed cloud-client adaptation:** [`custom_components/salus_cloud_native/api.py`](custom_components/salus_cloud_native/api.py) identifies [ZaBug/salus-it500](https://github.com/ZaBug/salus-it500) as its upstream source and notes the related `RichyA/pyit500` history. ZaBug's own [`LICENSE`](https://github.com/ZaBug/salus-it500/blob/main/LICENSE) is MIT, and its full copyright/permission notice is preserved locally in [`third_party/ZaBug-LICENSE.txt`](custom_components/salus_cloud_native/third_party/ZaBug-LICENSE.txt). This is the explicitly credited third-party client; it does not depend on a license from `floringhimie`.
3. **Unlicensed original fork parent:** [floringhimie/salusfy](https://github.com/floringhimie/salusfy) has **no declared LICENSE file**. There is no known permission grant here to relicense its original code, and `LICENSE.txt` is **not** asserted to cover that upstream's original files/history. They are excluded from the v1.2.4 installable source tree.

This audit is about identifiable source overlap, not a legal certification or proof about uninspected historical development.

## Hardware validation evidence is independent of source licensing

The [RT310i report](https://github.com/Kosztyk/salusfy/issues/8#issuecomment-6474946410) and the [iT500 firmware 11.7 owner report](VALIDATION.md#successful-real-device-test-it500) are device-operation reports, not proofs of licensing or implementation authorship. The iT500 owner reports successful writes via `A85/A88/A89/A92`, `B85/B88/B89/B92`, `C42` and `C43`. **No raw iT500 HTTP/Arrayent command capture or readback log is included**, so none is represented here as independently verified protocol evidence. Publish a sanitized, redacted capture as a follow-up only if one actually exists; never disclose credentials, session tokens, account identifiers, or device IDs.
