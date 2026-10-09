# Stay4S Gateway / Companion V3 Implementation

## Scope

This branch adds API endpoints and PWA features to the existing Gateway v3/PWA v2 sources. It is a review branch; it has **not** been deployed to production by this change.

## Gateway routes added

- `POST /v1/video`: authenticated proxy to `VIDEO_API_URL` (defaults to `https://video.stay4s.com/generate`).
- `POST /v1/voice`: authenticated multipart audio transcription proxy to a configured Whisper-compatible endpoint.
- `GET /v1/models`: Ollama models plus explicitly configured Cloudflare Workers AI model IDs.
- `POST /v1/embed`: Ollama embeddings, default model `nomic-embed-text`.
- `WS /v1/stream`: WebSocket chat stream; authenticate with first frame `{"type":"auth","api_key":"..."}`, then send `{"prompt":"...","model":"..."}`.
- `POST /v1/scan/image`: image scam analysis using an installed Ollama vision model.
- `GET /v1/push/vapid-public-key`, `POST /v1/push/subscribe`, `POST /v1/push/test`: Web Push subscription and test.
- `POST /v1/subscribe`: Free activation or Mollie first-payment checkout for Pro/Enterprise.
- `POST /webhooks/mollie`: verifies payment status by retrieving it from Mollie, then attempts to create the recurring subscription after the first paid payment.
- `POST /v1/subscribe/claim`: one-time claim of the API key after confirmed payment; token expires after two hours.
- `GET /v1/subscribe/status/{payment_id}`: payment status only.

## Pricing and quotas

- Free: EUR 0, 20 requests per rolling 24 hours.
- Pro: EUR 49/month, 1,000 requests per rolling 24 hours.
- Enterprise: EUR 199/month, no configured daily request cap.

Quota accounting is request-based, not token-based. Enterprise still needs abuse protection, concurrency limits, and cost monitoring before broad public launch.

## Required environment variables

- `CF_API_TOKEN`
- `MOLLIE_API_KEY` (use a Mollie test key first)
- `VIDEO_API_URL` (optional override)
- `WHISPER_URL` (required to enable voice; must be a private Whisper-compatible `/asr` endpoint)
- `OLLAMA_URL` (currently defaults to localhost:11434)
- `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_VISION_MODEL` (optional)
- `CLOUDFLARE_MODELS` (comma-separated model IDs; defaults to configured chat model)
- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL` (required for Web Push)
- `MOLLIE_WEBHOOK_URL`, `PUBLIC_BASE_URL` (optional overrides)

Never commit actual provider credentials. The demo API key currently present in the legacy source/PWA should be treated as a demo credential and replaced with a real per-user key before public production.

## PWA changes

- Service worker caches the shell and supports notification display.
- Offline chat requests are queued locally and replayed when connectivity returns.
- Adds push subscription flow, photo scam scan upload, audio transcription upload, theme toggle, and NL/EN/DE UI labels.
- API key can be set in the UI and is stored in browser localStorage. This is convenient but not appropriate for shared/untrusted devices; consider a session-based auth flow before broad production use.
- Offline queue is local browser storage, not end-to-end encrypted.

## Training data

Run:

```bash
python generate_stay4s_training_data_v1.py --output stay4s_training_5000.jsonl --manifest stay4s_training_5000.manifest.json
```

It produces exactly 5,000 synthetic user/assistant records in JSONL with the requested category allocation: 2,000 math, 1,000 reasoning, 1,000 code, 500 Dutch, 500 tool-use. This is synthetic starter data and must be quality-reviewed before training; it is not a verified high-quality benchmark dataset.

## Tests

GitHub Actions runs Python syntax compilation and pytest contract/dataset tests. The tests in this branch do not replace end-to-end tests against live Ollama, Whisper, Cloudflare, Mollie, the video provider, or the browser/PWA.

## Deployment checklist

1. Back up the Pi 5 deployment and SQLite database.
2. Set env vars and install `requirements_gateway_v3.txt`.
3. Generate VAPID keys and configure private/public keys securely.
4. Configure a Whisper-compatible service and test a real audio upload.
5. Test Mollie using a test API key and test webhook delivery.
6. Verify Cloudflare routing and CORS/auth policy.
7. Deploy to staging; do not replace production before all integration tests pass.
8. Confirm subscription renewal and failure handling before accepting live payments.
