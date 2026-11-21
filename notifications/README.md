# SMS notifications (TextBee)

This app sends NCR alerts through [TextBee](https://textbee.dev), which turns an
Android phone into an SMS gateway.

## What is sent

| Event | SMS content | Recipients |
| --- | --- | --- |
| NCR created | Reference, subject, cause | Every Alert Recipient |
| Status -> In Progress | Reference, new status, remarks | Every Alert Recipient |
| Status -> Resolved | Reference, new status, resolution type, resolution note, remarks | Every Alert Recipient |
| Status -> Open (reopened) | Reference, new status, remarks | Every Alert Recipient |

Set `TEXTBEE_NOTIFY_ALL_RECIPIENTS=False` to instead send only to recipients
in the NCR's responsible department.

Messages are sent after the database transaction commits, so a failed SMS can
never roll back or break an NCR save.

## Setup

1. Create an account at <https://app.textbee.dev>, install the Android app, and
   register the phone (the device must stay online with SMS permission).
2. Create an API key in the dashboard.
3. Create a `.env` file in the project root (copy `.env.example`) and fill in
   the values. This works from any terminal or IDE without exports:
   ```bash
   cp .env.example .env
   ```
   ```ini
   TEXTBEE_ENABLED=True
   TEXTBEE_API_KEY=txb_your-api-key
   TEXTBEE_DEVICE_ID=your-device-id
   ```
   `.env` is ignored by Git, so the key is not committed. Real environment
   variables still take priority over `.env`.

   Prefer terminal variables? Use `$env:...` in PowerShell or `export ...` in
   Bash instead — both work the same way.

4. Verify the key and device list, then send a test SMS:
   ```bash
   python manage.py check_textbee
   python manage.py send_test_sms 09171234567
   ```

Without `TEXTBEE_API_KEY` the app logs a warning and skips sending; NCRs still
work normally.

## Configuration

| Setting | Env var | Default |
| --- | --- | --- |
| Enable SMS | `TEXTBEE_ENABLED` | `True` |
| API key | `TEXTBEE_API_KEY` | empty |
| API base URL | `TEXTBEE_BASE_URL` | `https://api.textbee.dev/api/v1` |
| Sending device | `TEXTBEE_DEVICE_ID` | default device |
| Request timeout (s) | `TEXTBEE_TIMEOUT` | `15` |
| Country code for local numbers | `TEXTBEE_DEFAULT_COUNTRY_CODE` | `63` |
| SMS prefix | `TEXTBEE_MESSAGE_PREFIX` | `[NCR]` |
| Alert every recipient | `TEXTBEE_NOTIFY_ALL_RECIPIENTS` | `True` |
| Log instead of send | `TEXTBEE_DRY_RUN` | `False` |

Phone numbers are normalized to international format: `09171234567` becomes
`+639171234567`. Messages longer than 480 characters are truncated.

## Code layout

- `textbee.py` - HTTP client (`send_sms`), errors, phone normalization.
- `messages.py` - SMS wording for each event.
- `services.py` - recipient lookup + event handlers called by `ncr.services`.
- `ncr/hooks.py` - the seam the NCR app imports.
