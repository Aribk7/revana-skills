---
name: revana-video
description: Make AI videos through the Revana API (api.revana.si) - Seedance 2.5, Veo 3.1, Kling, Wan, Hailuo, MiniMax, Grok Imagine, Vidu, PixVerse and 70+ more video models on one API key. Use when the user asks to make, render or generate a video, clip or animation, "make a video with seedance", "seedance 2.5 api", "veo 3 api", "kling api", "animate this image", "image to video", "text to video", wants a cheap video generation API, or asks to replace kie.ai, fal or Replicate for video.
---

# Revana video: Seedance, Veo, Kling, Wan, Hailuo on one key

Revana (https://revana.si) runs every video model behind one request shape: `POST /v1/generations`, poll, download.
Each job starts on the cheapest provider and falls back automatically. Only the route that succeeds is charged,
and a failed generation costs nothing. Credits are prepaid, 100 credits = $1.

## Rules

1. The key is in `REVANA_API_KEY` (starts `sr_live_`). If it is unset, ask the person to create one at
   https://revana.si/dashboard and `export REVANA_API_KEY=...` in their own shell. **Never print, echo, log or
   write the key into a file**, and never paste it into a command you show.
2. **Quote first.** Get the price (section 2), tell the person, and wait for a yes before anything is spent.
3. **Always send `max_cost_usd`** set to the price they agreed to, so the job can never cost more.
4. **One `Idempotency-Key` per video, made once.** Make it before the first try (`KEY=$(uuidgen)`) and note its
   value: agent shells often forget variables between commands, so reuse the literal value, never a fresh
   `$(uuidgen)`.
   - The create timed out, the connection dropped, or it answered 5xx or 429: send the same body with the
     **same** key. You get the video already started, never a second one or a second charge.
   - The video **failed** (`status: failed`): that key now always answers the failed video. To try again, make a
     **new** key.
   - The same key with a different body is refused with `409 idempotency_conflict`.

## 1. Pick a model and read its price (free, no key)

```bash
curl -s https://api.revana.si/v1/models \
  | jq '.data[] | select(.kind=="video") | {id, tasks, options, price}'
```

Common picks (check the list: models and prices change):

| Ask | Model ids |
|---|---|
| Best quality, sound, up to 30 s | `seedance-2.5` |
| Cheaper Seedance | `seedance-2.0`, `seedance-2.0-fast`, `seedance-2.0-mini` |
| Google Veo | `veo-3.1`, `veo-3.1-fast`, `veo-3.1-lite` |
| Kling | `kling-4.0`, `kling-3.0`, `kling-3.0-omni`, `kling-2.6-pro` |
| Wan | `wan-3.0`, `wan-2.6-flash`, `wan-2.7` |
| Hailuo / MiniMax | `hailuo-2.3`, `hailuo-2.3-fast`, `minimax-h3` |
| Others | `grok-imagine-video-1.5`, `vidu-q4`, `pixverse-v6`, `skyreels-v4-fast` |

Each model's options and prices are also at `https://revana.si/models/<id>` (markdown: `https://revana.si/models/<id>.md`).
For "which is cheapest", use the `revana-model-picker` skill.

## 2. Quote

Write the request body once; the quote and the create use the same one:

```bash
BODY='{"model": "seedance-2.5",
       "input": {"prompt": "a paper boat drifting down a rainy street, close up",
                 "resolution": "720p", "duration": 5, "aspect_ratio": "16:9", "audio": true}}'
```

**Ask the server** (free, creates and holds nothing). `POST /v1/generations/quote` is on API versions deployed
after 2026-10-31; an older server answers `404 not_found`, and then you price from the list instead.

```bash
curl -s https://api.revana.si/v1/generations/quote -H "Authorization: Bearer $REVANA_API_KEY" \
  -H "Content-Type: application/json" -d "$BODY" | jq '{quoted_usd, reserved_usd, enough_credit, error}'
```

**From the list.** Video prices are `per_second` of video out. `price.usd` is a number, or a map keyed by
resolution (`"720p"`), with `+audio` when sound costs extra (`"720p+audio"`) and `+video_input` when a clip goes in.

```
price = usd[key] x duration
```

Read the live price every time; prices change (they were cut on 2026-10-31). Say it plainly: "A 5-second 720p
Seedance 2.5 clip costs $X. Go ahead?" Once they agree, keep it as `PRICE=<that number>`.

**A start image can cost more than the list shows.** With `image_url` (a start frame), some models, Seedance 2.5
among them, charge a higher rate per second than the plain one in `/v1/models`. The server quote includes it; the
list does not yet. Without a server quote, say the listed price is the least it will cost and agree a cap with room
above it. A cap below the price is refused with `422 max_cost_exceeded` before anything is made or charged: then
ask again, never raise it silently. (If the Revana MCP is connected, its `get_quote` prices Seedance 2.5 on the
server today.)

Only values a model lists in `options` are accepted; anything else returns `422 invalid_input` and is free.

## 3. Generate

With the CLI (Node 18+), at the agreed price:

```bash
npx revana generate seedance-2.5 "a paper boat drifting down a rainy street, close up" \
  --duration 5 --resolution 720p --aspect 16:9 --audio --max-cost "$PRICE" -o boat.mp4
```

`--image photo.png` animates a local picture (it is uploaded for you), `--end-image` sets the last frame,
`--ref` adds reference pictures, `--set key=value` sends any other input field. It waits and saves the file.

With curl, using the same `$BODY` and the agreed `$PRICE`:

```bash
KEY=$(uuidgen); echo "Idempotency-Key: $KEY"   # once per video; resend with this same value
RESP=$(curl -s https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" -d "$(echo "$BODY" | jq --argjson max "$PRICE" '. + {max_cost_usd: $max}')")
ID=$(echo "$RESP" | jq -r '.id // empty')
[ -n "$ID" ] && echo "$RESP" | jq '{id, status, quoted_usd}' || echo "$RESP" | jq .error
```

No `id` means the request was refused (see Errors): nothing was made or charged, so don't poll.

Input fields: `prompt`, `resolution`, `aspect_ratio`, `duration`, `audio`, `seed`, `negative_prompt`, and media:
`image_url` (start frame), `end_image_url` (last frame), `image_urls` (reference pictures), `video_url` (a clip
to edit or extend), `audio_url`. Seedance 2.5 also takes `video_urls` and `audio_urls` as references, and
`image_url` cannot be combined with reference media there.

### Local files

Media must be public https links. For a file on disk, upload it (free, link lasts 14 days):

```bash
UP=$(curl -s https://api.revana.si/v1/uploads -H "Authorization: Bearer $REVANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"content_type\": \"image/png\", \"bytes\": $(wc -c < photo.png | tr -d ' ')}")
H=(); while IFS= read -r h; do H+=(-H "$h"); done \
  < <(echo "$UP" | jq -r '.upload_headers | to_entries[] | "\(.key): \(.value)"')
curl -s -X PUT "$(echo "$UP" | jq -r .upload_url)" "${H[@]}" --data-binary @photo.png
IMAGE_URL=$(echo "$UP" | jq -r .url)
```

PUT with exactly `upload_headers` (content type and length are signed). Or run `npx revana upload photo.png`,
which prints the URL.

## 4. Wait and download

```bash
while :; do
  S=$(curl -s https://api.revana.si/v1/generations/$ID -H "Authorization: Bearer $REVANA_API_KEY")
  case $(echo "$S" | jq -r '.status // "error"') in succeeded|failed|error) break;; esac
  sleep 10
done
echo "$S" | jq '{status, cost_usd, error}'
[ "$(echo "$S" | jq -r .status)" = succeeded ] && \
  curl -sL https://api.revana.si/v1/generations/$ID/content -H "Authorization: Bearer $REVANA_API_KEY" -o out.mp4
```

Video takes from under a minute to several minutes. Tell the person the final `cost_usd`.

## Errors

- `failed` with `error.retryable: true` (model_busy, timeout, all_routes_failed): the same request can work
  later. Send it again with a **new** Idempotency-Key; the old one keeps answering the failed video.
  `retryable: false` (content_policy, invalid_input): change the request, then use a new key.
- No answer, a timeout, or a 5xx on the create: resend with the **same** key (rule 4).
- `402 insufficient_credits`: `GET /v1/balance` shows `available_usd`; top up at https://revana.si/dashboard.
- `403 card_required`: the account's free credit needs a saved card first; add one in the dashboard.
- `422 max_cost_exceeded`: the cap is below the price. Re-quote and ask again; do not silently raise it.
- `429` or `503`: wait the `Retry-After` header's seconds, then resend with the same key.
- Asking for help: quote the `request_id` (in `error.request_id`, or the `X-Request-Id` header) and the
  generation `id`. Request ids are on API versions deployed after 2026-10-31.

Full reference: https://revana.si/llms.txt. Prices: https://revana.si/pricing.
