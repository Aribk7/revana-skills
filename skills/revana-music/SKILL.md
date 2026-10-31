---
name: revana-music
description: Make AI songs and instrumentals with Suno V6 through the Revana API (api.revana.si), on the same key as Revana's image and video models. Use when the user asks to "make a song", "generate music", "suno api", "background music for my video", "jingle", "instrumental track", or wants a cheap music generation API.
---

# Revana music: Suno V6 on the Revana key

`suno-v6` makes a full song with vocals, or an instrumental, from an idea, lyrics or a style. Each generation
returns two tracks. Priced `per_job` (one price for both tracks); failed generations are free.

## Rules

1. The key is in `REVANA_API_KEY`. If unset, ask the person to create one at https://revana.si/dashboard and
   export it themselves. **Never print, echo, log or write the key.**
2. **Quote first** and get a yes. **Pass `max_cost_usd`** at the quoted price.
3. **One `Idempotency-Key` per song, made once** (`KEY=$(uuidgen)`; note the value, since agent shells often
   forget variables). Resend with the **same** key after a timeout, a dropped connection, a 5xx or a 429. After a
   generation has **failed**, make a **new** key: the old one keeps answering the failure.

## Input

- `style`: the genre and sound, such as `"indie folk, warm vocals"`.
- `lyrics`: the words to sing, up to 5000 characters. Without lyrics the model writes its own.
- `prompt`: the idea, such as `"an upbeat song about a summer road trip"` (up to 3000 characters).
- `instrumental: true` for no vocals (then send no `lyrics`).

Send `style` or `lyrics` (a `prompt` alone is refused with `422 invalid_input`, free). Words to sing go in
`lyrics`, never in `prompt`.

## Quote (free, no key)

```bash
curl -s https://api.revana.si/v1/models | jq '.data[] | select(.kind=="audio") | {id, options, price}'
```

Read today's price from that list (never from memory) and keep the agreed number as `PRICE`. On API versions
deployed after 2026-10-31, `POST /v1/generations/quote` with the same body as the create also answers
`quoted_usd` (an older server answers `404 not_found`).

## Generate

```bash
npx revana generate suno-v6 "an upbeat acoustic song about a summer road trip" \
  --set style="indie folk, warm vocals" --set lyrics="$(cat lyrics.txt)" --max-cost "$PRICE" -o song.mp3
```

curl:

```bash
KEY=$(uuidgen); echo "Idempotency-Key: $KEY"   # once per song; resend with this same value
RESP=$(curl -s https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" \
  -d "$(jq -n --arg lyrics "$(cat lyrics.txt)" --argjson max "$PRICE" '{model: "suno-v6",
       input: {prompt: "an upbeat acoustic song about a summer road trip",
               style: "indie folk, warm vocals", lyrics: $lyrics},
       max_cost_usd: $max}')")
ID=$(echo "$RESP" | jq -r '.id // empty')
[ -n "$ID" ] || echo "$RESP" | jq .error   # refused: nothing made or charged, don't poll
```

Poll `GET /v1/generations/$ID` until `succeeded` or `failed`, then download both tracks:

```bash
curl -sL https://api.revana.si/v1/generations/$ID/content   -H "Authorization: Bearer $REVANA_API_KEY" -o song-1.mp3
curl -sL https://api.revana.si/v1/generations/$ID/content/2 -H "Authorization: Bearer $REVANA_API_KEY" -o song-2.mp3
```

For a video's soundtrack, set `instrumental: true`, describe the mood and tempo in `style`, and send no `lyrics`.

When asking for help, quote the `request_id` (`error.request_id` or the `X-Request-Id` header, on API versions
deployed after 2026-10-31) and the generation `id`.

Full reference: https://revana.si/llms.txt. Prices: https://revana.si/pricing.
