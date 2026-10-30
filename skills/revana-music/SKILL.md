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
3. Send an `Idempotency-Key` header and reuse it on retries.

## Quote (free, no key)

```bash
curl -s https://api.revana.si/v1/models | jq '.data[] | select(.kind=="audio") | {id, options, price}'
```

## Generate

```bash
npx revana generate suno-v6 "an upbeat acoustic song about a summer road trip" \
  --set style="indie folk, warm vocals" --set instrumental=false --max-cost 0.08 -o song.mp3
```

curl:

```bash
RESP=$(curl -s https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model": "suno-v6",
       "input": {"prompt": "an upbeat acoustic song about a summer road trip",
                 "style": "indie folk, warm vocals", "instrumental": false},
       "max_cost_usd": 0.08}')
ID=$(echo "$RESP" | jq -r .id)
```

(The `0.08` above is the dated price from 2026-10-30; use today's.) Poll `GET /v1/generations/$ID` until
`succeeded` or `failed`, then download both tracks:

```bash
curl -sL https://api.revana.si/v1/generations/$ID/content   -H "Authorization: Bearer $REVANA_API_KEY" -o song-1.mp3
curl -sL https://api.revana.si/v1/generations/$ID/content/2 -H "Authorization: Bearer $REVANA_API_KEY" -o song-2.mp3
```

For lyrics, put them in `prompt`. For a video's soundtrack, set `instrumental: true` and describe the mood and tempo.

Full reference: https://revana.si/llms.txt. Prices: https://revana.si/pricing.
