# Tarceel `message.status` webhook can't be correlated to a sent message

**Status:** open — change requested on the Tarceel product (this app is only a consumer).
**Found:** 2026-09-15, verified live against a real instance.

## Summary

The id Tarceel returns from a **send** call is not the id it reports in the
**`message.status` webhook**, and the two payloads share no common key. As a
result an integrator cannot match an incoming status event to the message it
sent, so delivery status can't be reflected back onto the originating record.

This contradicts the documented contract, which states the webhook's `data.id`
is "the message id from the original send call."

## Evidence (real instance)

Send:

```
POST /instances/{instanceId}/messages/text   { "to": "...", "text": "..." }
→ 200 { "id": "83ad449d-c6ef-49c0-97be-c08b5e452d73" }        # a UUID
```

Status webhook actually delivered for that message stream:

```json
{
  "event": "message.status",
  "instanceId": "c01d03c0-...",
  "timestamp": 1789479243426,
  "data": { "id": "3EB0C6F5BC2D50B88712F0", "status": "sent" },   // a WhatsApp WAMID
  "id": "b9b67c22-aa13-4e48-9fbb-e85fc894d9d5"                     // per-event delivery id, NOT the message id
}
```

- `data.id` in the webhook is the **WhatsApp WAMID** (`3EB0C6F5...`), not the
  UUID the send call returned.
- The top-level `id` is a **per-delivery event id** (different for every
  status event of the same message), not the message id.
- `GET /instances/{id}/messages/{uuid}/status` works **by the UUID** and returns
  `{ "id": "<uuid>", "status": "..." }` — it never exposes the WAMID.
- `GET /instances/{id}/messages/{uuid}` returns 404 (no detail route).

So there is no forward path (send → webhook) and no reverse lookup
(WAMID → UUID) available to a consumer.

## Requested change (pick one)

**Preferred — make the documented contract true.** Make the webhook's `data.id`
equal the id returned by the send call (the UUID), and expose the WAMID under a
new field:

```json
"data": { "id": "83ad449d-...", "whatsappId": "3EB0C6F5...", "status": "sent" }
```

This needs no change in any existing consumer that already follows the docs, and
makes `docs/openapi.yaml` / `docs/webhooks.md` accurate.

**Backward-compatible alternative.** Keep `data.id` as the WAMID (for any
consumer already relying on it) and **add** the send-call UUID as a new field:

```json
"data": { "id": "3EB0C6F5...", "messageId": "83ad449d-...", "status": "sent" }
```

## What this app does meanwhile

`tarceel_erpnext/webhook.py::apply_status_event` matches the log on
`data.messageId or data.id`, so it starts working automatically under **either**
option above the moment Tarceel ships it — no further change needed here. Until
then, `message.status` webhooks verify and return 200 but match no log (status
stays at "Sent").
