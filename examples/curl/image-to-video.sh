#!/usr/bin/env bash
# Animate a local picture with Seedance 2.5: upload it (free), then use it as the first frame.
#   ./image-to-video.sh photo.png "the camera slowly pushes in"
#   MAX_COST=1.50 ./image-to-video.sh photo.png   # a cap of your own instead of the quote
set -euo pipefail
: "${REVANA_API_KEY:?Set REVANA_API_KEY first (https://revana.si/dashboard)}"
source "$(dirname "$0")/lib.sh"
FILE=${1:?usage: image-to-video.sh <image> [prompt]}
PROMPT=${2:-"the camera slowly pushes in, gentle natural motion"}

# 1. Upload: ask for a link, PUT the bytes with exactly the headers it gives, use its url (14 days).
TYPE=$(file -b --mime-type "$FILE")
http POST /v1/uploads "$(jq -n --arg t "$TYPE" --argjson b "$(wc -c < "$FILE" | tr -d ' ')" '{content_type: $t, bytes: $b}')"
[ "$CODE" = 201 ] || [ "$CODE" = 200 ] || { show_error >&2; exit 1; }
UP=$RESP
H=(); while IFS= read -r h; do H+=(-H "$h"); done < <(echo "$UP" | jq -r '.upload_headers | to_entries[] | "\(.key): \(.value)"')
curl -sf -X PUT "$(echo "$UP" | jq -r .upload_url)" ${H[@]+"${H[@]}"} --data-binary @"$FILE" >/dev/null
IMAGE_URL=$(echo "$UP" | jq -r .url)
echo "uploaded $FILE"

BODY=$(jq -n --arg p "$PROMPT" --arg i "$IMAGE_URL" \
  '{model: "seedance-2.5", input: {prompt: $p, image_url: $i, resolution: "720p", duration: 5, aspect_ratio: "adaptive"}}')

# 2. Quote and confirm.
quote_job "$BODY"
if [ "$QUOTED_BY" = list ] && [ -z "${MAX_COST:-}" ]; then
  echo "note: listed price. With a start image Seedance 2.5 costs more; if the API refuses the cap (free), rerun with MAX_COST=<usd>."
fi
PRICE=${MAX_COST:-$PRICE}
echo "seedance-2.5, 5s 720p from $FILE: \$$PRICE"
read -r -p "Spend up to \$$PRICE? [y/N] " OK; [[ $OK =~ ^[Yy] ]] || exit 0

# 3. Submit (checked before polling), poll, download.
create_job "$BODY" "$PRICE"
echo "submitted $ID"
wait_job "$ID" 10
curl -sL "$API/v1/generations/$ID/content" -H "Authorization: Bearer $REVANA_API_KEY" -o "$ID.mp4"
echo "saved $ID.mp4, cost \$$(echo "$GEN" | jq .cost_usd)"
