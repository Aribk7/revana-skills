---
name: revana-image
description: Make or edit AI images through the Revana API (api.revana.si) - Nano Banana Pro, Nano Banana 2, GPT Image 2, Flux 2 and 3, Seedream, Imagen 4, Midjourney, Ideogram, Qwen Image and 40+ more image models on one API key. Use when the user asks to generate, draw, render or edit a picture, photo, product shot, thumbnail or logo with AI, "nano banana pro api", "gpt image api", "flux api", "edit this photo with AI", wants cheap image generation in code, or asks to replace kie.ai, fal or Replicate for images.
---

# Revana image: Nano Banana Pro, GPT Image, Flux on one key

Revana (https://revana.si) runs every image model behind one request shape: `POST /v1/generations`, poll,
download. The cheapest provider is tried first with automatic fallback; failed generations are free. Credits are
prepaid, 100 credits = $1.

## Rules

1. The key is in `REVANA_API_KEY` (starts `sr_live_`). If it is unset, ask the person to create one at
   https://revana.si/dashboard and export it in their own shell. **Never print, echo, log or write the key.**
2. **Quote first**, tell the person the price, and wait for a yes before spending.
3. **Always send `max_cost_usd`** at the agreed price.
4. **One `Idempotency-Key` per generation, made once** (`KEY=$(uuidgen)`; note the value, since agent shells
   often forget variables). Resend with the **same** key after a timeout, a dropped connection, a 5xx or a 429:
   you get the generation already started, never a second charge. After a generation has **failed**, make a
   **new** key: the old one keeps answering the failure. The same key with a different body is
   `409 idempotency_conflict`.

## 1. Pick a model and read its price (free, no key)

```bash
curl -s https://api.revana.si/v1/models \
  | jq '.data[] | select(.kind=="image") | {id, tasks, options, price}'
```

| Ask | Model ids |
|---|---|
| Best edits, text in images, many references | `nano-banana-pro`, `nano-banana-2`, `nano-banana-2.1` |
| OpenAI | `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1` |
| Flux | `flux-2-pro`, `flux-2-max`, `flux-3`, `flux-3-klein`, `flux-kontext-pro` |
| Others | `seedream-5.0-pro`, `imagen-4`, `midjourney-v7`, `ideogram-v3`, `qwen-image-3.0`, `z-image` |
| Upscale | `recraft-crisp-upscale` |

Every model has a page at `https://revana.si/models/<id>`. For "which is cheapest", use `revana-model-picker`.

## 2. Quote

Image prices are `per_image`. `price.usd` is a number, or a map keyed by what changes the price: resolution
(`"1K"`, `"2K"`, `"4K"`), megapixels (`"1MP"`), quality (`"turbo"`, `"quality"`) or aspect and quality
(`"1:1-high"` on gpt-image-1). Price = `usd[key]` for each generation; several pictures means several
generations. If a model's `options` say it returns more than one output, check its page before quoting.

Tell the person: "One 2K Nano Banana Pro image costs $X. Go ahead?" (read X from the live list, never from
memory) and keep the agreed number as `PRICE`.

On API versions deployed after 2026-10-31 the server prices the exact request for free: `POST
/v1/generations/quote` with the same body as the create answers `quoted_usd` (an older server answers
`404 not_found`; then use the list).

## 3. Generate

CLI (Node 18+):

```bash
npx revana generate nano-banana-pro "studio photo of a matte black water bottle on wet slate, soft light" \
  --resolution 2K --aspect 4:5 --max-cost "$PRICE" -o bottle.png
```

Edit a local photo: add `--image photo.jpg` (uploaded for you). More references: `--ref a.png --ref b.png`.

curl:

```bash
KEY=$(uuidgen); echo "Idempotency-Key: $KEY"   # once per generation; resend with this same value
RESP=$(curl -s https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" \
  -d "$(jq -n --argjson max "$PRICE" '{model: "nano-banana-pro",
       input: {prompt: "studio photo of a matte black water bottle on wet slate, soft light",
               resolution: "2K", aspect_ratio: "4:5"},
       max_cost_usd: $max}')")
ID=$(echo "$RESP" | jq -r '.id // empty')
[ -n "$ID" ] || echo "$RESP" | jq .error   # refused: nothing made or charged, don't poll
```

Input fields: `prompt`, `resolution`, `aspect_ratio`, `quality`, `seed`, `negative_prompt`, `image_url`
(the picture to edit), `image_urls` (references, up to the model's `max_input_images`). Values a model does not
list return `422 invalid_input`, free.

For a local file, `POST /v1/uploads` with `{"content_type": "image/png", "bytes": <size>}`, PUT the bytes to
`upload_url` with exactly `upload_headers`, then pass the returned `url`. Or `npx revana upload photo.png`.

## 4. Wait and download

```bash
while :; do
  S=$(curl -s https://api.revana.si/v1/generations/$ID -H "Authorization: Bearer $REVANA_API_KEY")
  case $(echo "$S" | jq -r '.status // "error"') in succeeded|failed|error) break;; esac
  sleep 3
done
echo "$S" | jq '{status, cost_usd, n: (.output.urls | length), error}'
[ "$(echo "$S" | jq -r .status)" = succeeded ] && \
  curl -sL https://api.revana.si/v1/generations/$ID/content -H "Authorization: Bearer $REVANA_API_KEY" -o out.png
```

Images usually take 5-60 s. A model can return several files: `output.urls` lists them; fetch the second with
`/content/2`, the third with `/content/3`.

## Errors

- `error.code: content_policy` (with `reason`) or `model_declined`: change the prompt, then send it with a new
  Idempotency-Key. `retryable: true`: the same request can work later; send it again with a **new** key (the
  old one keeps answering the failed generation).
- A timeout, a 5xx or a 429 on the create (`Retry-After` says how long to wait): resend with the **same** key.
- `402 insufficient_credits`: check `GET /v1/balance`; top up at https://revana.si/dashboard.
- `403 card_required`: the account's free credit needs a saved card first; add one in the dashboard.
- Asking for help: quote the `request_id` (`error.request_id`, or the `X-Request-Id` header; on API versions
  deployed after 2026-10-31) and the generation `id`.

Full reference: https://revana.si/llms.txt. Prices: https://revana.si/pricing.
