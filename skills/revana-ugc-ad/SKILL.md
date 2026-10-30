---
name: revana-ugc-ad
description: Make a short AI product ad or UGC-style video (a person holding, using or talking about a product) through the Revana API - first a still with Nano Banana Pro or GPT Image 2 from the product photo, then a 9:16 talking video with Seedance 2.5 or Veo 3.1 with sound. Use when the user asks for a "UGC ad", "product video", "TikTok ad", "Reels ad", "AI influencer video", "make an ad for my product", "animate my product photo", or "product photo to video".
---

# Revana UGC ad: product photo -> still -> 9:16 video

Two Revana generations on one key: a still (the person and the product, in the setting) and then a video that
starts on that still. Revana (https://revana.si) picks the cheapest route for each and charges only what succeeds;
failed generations are free.

## Rules

1. The key is in `REVANA_API_KEY` (starts `sr_live_`). If unset, ask the person to create one at
   https://revana.si/dashboard and export it themselves. **Never print, echo, log or write the key.**
2. **Quote both steps up front** from the live price list and get a yes before spending anything.
3. **Pass `max_cost_usd`** on each generation, at that step's quoted price.
4. Show the still and get an OK before the video: the video is the expensive step.
5. Send an `Idempotency-Key` header per generation and reuse it on retries.

## 0. Brief

Ask for (or infer): the product photo (file or link), who is in the ad (age, look, setting), the line they say
(one or two short sentences, about 2.5 words a second), length (5-10 s), and format (9:16 by default).

## 1. Quote (free, no key)

```bash
curl -s https://api.revana.si/v1/models | jq '.data[] | select(.id=="nano-banana-pro" or .id=="seedance-2.5") | {id, price}'
```

Total = one still (`per_image`, by resolution) + video (`per_second` x seconds, by resolution). Example from the
list on 2026-10-30: a 2K Nano Banana Pro still plus 8 s of 720p Seedance 2.5 was $0.04 + 8 x $0.25 = $2.04.
Read today's prices; they change. Say: "Still about $0.04, then an 8-second 720p video $2.00: $2.04 total. Go?"

Cheaper draft: `gpt-image-2` for the still and `seedance-2.0-fast` or `wan-3.0` for the video (use the
`revana-model-picker` skill to rank them).

## 2. Product photo

A local photo must be uploaded first (free, link good for 14 days):

```bash
npx revana upload product.jpg        # prints the URL
```

or by API: `POST /v1/uploads` with `{"content_type": "image/jpeg", "bytes": <size>}`, PUT the bytes to
`upload_url` with exactly `upload_headers`, then use the answer's `url`.

## 3. Still

```bash
npx revana generate nano-banana-pro \
  "UGC selfie photo, a woman in her late 20s in a bright kitchen holds this exact bottle up to the camera, smiling, natural phone-camera look, product label sharp and readable" \
  --ref "$PRODUCT_URL" --resolution 2K --aspect 9:16 --max-cost 0.04 -o still.png
```

Keep the product photo as a reference (`image_urls`) so the label stays right. Show `still.png` and ask.

## 4. Video from the still

Upload the still (`npx revana upload still.png`) and make it the first frame (`image_url`):

```bash
npx revana generate seedance-2.5 \
  "She looks into the camera and says: \"I stopped buying plastic bottles. This one keeps ice for a whole day.\" Handheld selfie video, natural light, slight camera shake, real room sound." \
  --image "$STILL_URL" --duration 8 --resolution 720p --aspect 9:16 --audio --max-cost 2.00 -o ad.mp4
```

curl equivalent:

```bash
curl -s https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d "{\"model\": \"seedance-2.5\", \"max_cost_usd\": 2.00,
       \"input\": {\"prompt\": \"...\", \"image_url\": \"$STILL_URL\", \"duration\": 8,
                  \"resolution\": \"720p\", \"aspect_ratio\": \"9:16\", \"audio\": true}}"
```

Then poll `GET /v1/generations/{id}` until `succeeded` or `failed` and download `GET /v1/generations/{id}/content`
(see the `revana-video` skill). Report what it cost (`cost_usd`).

## Tips

- Write the spoken line in quotes in the prompt; Seedance 2.5 and Veo 3.1 speak it with lip sync when `audio` is on.
- For several hooks, make one still and several videos with different lines: quote the total first.
- Longer ads: make 2-3 clips of 5-10 s and cut them together; Seedance 2.5 goes up to 30 s in one clip.
- `error.code: content_policy` with `reason: real_person` means the still looks like a real, known person:
  describe a generic person instead.

Full reference: https://revana.si/llms.txt. Prices: https://revana.si/pricing.
