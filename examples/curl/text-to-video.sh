#!/usr/bin/env bash
# Text to video with Seedance 2.5 on Revana, with curl and jq.
#   export REVANA_API_KEY=...   (https://revana.si/dashboard)
#   ./text-to-video.sh "a paper boat drifting down a rainy street at night"
set -euo pipefail
: "${REVANA_API_KEY:?Set REVANA_API_KEY first (https://revana.si/dashboard)}"
source "$(dirname "$0")/lib.sh"
PROMPT=${1:-"a paper boat drifting down a rainy street at night, close up, reflections"}
BODY=$(jq -n --arg p "$PROMPT" \
  '{model: "seedance-2.5", input: {prompt: $p, resolution: "720p", duration: 5, aspect_ratio: "16:9", audio: true}}')

# 1. Quote: the server's free quote, or the live price list on an older API. Prices change: never hardcode them.
quote_job "$BODY"
PRICE=${MAX_COST:-$PRICE}
echo "seedance-2.5, 5s 720p with sound: \$$PRICE (priced by the $QUOTED_BY)"
read -r -p "Spend up to \$$PRICE? [y/N] " OK; [[ $OK =~ ^[Yy] ]] || exit 0

# 2. Submit. max_cost_usd caps the charge; one Idempotency-Key, reused on any resend, means one video at most.
create_job "$BODY" "$PRICE"
echo "submitted $ID"

# 3. Poll until it finishes (video takes from under a minute to several minutes).
wait_job "$ID" 10

# 4. Download. curl -L does not send the key on to the file host.
curl -sL "$API/v1/generations/$ID/content" -H "Authorization: Bearer $REVANA_API_KEY" -o "$ID.mp4"
echo "saved $ID.mp4, cost \$$(echo "$GEN" | jq .cost_usd)"
