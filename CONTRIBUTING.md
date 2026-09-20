# Contributing

## Local setup

```bash
python3 -m pytest
cd ui && npm install && npm run build
python3 server/app.py
```

Keep the server on loopback. Do not add cloud telemetry, account login, or a bind-to-all-interfaces option.

## Privacy rule

Do not commit:

- Home directory paths
- Usernames, hostnames, emails, or phone numbers
- API keys, tokens, cookies, or `.env` files
- GPU UUIDs, MAC addresses, or serial numbers
- Screenshots of a live HUD that show a private machine

`tests/test_privacy.py` fails the build if common personal markers appear in tracked files.

## Pull requests

Keep changes focused. Match the existing HUD tone. Update README or `docs/` when behavior changes.
