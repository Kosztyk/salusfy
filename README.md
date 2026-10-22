# Salus Thermostat (Salusfy)

Unofficial Home Assistant integration for compatible Salus iT500 / RT301i devices using https://salus-it500.com. It provides a thermostat (climate entity), heating status, temperature and history sensors. Connection to the Salus service is required.

## HACS installation

Until this repository is accepted into the default HACS catalog, open **HACS → Custom repositories**, enter `https://github.com/Kosztyk/salusfy`, choose **Integration**, install **Salus thermostat**, and restart Home Assistant.

After inclusion in the default HACS catalog, the repository can be found through HACS search.

## Manual installation

Copy the complete **`custom_components/salus`** directory to `/config/custom_components/salus/`, and restart Home Assistant. The integration's Home Assistant domain is **`salus`**, not `salusfy`.

## Configure in the Home Assistant UI

Open **Settings → Devices & services → Add integration**, search for **Salus thermostat**, and enter the Salus service email, password and device ID. You can later change these using the integration's Configure/options flow.

### Find your device ID

1. Sign in to https://salus-it500.com using your Salus credentials.
2. Select your device.
3. Copy the device ID from the device page URL.

**Note:** Earlier documentation included a `climate: - platform: salusfy` YAML configuration and a `salusfy` folder. Those instructions are obsolete for this version: use the UI configuration flow and the `salus` directory.

## Known limitations

The Salus service may rate-limit or block repeated requests from an IP address. Do not configure excessive polling.

Some sensor entity IDs in this integration assume the default `climate.salus_thermostat` name. Renaming the climate entity can affect these derived sensors. The included CI checks verify packaging and metadata; they do not connect to the live Salus cloud or exercise a thermostat.

## Validation and license

See [VALIDATION.md](VALIDATION.md) for CI scope. Licensed under [MIT](LICENSE.txt); the [original Romanian translation](docs/licenta-originala-ro.md) is retained.
