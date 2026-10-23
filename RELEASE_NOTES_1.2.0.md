# Salusfy 1.2.0

- Use the iT500 Plus mobile app's HTTPS authentication and Arrayent API instead of the unavailable salus-it500.com website.
- Reuse existing account settings and entity registry identities; discover thermostats during setup and Configure.
- Renew expired security tokens, bound requests and retries, and request reauthentication for rejected credentials.
- Share cloud polling between thermostat, temperature and heating-output entities. Read heating output from the reported relay instead of comparing temperatures.
- Handle missing temperatures as unavailable and tolerate unavailable restored history values.
- Check command acknowledgements and fresh reported values. Expose Heat, Off and Auto modes through the mobile API.

Update through HACS and restart Home Assistant. Your existing integration entry is reused. If SALUS requests authentication, enter the same email and password that work in iT500 Plus.

Validation uses simulated HTTP/API responses and Home Assistant interface stubs. No account credentials are included in tests, and real thermostat login and commands still require verification on the installed update.
