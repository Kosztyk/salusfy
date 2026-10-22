# Validation notes

The Validate Salusfy GitHub workflow runs HACS validation (with no ignored checks), Hassfest validation, static package checks, and Python compilation.

Run locally:

```sh
python3 tools/check_repository.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components
```

These checks do not log in to the Salus cloud, test control commands on real thermostats, or validate runtime behavior. Keep credentials and device IDs out of public logs.
