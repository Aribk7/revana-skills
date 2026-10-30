#!/usr/bin/env bash
# Text to video with Seedance 2.5 on Revana, with curl and jq.
#   export REVANA_API_KEY=...   (https://revana.si/dashboard)
#   ./text-to-video.sh "a paper boat drifting down a rainy street at night"
set -euo pipefail
: "${REVANA_API_KEY:?Set REVANA_API_KEY first (https://revana.si/dashboard)}"
API=https://api.revana.si
PROMPT=${1:-"a paper boat drifting down a rainy street at night, close up, reflections"}
MODEL=seedance-2.5 RES=720p DURATION=5

# 1. Quote from the live price list (no key needed). Prices change: never hardcode them.
# price.usd is a number, or a map keyed by resolution with "+audio" where sound costs extra.
PER_S=$(curl -sf $API/v1/models | jq -r --arg m $MODEL --arg r $RES \
  '.data[] | select(.id==$m) | .price.usd | if type=="number" then . else (.[$r+"+audio"] // .[$r]) end')
PRICE=$(jq -n "$PER_S * $DURATION * 100 | ceil / 100")
echo "$MODEL, ${DURATION}s $RES with sound: \$$PRICE"
read -r -p "Spend up to \$$PRICE? [y/N] " OK; [[ $OK =~ ^[Yy] ]] || exit 0

# 2. Submit. max_cost_usd caps the charge; the Idempotency-Key makes a retry return the same job.
BODY=$(jq -n --arg p "$PROMPT" --arg m $MODEL --arg r $RES --argjson s $DURATION --argjson max "$PRICE" \
  '{model: $m, input: {prompt: $p, resolution: $r, duration: $s, aspect_ratio: "16:9", audio: true}, max_cost_usd: $max}')
RESP=$(curl -s $API/v1/generations -H "Authorization: Bearer $REVANA_API_KEY" \
  -H "Content-Type: application/json" -H "Idempotency-Key: $(uuidgen)" -d "$BODY")
ID=$(echo "$RESP" | jq -r '.id // empty')
[ -n "$ID" ] || { echo "$RESP" | jq .error; exit 1; }
echo "submitted $ID"

# 3. Poll until it finishes (video takes from under a minute to several minutes).
while :; do
  GEN=$(curl -s $API/v1/generations/$ID -H "Authorization: Bearer $REVANA_API_KEY")
  STATUS=$(echo "$GEN" | jq -r .status)
  [ "$STATUS" = succeeded ] && break
  [ "$STATUS" = failed ] && { echo "$GEN" | jq .error; exit 1; }
  echo "  $STATUS"; sleep 10
done

# 4. Download. curl -L does not send the key on to the file host.
curl -sL $API/v1/generations/$ID/content -H "Authorization: Bearer $REVANA_API_KEY" -o "$ID.mp4"
echo "saved $ID.mp4, cost \$$(echo "$GEN" | jq .cost_usd)"
