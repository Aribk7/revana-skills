# Revana examples

Small runnable scripts against `https://api.revana.si`. Each one prices the job from the live model list first,
asks before it spends, and sends `max_cost_usd` at that price. Pass `--yes` to skip the question.

```bash
export REVANA_API_KEY=sr_live_...   # https://revana.si/dashboard; keep it out of code and git
```

| Folder | What | Run |
|---|---|---|
| [`curl/`](curl) | text to video, image to video (with upload), chat, and the free calls | `./curl/text-to-video.sh "a paper boat in the rain"` |
| [`node/`](node) | text to video, image to video, batch images, chat; plain `fetch`, Node 18+, no install. `sdk.mjs` uses the `revana` package | `node node/text-to-video.mjs` |
| [`python/`](python) | the same in Python, standard library only. `sdk_example.py` uses the `revana` package | `python3 python/text_to_video.py` |
| [`nextjs/`](nextjs) | App Router route handlers: start a generation (server-side key, model allowlist, spend cap), poll it, redirect to the file | copy `app/api/revana` into your app |
| [`ai-sdk/`](ai-sdk) | Vercel AI SDK tools: list models, quote (free), generate (needs approval), check status | `import { revanaTools } from "./revana-tools"` |
| [`mcp/`](mcp) | MCP server config for Claude Code, Codex, Cursor, VS Code, ChatGPT | see its README |

Free to try without spending anything: `./curl/free-calls.sh` lists models and prices, shows your balance, and
sends a request the API refuses with `422 invalid_input` (refused requests are never charged).

Python on macOS from python.org may lack CA certificates: `pip install certifi`, or run its
`Install Certificates.command`.

The request in short:

```bash
curl https://api.revana.si/v1/generations \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model": "seedance-2.5", "input": {"prompt": "...", "resolution": "720p", "duration": 5}, "max_cost_usd": 1.25}'
# then GET /v1/generations/{id} until "succeeded", then GET /v1/generations/{id}/content
```
