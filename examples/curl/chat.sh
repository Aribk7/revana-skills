#!/usr/bin/env bash
# Chat completions on the same key: OpenAI-compatible, 90+ language models, billed per token.
# Any OpenAI SDK works with base URL https://api.revana.si/v1.
set -euo pipefail
: "${REVANA_API_KEY:?Set REVANA_API_KEY first}"
curl -s https://api.revana.si/v1/chat/completions \
  -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "claude-haiku-5-5", "max_tokens": 200,
       "messages": [{"role": "user", "content": "Write a 10-word hook for a water bottle ad."}]}' \
  | jq '{text: .choices[0].message.content, cost_usd: .usage.cost_usd}'
