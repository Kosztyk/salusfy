# Validation notes

The Validate Salusfy workflow runs HACS validation, Hassfest validation, package checks, Python compilation and offline regression tests.

Run locally with Python 3.12 or later:

```sh
python3 -m pip install aiohttp
python3 tools/check_repository.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components
```

The tests exercise mobile login payloads, token renewal (including faults returned with HTTP 200), bounded retries, API acknowledgement failures, namespaced XML parsing, device selection, attribute decoding, unavailable numeric readings, existing entity unique IDs, saved credential precedence, reauthentication, and command confirmation.

HTTP responses are simulated. Flow, entity and coordinator tests use small Home Assistant interface stubs, not a full Home Assistant runtime. They do not authenticate a real account, issue real thermostat commands, or establish device/firmware compatibility. Keep credentials and device IDs out of public logs.
