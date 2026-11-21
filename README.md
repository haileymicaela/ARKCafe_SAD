# ARKCafe_SAD

This is Team 5's GitHub for the NCR Tracking System

## SMS alerts (TextBee)

Copy the template once, then fill in the key and device ID:

```bash
cp .env.example .env
```

```ini
TEXTBEE_ENABLED=True
TEXTBEE_API_KEY=txb_your-api-key
TEXTBEE_DEVICE_ID=your-device-id
```

`.env` is ignored by Git, so the key is not committed. No terminal exports are
needed — the file is read automatically wherever Django starts.

To disable SMS, set `TEXTBEE_ENABLED=False` in `.env`. NCR creation and status
updates keep working normally.