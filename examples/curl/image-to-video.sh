#!/usr/bin/env bash
# Animate a local picture with Seedance 2.5: upload it (free), then use it as the first frame.
#   ./image-to-video.sh photo.png "the camera slowly pushes in"
set -euo pipefail
: "${REVANA_API_KEY:?Set REVANA_API_KEY first (https://revana.si/dashboard)}"
API=https://api.revana.si
FILE=${1:?usage: image-to-video.sh <image> [prompt]}
PROMPT=${2:-"the camera slowly pushes in, gentle natural motion"}
MODEL=seedance-2.5 RES=720p DURATION=5
AUTH=(-H "Authorization: Bearer $REVANA_API_KEY")

# 1. Upload: ask for a link, PUT the bytes with exactly the headers it gives, use its url (14 days).
TYPE=$(file -b --mime-type "$FILE")
UP=$(curl -sf $API/v1/uploads "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "$(jq -n --arg t "$TYPE" --argjson b "$(wc -c < "$FILE" | tr -d ' ')" '{content_type: $t, bytes: $b}')")
H=(); while IFS= read -r h; do H+=(-H "$h"); done < <(echo "$UP" | jq -r '.upload_headers | to_entries[] | "\(.key): \(.value)"')
curl -sf -X PUT "$(echo "$UP" | jq -r .upload_url)" "${H[@]}" --data-binary @"$FILE" >/dev/null
IMAGE_URL=$(echo "$UP" | jq -r .url)
echo "uploaded $FILE"

# 2. Quote and confirm.
PER_S=$(curl -sf $API/v1/models | jq -r --arg m $MODEL --arg r $RES \
  '.data[] | select(.id==$m) | .price.usd | if type=="number" then . else .[$r] end')
PRICE=$(jq -n "$PER_S * $DURATION * 100 | ceil / 100")
echo "$MODEL, ${DURATION}s $RES: \$$PRICE"
read -r -p "Spend up to \$$PRICE? [y/N] " OK; [[ $OK =~ ^[Yy] ]] || exit 0

# 3. Submit, poll, download.
BODY=$(jq -n --arg p "$PROMPT" --arg i "$IMAGE_URL" --arg m $MODEL --arg r $RES --argjson s $DURATION --argjson max "$PRICE" \
  '{model: $m, input: {prompt: $p, image_url: $i, resolution: $r, duration: $s, aspect_ratio: "adaptive"}, max_cost_usd: $max}')
ID=$(curl -s $API/v1/generations "${AUTH[@]}" -H "Content-Type: application/json" -H "Idempotency-Key: $(uuidgen)" -d "$BODY" | jq -r .id)
until GEN=$(curl -s $API/v1/generations/$ID "${AUTH[@]}"); echo "$GEN" | jq -e '.status=="succeeded" or .status=="failed"' >/dev/null; do sleep 10; done
[ "$(echo "$GEN" | jq -r .status)" = succeeded ] || { echo "$GEN" | jq .error; exit 1; }
curl -sL $API/v1/generations/$ID/content "${AUTH[@]}" -o "$ID.mp4"
echo "saved $ID.mp4, cost \$$(echo "$GEN" | jq .cost_usd)"
