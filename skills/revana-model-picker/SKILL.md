---
name: revana-model-picker
description: Find the cheapest AI model for a job from Revana's live price list (GET https://api.revana.si/v1/models, no key needed) - video, image, music and 90+ chat LLMs. Use when the user asks "cheapest veo api", "cheapest seedance api", "what's the cheapest text to video model", "compare kling vs veo price", "how much does a 10 second video cost", "cheapest image generation api", "cheaper than kie.ai / fal / replicate", or wants a model recommendation that fits a budget.
---

# Revana model picker: the cheapest model for the job, from live prices

Revana (https://revana.si) lists every model it can run right now, with options and prices, at
`GET https://api.revana.si/v1/models`. No key is needed. **Always read prices from that list at the time you
answer**: prices change (cuts included), so never quote from memory or from an old file.

## Rank models for a job

The bundled script reads the live list and ranks what fits:

```bash
python3 scripts/cheapest.py --kind video --seconds 5 --resolution 720p          # any video model
python3 scripts/cheapest.py --kind video --family veo --seconds 8 --audio      # cheapest Veo with sound
python3 scripts/cheapest.py --kind video --task image_to_video --seconds 5     # animate a picture
python3 scripts/cheapest.py --kind image --task text_to_image --resolution 2K  # pictures
python3 scripts/cheapest.py --kind image --task image_to_image                 # edits
python3 scripts/cheapest.py --kind text --top 10                               # chat LLMs, $/M tokens
```

(`scripts/` is next to this file.) Or with jq:

```bash
curl -s https://api.revana.si/v1/models | jq -r '.data[] | select(.kind=="video") | [.id, (.price|tostring)] | @tsv'
```

## How prices read

- `price.unit`: `per_second` (of video out), `per_image`, `per_job` (music), `per_million_tokens` (chat).
- `price.usd`: a number, or a map keyed by the setting that changes the price: resolution (`"720p"`, `"2K"`),
  `+audio` when the video has sound (`"1080p+audio"`), `+video_input` when a clip goes in (edits; billed per
  second of clip), megapixels (`"1MP"`) or quality (`"turbo"`, `"1:1-high"`).
- `price.free: true` means the model costs nothing (it may cap running jobs, `options.max_active_per_account`).
- A video job costs `usd[key] x seconds`. Check `options.durations` (a list, or `{min, max}`) and
  `options.resolutions`: values a model does not list are refused with `422 invalid_input`, free.
- A start image (`image_url`) can cost more per second than the plain price listed: Seedance 2.5 charges more
  with one. For image to video, treat the ranked price as the least it costs, and get the exact number from the
  server quote (`POST /v1/generations/quote`, with a key, on API versions deployed after 2026-10-31) before
  anything is spent.
- Each model has a page at `https://revana.si/models/<id>`; https://revana.si/pricing has the full table, and
  https://revana.si/llms.txt lists where Revana is cheaper than other APIs, with the comparison dates.

## Answering

1. Ask (or infer) what matters: kind, length, resolution, sound, start image, quality bar.
2. Run the ranking. Give the top 2-4 with the job price, and say which you'd pick and why (the cheapest is not
   always right: Seedance 2.5 and Veo 3.1 lead on quality, Wan/Hailuo/MiniMax/Grok are cheaper drafts).
3. Mention the date of the prices ("live price list, today"). For a different price book (enterprise or volume)
   the server's quote, or the generation's own `quoted_usd`, is the source of truth.
4. If they want to run it, hand off to `revana-video` or `revana-image`: quote, get a yes, pass `max_cost_usd`.

Never print the person's `REVANA_API_KEY`; the price list needs no key at all.
