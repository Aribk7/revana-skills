#!/usr/bin/env bash
# Everything here is free: the model list, your balance, and a request the API refuses before charging.
set -euo pipefail
API=https://api.revana.si

echo "Video models and their price per second (no key needed):"
curl -sf $API/v1/models | jq -r '.data[] | select(.kind=="video") | "\(.id)\t\(.price.usd | tostring)"' | head -15

: "${REVANA_API_KEY:?Set REVANA_API_KEY to also check your balance}"
echo; echo "Balance:"
curl -sf $API/v1/balance -H "Authorization: Bearer $REVANA_API_KEY" | jq '{available_usd, held_usd, spent_usd}'

echo; echo "A value the model does not offer is refused with 422 invalid_input, and nothing is charged:"
curl -s $API/v1/generations -H "Authorization: Bearer $REVANA_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "seedance-2.5", "input": {"prompt": "test", "resolution": "999p"}, "max_cost_usd": 0.01}' | jq .error
