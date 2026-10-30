# Revana skills and examples

Agent skills, runnable examples and n8n workflows for **[Revana](https://revana.si)**: one API key for 200+
image, video, music and chat models, including Seedance 2.5, Veo 3.1, Kling, Wan, Hailuo, MiniMax, Nano Banana Pro,
GPT Image, Flux, Midjourney, Suno, and 90+ LLMs through an OpenAI-compatible endpoint.

- **One request shape for every model**: `POST /v1/generations` with `model` and `input`, poll, download.
- **Cheapest route first, automatic fallback.** You pay only for the route that succeeds. Failed generations cost nothing.
- **Hard price cap per job** (`max_cost_usd`) and **idempotent retries** (`Idempotency-Key`).
- **Prepaid credits**: no subscription, no monthly quota. Prices: **https://revana.si/pricing**

## Install the skills

Works with Claude Code, Codex, Cursor and other agents that read the open [Agent Skills](https://agentskills.io) format.

| Tool | Install |
|---|---|
| Any agent | `npx skills add Aribk7/revana-skills` |
| Claude Code | `npx skills add Aribk7/revana-skills -a claude-code`, or `/plugin marketplace add Aribk7/revana-skills` then `/plugin install revana-skills@revana-skills` |
| Codex | `npx skills add Aribk7/revana-skills -a codex` |
| Cursor | `npx skills add Aribk7/revana-skills -a cursor` |
| By hand | copy a folder from [`skills/`](skills) into your agent's skills directory (e.g. `~/.claude/skills/`) |
| MCP instead | `claude mcp add --transport http revana https://revana.si/api/mcp` ([other apps](examples/mcp)) |

Then set your key in the shell your agent runs in (create one at https://revana.si/dashboard):

```bash
export REVANA_API_KEY=sr_live_...
```

and ask: *"make a 5 second video of a paper boat in the rain with seedance"*, *"what's the cheapest veo api?"*,
*"make a UGC ad for this product photo"*.

## Skills

| Skill | Use it for | Ask it like |
|---|---|---|
| [`revana-video`](skills/revana-video/SKILL.md) | Text or image to video: Seedance 2.5, Veo 3.1, Kling, Wan, Hailuo, MiniMax, Grok Imagine, Vidu | "make a video with seedance", "veo 3 api", "animate this image" |
| [`revana-image`](skills/revana-image/SKILL.md) | Make and edit pictures: Nano Banana Pro, GPT Image 2, Flux, Seedream, Imagen, Midjourney | "nano banana pro api", "edit this photo", "product shot" |
| [`revana-ugc-ad`](skills/revana-ugc-ad/SKILL.md) | A short product ad: a still from your product photo, then a 9:16 talking video | "make a UGC ad", "TikTok ad for my product" |
| [`revana-model-picker`](skills/revana-model-picker/SKILL.md) | The cheapest model for a job, ranked from live prices (bundled script, no key) | "cheapest veo api", "cheapest text to video" |
| [`revana-music`](skills/revana-music/SKILL.md) | Songs and instrumentals with Suno V6 | "make a song", "suno api" |

Every skill quotes the price from the live list and waits for your OK before spending, sends `max_cost_usd` at
the agreed price, never prints your key, and works with the `revana` CLI or plain curl.

## Examples

[`examples/`](examples): runnable scripts that call `https://api.revana.si`.

| | |
|---|---|
| [curl](examples/curl) | text to video, image to video with an upload, chat, free calls |
| [Node](examples/node) | text to video, image to video, batch images, chat (plain `fetch`), and the `revana` SDK |
| [Python](examples/python) | the same, standard library only, and the `revana` package |
| [Next.js](examples/nextjs) | route handlers: server-side key, model allowlist, spend cap, polling, file redirect |
| [Vercel AI SDK](examples/ai-sdk) | tools: list models, quote, generate (with approval), status |
| [MCP](examples/mcp) | remote MCP config for Claude Code, Codex, Cursor, VS Code, ChatGPT |

## n8n

[`n8n/`](n8n): importable workflows, *AI video generator with Seedance 2.5 via Revana* and *Product photo to UGC
video ad*. Each one quotes from live prices, creates the job, polls with a Wait node, and downloads the video.
[How to import](n8n/README.md).

## The API in 30 seconds

```bash
# Models, options and prices (no key)
curl https://api.revana.si/v1/models

# Make a video
curl https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model": "seedance-2.5", "input": {"prompt": "a paper boat drifting down a rainy street", "resolution": "720p", "duration": 5}, "max_cost_usd": 1.25}'

# Poll, then download
curl https://api.revana.si/v1/generations/$ID -H "Authorization: Bearer $REVANA_API_KEY"
curl -L https://api.revana.si/v1/generations/$ID/content -H "Authorization: Bearer $REVANA_API_KEY" -o out.mp4
```

Prices change, so read them from `/v1/models` when you need them. As a dated example, on 2026-10-30 that
5-second 720p Seedance 2.5 clip listed at $1.25.

Also on the same key:
- `POST /v1/uploads`: a public link for a local file, to use as a reference (free)
- `GET /v1/balance`: what the key can spend
- `POST /v1/chat/completions`: OpenAI-compatible chat. Point any OpenAI SDK at `https://api.revana.si/v1`.

SDKs: `npm i revana` (`npx revana generate seedance-2.5 "..." -o out.mp4`), and `pip install revana`.

Docs: https://revana.si/docs · OpenAPI: https://revana.si/openapi.json · For LLMs: https://revana.si/llms.txt ·
Full reference: https://revana.si/llms-full.txt

## License

[MIT](LICENSE)
