# n8n workflows for Revana

Importable n8n workflows that make AI videos through [Revana](https://revana.si): one API key for Seedance 2.5,
Veo 3.1, Kling, Wan, Hailuo, Nano Banana Pro, GPT Image and 200+ more models.

| Workflow | What it does |
|---|---|
| [`seedance-2.5-video-generator.json`](seedance-2.5-video-generator.json) | AI video generator with Seedance 2.5: text to video, or animate a picture (`image_url`). Switch `model` to `veo-3.1-fast`, `kling-3.0`, `wan-3.0`... |
| [`product-ugc-ad-seedance-2.5.json`](product-ugc-ad-seedance-2.5.json) | Product photo to a 9:16 UGC video ad: a person holds your product and says your line, with sound. |

Both run the same way:

1. **Settings** -> **Get price list** -> **Quote** -> **Within budget?** (stops if the quote is over `max_cost_usd`)
2. **Create generation** -> **Wait** 20 s -> **Get generation**
3. **Succeeded?** -> **Download video**. Not yet -> **Failed?** -> stop with the reason, or back to **Wait**.

- **Quote** reads today's prices from `GET https://api.revana.si/v1/models` (no key). Nothing is hardcoded, so price
  changes flow through.
- The job is sent with `max_cost_usd` set to that quote, so it can never cost more, and with an `Idempotency-Key`
  (`n8n-<execution id>`), so a retried request never makes a second video.
- Failed generations are not charged.

## Import

1. In n8n: **Workflows -> Create -> ... menu -> Import from File** (or paste the JSON onto the canvas), and pick a
   file from this folder. Or from a terminal: `n8n import:workflow --input=seedance-2.5-video-generator.json`.
2. Create an API key at https://revana.si/dashboard and top up credits.
3. **Credentials -> Add credential -> Header Auth**: name `Authorization`, value `Bearer sr_live_...` (your key).
   Call it `Revana API`.
4. Open the three Revana nodes (**Create generation**, **Get generation**, **Download video**) and select that
   credential. **Get price list** needs none.
5. Edit **Settings** (prompt, model, resolution, duration, `max_cost_usd`) and click **Test workflow**.

The video arrives as binary data on **Download video**. Add a Google Drive, S3, Slack or "Write Binary File" node
after it to keep it.

## Change the model

Set `model` in **Settings** to any video model id from https://revana.si/pricing, and `resolution` / `duration` to
values that model lists (https://revana.si/models/<id>). A value it does not offer is refused with
`422 invalid_input` before anything is charged.

For a picture model (e.g. `nano-banana-pro`), set `resolution` to `1K`/`2K`/`4K`, drop `duration` and `audio` from
the **Create generation** body, and lower the **Wait** to 5 s.

## Local pictures

Media must be public https links. To send a file from n8n, call `POST https://api.revana.si/v1/uploads` with
`{"content_type": "image/png", "bytes": <size>}`, PUT the bytes to `upload_url` with exactly `upload_headers`, and
use the returned `url` (good for 14 days). Uploads are free.
