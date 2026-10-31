# Shared by the curl examples: source it, don't run it. Needs curl and jq.
API=${REVANA_BASE_URL:-https://api.revana.si}

# http METHOD PATH [JSON BODY] [extra curl args...]: sets CODE (000 when there was no answer) and RESP.
http() {
  local method=$1 path=$2 body=${3-}; shift 3 2>/dev/null || shift $#
  local args=(-s -X "$method" -w '\n%{http_code}' -H "Authorization: Bearer $REVANA_API_KEY")
  [ -n "$body" ] && args+=(-H "Content-Type: application/json" -d "$body")
  local out
  out=$(curl "${args[@]}" "$@" "$API$path") || out=$'\n000'
  CODE=${out##*$'\n'}
  RESP=${out%$'\n'*}
}

# Print an error answer: its code, message and request_id, or the raw text.
show_error() { echo "$RESP" | jq -c '.error // .' 2>/dev/null || echo "${RESP:-no answer} (HTTP $CODE)"; }

# quote_job BODY: sets PRICE (USD, whole cents) and QUOTED_BY ("server" or "list").
# The server's free quote (POST /v1/generations/quote) prices the exact request. API versions from before the
# 2026-10-31 deploy answer it 404; then the price comes from the live list at GET /v1/models (no key), which does not
# show what a start image adds on some models (Seedance 2.5): a refusal (422 max_cost_exceeded) is free.
quote_job() {
  local body=$1
  http POST /v1/generations/quote "$body"
  case $CODE in
    200) PRICE=$(echo "$RESP" | jq -r .quoted_usd); QUOTED_BY=server ;;
    404)
      QUOTED_BY=list
      PRICE=$(curl -sf "$API/v1/models" | jq -r --argjson b "$body" '
        .data[] | select(.id == $b.model) | .price as $p
        | ($p.usd | if type == "number" then .
            else ((if $b.input.audio then .[($b.input.resolution // "") + "+audio"] else null end)
                  // .[$b.input.resolution // ""]) end) as $each
        | select($each != null)
        | ($each * (if $p.unit == "per_second" then ($b.input.duration // 5) else 1 end) * 100 - 1e-6) | ceil / 100') || PRICE=
      [ -n "$PRICE" ] || { echo "No list price for this model and setting (or no answer): see $API/v1/models" >&2; exit 1; } ;;
    *) show_error >&2; exit 1 ;;
  esac
}

# create_job BODY MAX_COST_USD: sets ID. One Idempotency-Key for this generation, made once: a resend after no
# answer, a 429 or a 5xx carries the same key, so it returns the generation already started instead of a second one.
create_job() {
  local body key try
  body=$(echo "$1" | jq --argjson max "$2" '. + {max_cost_usd: $max}')
  key=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
  for try in 1 2 3 4; do
    http POST /v1/generations "$body" -H "Idempotency-Key: $key"
    case $CODE in
      000|429|5??) [ $try -lt 4 ] || break; echo "  create answered $CODE; resending with the same key" >&2; sleep $((try * 5)) ;;
      *) break ;;
    esac
  done
  ID=$(echo "$RESP" | jq -r '.id // empty' 2>/dev/null || true)
  # No id: the request was refused, so nothing was made or charged. Don't poll.
  [ -n "$ID" ] || { show_error >&2; exit 1; }
}

# wait_job ID [SECONDS]: polls until succeeded (sets GEN) or exits on failed or an error answer.
# After "failed", a new try needs a new Idempotency-Key: the old one keeps answering the failed generation.
wait_job() {
  local status
  while :; do
    http GET "/v1/generations/$1"
    status=$(echo "$RESP" | jq -r '.status // empty' 2>/dev/null || true)
    case $status in
      succeeded) GEN=$RESP; return ;;
      failed) echo "$RESP" | jq -c .error >&2; exit 1 ;;
      queued|running) echo "  $status" >&2; sleep "${2:-10}" ;;
      *) [ "$CODE" = 000 ] || [ "${CODE:0:1}" = 5 ] || [ "$CODE" = 429 ] || { show_error >&2; exit 1; }; sleep "${2:-10}" ;;
    esac
  done
}
