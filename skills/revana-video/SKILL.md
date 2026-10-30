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
2. **Quote first.** Work out the price from the live model list, tell the person, and wait for a yes before
   anything is spent.
3. **Always send `max_cost_usd`** set to the price they agreed to, so the job can never cost more.
4. Send an `Idempotency-Key` header. If you retry, send the same key again: that never makes or charges a
   second video.

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

Video prices are `per_second` of video out. `price.usd` is a number, or a map keyed by resolution
(`"720p"`), with `+audio` when sound is on (`"720p+audio"`) and `+video_input` when a clip goes in.

```
price = usd[key] x duration
```

Example: `seedance-2.5`, 720p, 5 s at a listed $0.25/s quotes $1.25 (dated example from 2026-10-30; read the
live price, it changes). Say it plainly: "A 5-second 720p Seedance 2.5 clip costs $1.25. Go ahead?"

Only values a model lists in `options` are accepted; anything else returns `422 invalid_input` and is free.

## 3. Generate

With the CLI (Node 18+):

```bash
npx revana generate seedance-2.5 "a paper boat drifting down a rainy street, close up" \
  --duration 5 --resolution 720p --aspect 16:9 --audio --max-cost 1.25 -o boat.mp4
```

`--image photo.png` animates a local picture (it is uploaded for you), `--end-image` sets the last frame,
`--ref` adds reference pictures, `--set key=value` sends any other input field. It waits and saves the file.

With curl:

```bash
RESP=$(curl -s https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model": "seedance-2.5",
       "input": {"prompt": "a paper boat drifting down a rainy street, close up",
                 "resolution": "720p", "duration": 5, "aspect_ratio": "16:9", "audio": true},
       "max_cost_usd": 1.25}')
ID=$(echo "$RESP" | jq -r .id); echo "$RESP" | jq '{id, status, quoted_usd, error}'
```

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
until S=$(curl -s https://api.revana.si/v1/generations/$ID -H "Authorization: Bearer $REVANA_API_KEY"); \
      echo "$S" | jq -e '.status=="succeeded" or .status=="failed"' >/dev/null; do sleep 10; done
echo "$S" | jq '{status, cost_usd, error}'
curl -sL https://api.revana.si/v1/generations/$ID/content -H "Authorization: Bearer $REVANA_API_KEY" -o out.mp4
```

Video takes from under a minute to several minutes. Tell the person the final `cost_usd`.

## Errors

- `failed` with `error.retryable: true` (model_busy, timeout, all_routes_failed): the same request can work
  later; resend with the same Idempotency-Key. `retryable: false` (content_policy, invalid_input): change it.
- `402 insufficient_credits`: `GET /v1/balance` shows `available_usd`; top up at https://revana.si/dashboard.
- `422 max_cost_exceeded`: the cap is below the price. Re-quote and ask again; do not silently raise it.

Full reference: https://revana.si/llms.txt. Prices: https://revana.si/pricing.
