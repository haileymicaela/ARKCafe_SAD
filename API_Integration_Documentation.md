# TextBee SMS API Integration

**System:** Crimson NCR Tracking System  
**Integration file:** `notifications/textbee.py`  
**Base URL:** `https://api.textbee.dev/api/v1`

---

## Configuration

| Variable | Required | Where set | Purpose |
|---|---|---|---|
| `TEXTBEE_API_KEY` | Yes | `.env` in the project root, or the hosting provider's environment settings | Authenticates requests to TextBee |
| `TEXTBEE_DEVICE_ID` | Optional | Same as above | Selects the sending Android phone. If omitted, TextBee uses the account's default device. |
| `TEXTBEE_ENABLED` | Optional | Same as above | Master switch. Set to `False` to disable sending. |
| `TEXTBEE_NOTIFY_ALL_RECIPIENTS` | Optional | Same as above | `True` alerts every recipient; `False` limits alerts to the NCR's department. |
| `TEXTBEE_DEFAULT_COUNTRY_CODE` | Optional | Same as above | Country code used when converting local numbers. Default `63` for the Philippines. |

`.env` is read by `config/settings.py` when Django starts. Real environment variables take priority over `.env`. On a deployed server, set these in the hosting provider's environment-variable settings instead of relying on a local file.

```ini
TEXTBEE_ENABLED=True
TEXTBEE_API_KEY=txb_your-api-key
TEXTBEE_DEVICE_ID=your-device-id
```

> **Warning:** Do not commit `.env` or paste the API key into source code, screenshots, or Git history. `.env` is listed in `.gitignore`; never use `git add -f .env`. If a key is exposed, revoke it in the TextBee dashboard and create a new one.

---

## When SMS Is Triggered

| NCR event | Who receives it | Message template |
|---|---|---|
| New NCR created | Every Alert Recipient by default | Reference, subject, cause, description |
| Status → In Progress | Every Alert Recipient by default | Reference, new status, remarks |
| Status → Resolved | Every Alert Recipient by default | Reference, new status, resolution type, resolution note, remarks |
| Status → Open (reopened) | Every Alert Recipient by default | Reference, new status, remarks |

By default, every unique number on the **Alert Recipients** page receives each alert, regardless of the NCR's department. Set `TEXTBEE_NOTIFY_ALL_RECIPIENTS=False` to send only to recipients in the NCR's department. Editing an NCR or changing attachments does not send an SMS.

**New NCR**

```text
[NCR] New NCR-2026-0001 (PRJ-001)
Subject: Cracked weld on column C4
Cause: Workmanship
Description: Weld toe crack found during visual inspection
```

**Status → In Progress**

```text
[NCR] NCR-2026-0001 (PRJ-001) is now In Progress.
Remarks: Crew assigned; work starts tomorrow.
```

**Status → Resolved**

```text
[NCR] NCR-2026-0001 (PRJ-001) is now Resolved.
Resolution type: Replaced
Resolution note: Defective weld cut out and re-welded.
Remarks: Re-inspection passed.
```

**Status → Open (reopened)**

```text
[NCR] NCR-2026-0001 (PRJ-001) is now Open.
Remarks: Reopened (previous resolution: Closed). Defect returned.
```

Blank fields are omitted from the SMS. For example, a new NCR without a description sends only the reference, subject, and cause. A status update without remarks ends with `Changed from <previous status>.` instead of a `Remarks:` line.

---

## URL: `POST /gateway/send-sms`

**Description:** Sends an NCR alert through the registered TextBee Android phone. The system calls this endpoint after an NCR is created or its status changes.

**Full URL:** `https://api.textbee.dev/api/v1/gateway/send-sms`

### Headers

| Header | Required | Description |
|---|---|---|
| `x-api-key` | Yes | TextBee API key from the dashboard |
| `Content-Type` | Yes | `application/json` |
| `User-Agent` | No | Any non-empty value; the default Python user agent is blocked |

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | SMS content. Long text is split into multiple segments by TextBee. |
| `recipients` | string[] | Yes | Phone numbers in international format, e.g. `+639171234567`. Each recipient counts as one message. |
| `deviceId` | string | No | ID of the sending phone. If omitted, TextBee uses the account's default device. |
| `simSlotIndex` | number | No | SIM slot on a dual-SIM phone: `0` = SIM 1, `1` = SIM 2. |
| `scheduledAt` | string | No | ISO 8601 time up to 72 hours ahead. This system sends immediately and does not use it. |

### Example Request

```bash
curl -X POST "https://api.textbee.dev/api/v1/gateway/send-sms" \
  -H "x-api-key: $TEXTBEE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": ["+639171234567"],
    "message": "[NCR] New NCR-2026-0001 (PRJ-001)\nSubject: Cracked weld on column C4\nCause: Workmanship\nDescription: Weld toe crack found during visual inspection",
    "deviceId": "6b01a43696bbd64a70ee49d3"
  }'
```

### Example Response

**Status:** `200 OK` (not `201 Created`)

```json
{
  "data": {
    "success": true,
    "message": "SMS added to queue for processing",
    "smsBatchId": "66b1f2c3a4d5e6f7a8b9c0d2",
    "recipientCount": 1
  }
}
```

> A `200` response means TextBee queued the message, not that the carrier delivered it. Delivery is confirmed in the TextBee dashboard.

---

## URL: `GET /gateway/devices`

**Description:** Verifies the API key and lists the Android phones on the account. The system uses this to check that the configured `TEXTBEE_DEVICE_ID` exists and is enabled.

**Full URL:** `https://api.textbee.dev/api/v1/gateway/devices`

### Headers

| Header | Required | Description |
|---|---|---|
| `x-api-key` | Yes | TextBee API key from the dashboard |

### Request Body

None.

### Example Request

```bash
curl "https://api.textbee.dev/api/v1/gateway/devices" \
  -H "x-api-key: $TEXTBEE_API_KEY"
```

### Example Response

```json
{
  "data": [
    {
      "_id": "6b01a43696bbd64a70ee49d3",
      "name": "vivo V2417",
      "enabled": true,
      "isDefault": true,
      "lastHeartbeat": "2026-11-21T14:32:01.344Z"
    }
  ]
}
```

> If `TEXTBEE_DEVICE_ID` is not in this list, SMS requests fail with `Device not found`.

---

## Error Codes

| Code | Message | Description |
|---|---|---|
| `400` | Bad Request | No enabled device, device disabled, invalid recipient, unverified account email, or the message could not be pushed to the phone. |
| `401` | Unauthorized | API key is missing, invalid, or revoked. |
| `404` | Not Found | The requested device or resource does not exist. |
| `429` | Too Many Requests | Daily, monthly, or per-batch plan limit reached. Nothing was sent. |

### Example Error Response (401)

**Status:** `401 Unauthorized`

```json
{
  "error": "Unauthorized",
  "code": "AUTH_INVALID"
}
```

### Example Error Response (400)

**Status:** `400 Bad Request`

```json
{
  "success": false,
  "error": "Invalid recipients: \"ABC\". A recipient must be a phone number or short code. Text such as a sender name or email cannot receive SMS."
}
```

---

## Error Handling

`notifications/textbee.py` and `notifications/services.py` handle failures as follows:

- `send_sms()` raises `TextBeeError` for HTTP 4xx/5xx responses, network/timeout errors, or an invalid JSON response.
- `_send_to_all()` catches `TextBeeError` for each recipient, logs the failure with `logger.exception`, and continues with the next recipient. One bad number does not stop the others.
- There is no automatic retry. A failed message is not sent later.
- Sending runs inside `transaction.on_commit`, after the NCR has been saved. An SMS failure never blocks or rolls back NCR creation or a status update.
- `TEXTBEE_ENABLED=False` or a missing API key skips the HTTP call and logs a warning.
- A `200` response means the message was queued by TextBee, not that the carrier delivered it.

Example server log entries:

```text
TextBee SMS failed for NCR-2026-0042 (***4567)
notifications.textbee.TextBeeError: Unauthorized (AUTH_INVALID)
```

```text
TEXTBEE_API_KEY is not set; SMS not sent
```

---

## Phone Number Format

Alert Recipient numbers are stored as 11-digit Philippine local numbers, for example `09171234567`. The code converts them automatically to international format before calling TextBee through `normalize_phone_number()` in `notifications/textbee.py`.

| Stored number | Number sent to TextBee |
|---|---|
| `09171234567` | `+639171234567` |
| `639171234567` | `+639171234567` |
| `+639171234567` | `+639171234567` |
| `0917 123 4567` | `+639171234567` |

No manual conversion is needed for Philippine numbers. If recipients are in another country, set `TEXTBEE_DEFAULT_COUNTRY_CODE` to that country's code.

---

## Rate Limits

| Limit | Value |
|---|---|
| Messages per day | Plan-dependent |
| Messages per month | Plan-dependent |
| Recipients per batch | Plan-dependent |

**Note:** Each recipient counts as one message. Limits are account-wide and enforced by TextBee. A `429` means the limit is reached; wait for the reset or upgrade the plan. Reading devices or messages does not consume the send quota.

---

## Testing

1. Verify the API key and list devices first:

   ```bash
   python manage.py check_textbee
   ```

   This calls `GET /gateway/devices`. Confirm the configured `TEXTBEE_DEVICE_ID` appears and `enabled=True`.

2. Send a test SMS:

   ```bash
   python manage.py send_test_sms 09171234567
   ```

   This calls `POST /gateway/send-sms`. A successful result looks like `Queued batch ... for 1 recipient(s)`.

3. Confirm delivery in the TextBee dashboard under **Messages** (`pending → sent → delivered`).

> Django tests mock the SMS sender and never call TextBee. Use the two commands above to verify a real configuration.

---

## Support

For TextBee API questions, see the [TextBee documentation](https://textbee.dev/docs) or contact TextBee at [textbee.dev](https://textbee.dev).

For this system's integration code, contact the ARKCafe / Team 5 maintainers.
