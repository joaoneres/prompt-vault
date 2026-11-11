#!/usr/bin/env bash
# Global smoke test of prompt-vault: proves that HTTP -> api -> NATS -> core -> SQLite works
# and that both projects agree on the contract.
#
# What it validates on top of each project's own smoke test:
#   1. the three hops answer (NATS, core via NATS, api via HTTP);
#   2. every HTTP body is valid against the api DTOs (api/models/response_models.py);
#   3. every HTTP query returns exactly the `data` of the same query sent straight to NATS
#      (the gateway only transports);
#   4. a prompt created over HTTP is seen on NATS and one created on NATS is seen over HTTP;
#   5. creating over HTTP publishes the domain event on NATS (prompt.events.created);
#   6. core errors reach HTTP with the standardized status and code.
#
# Prerequisites (this script starts nothing):
#   (core) docker compose up -d && uv run src/main.py
#   (api)  uv run uvicorn main:app          # inside api/ (uv sync done)
#
# Usage: ./smoke_test.sh
# Variables: API_URL (http://localhost:8000), NATS_URL (nats://localhost:4222), SMOKE_TIMEOUT (10)
# Side effect: creates prompts "global-smoke-<id>" in the core database (they end up deleted).

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$ROOT/api"
API_PY="$API_DIR/.venv/bin/python"

API_URL="${API_URL:-http://localhost:8000}"
export NATS_URL="${NATS_URL:-nats://localhost:4222}"
TIMEOUT="${SMOKE_TIMEOUT:-10}"
RUN_ID="$(date +%s)-$RANDOM"
WORKDIR="$(mktemp -d)"
EVENTS_LOG="$WORKDIR/events.log"
SUB_PID=""
STATUS="" BODY="" NRESP=""

if [[ -t 1 ]]; then
  GREEN=$'\033[32m' RED=$'\033[31m' DIM=$'\033[2m' BOLD=$'\033[1m' RESET=$'\033[0m'
else
  GREEN='' RED='' DIM='' BOLD='' RESET=''
fi

PASSED=0
FAILED=0
FAILURES=()

cleanup() {
  [[ -n "$SUB_PID" ]] && kill "$SUB_PID" 2>/dev/null
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

# ------------------------------------------------------------------ helpers

die() {
  printf '%sError:%s %s\n' "$RED" "$RESET" "$1" >&2
  exit 2
}

section() { printf '\n%s%s%s\n' "$BOLD" "$1" "$RESET"; }

pass() {
  PASSED=$((PASSED + 1))
  printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"
}

fail() {
  FAILED=$((FAILED + 1))
  FAILURES+=("$1")
  printf '  %s✗%s %s\n' "$RED" "$RESET" "$1"
  [[ -n "${2:-}" ]] && printf '      %s%s%s\n' "$DIM" "$2" "$RESET"
}

expect_eq() { # <description> <expected> <actual>
  if [[ "$3" == "$2" ]]; then pass "$1"; else fail "$1" "expected: $2 | actual: $3"; fi
}

expect_contains() { # <description> <snippet> <text>
  if [[ "$3" == *"$2"* ]]; then pass "$1"; else fail "$1" "not found: $2 | in: $3"; fi
}

# json_get <json> <path>: value at the path (e.g. data.id, *.id, lines.#). Missing -> <missing>.
json_get() {
  "$API_PY" -I - "$2" "$1" <<'PY'
import json, sys

path, raw = sys.argv[1], sys.argv[2]

def walk(cur, parts):
    if not parts:
        return cur
    head, rest = parts[0], parts[1:]
    if head == "#":
        return len(cur)
    if head == "*":
        return [walk(item, rest) for item in cur]
    if isinstance(cur, list):
        return walk(cur[int(head)], rest)
    return walk(cur[head], rest)

try:
    value = walk(json.loads(raw), [] if path == "" else path.split("."))
except (ValueError, KeyError, IndexError, TypeError):
    print("<missing>")
    sys.exit(0)

def fmt(v):
    return "true" if v is True else "false" if v is False else "null" if v is None else v

print(" ".join(str(fmt(i)) for i in value) if isinstance(value, list) else fmt(value))
PY
}

# http <METHOD> <path> [json]  ->  $STATUS and $BODY
http() {
  local method=$1 path=$2 payload=${3:-}
  local args=(-s -o "$WORKDIR/body" -w '%{http_code}' --max-time "$TIMEOUT" -X "$method" "$API_URL$path")
  [[ -n "$payload" ]] && args+=(-H 'Content-Type: application/json' -d "$payload")
  STATUS="$(curl "${args[@]}" 2>/dev/null)" || STATUS="000"
  BODY="$(cat "$WORKDIR/body" 2>/dev/null)"
}

# nats_req <subject> <json>  ->  core envelope in $NRESP
nats_req() {
  NRESP="$(nats request "$1" "$2" --timeout "${TIMEOUT}s" --raw 2>/dev/null)" || NRESP="<no response>"
}

# The `data` of the core envelope (compact, sorted JSON).
nats_data() {
  "$API_PY" -I -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["data"], sort_keys=True))' "$NRESP" 2>/dev/null
}

# Normalized HTTP body, to compare with nats_data.
http_body_norm() {
  "$API_PY" -I -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1]), sort_keys=True))' "$BODY" 2>/dev/null
}

# validate <type>: validates $BODY against an api DTO (e.g. PromptResponse, list[PromptVersionResponse]).
validate() {
  local label=$1 spec=$2 out
  out="$("$API_PY" -I - "$API_DIR" "$spec" "$BODY" <<'PY' 2>&1
import json, sys
sys.path.insert(0, sys.argv[1])
from pydantic import TypeAdapter, ValidationError
from models import response_models as m

adapter = TypeAdapter(eval(sys.argv[2], vars(m)))
try:
    adapter.validate_python(json.loads(sys.argv[3]))
except (ValidationError, ValueError) as exc:
    print(str(exc).splitlines()[0:4])
    sys.exit(1)
PY
)" && pass "$label -> body valid as $spec" || fail "$label -> body valid as $spec" "$out | body: $BODY"
}

# same_as_core <description> <subject> <json>: current HTTP body == data of the same query sent to NATS.
same_as_core() {
  local label=$1 http_norm
  http_norm="$(http_body_norm)"
  nats_req "$2" "$3"
  expect_eq "$label -> HTTP identical to the core data on NATS" "$(nats_data)" "$http_norm"
}

expect_ok() { expect_eq "$1 -> HTTP 200" "200" "$STATUS"; }

expect_error() { # <description> <status> <code>
  expect_eq "$1 -> HTTP $2" "$2" "$STATUS"
  expect_eq "$1 -> code $3" "$3" "$(json_get "$BODY" error.code)"
}

wait_for_text() { # <file> <text> [attempts of 0.1s]
  local file=$1 text=$2 tries=${3:-30}
  for ((i = 0; i < tries; i++)); do
    grep -qF -- "$text" "$file" 2>/dev/null && return 0
    sleep 0.1
  done
  return 1
}

# ------------------------------------------------------------------ prerequisites

command -v curl >/dev/null || die "curl not found in PATH"
command -v nats >/dev/null || die "NATS CLI not found in PATH"
[[ -x "$API_PY" ]] || die "api virtualenv not found ($API_PY). Run: (cd api && uv sync)"

nats pub _smoke.ping ping >/dev/null 2>&1 \
  || die "cannot connect to NATS at $NATS_URL (cd core && docker compose up -d)"

nats_req prompt.list.active '{}'
[[ "$(json_get "$NRESP" ok)" == "true" ]] \
  || die "the core did not answer on prompt.list.active (cd core && uv run src/main.py). Response: $NRESP"

http GET /prompts/active
[[ "$STATUS" == "000" ]] && die "cannot connect to the api at $API_URL (cd api && uv run uvicorn main:app)"
[[ "$STATUS" == "200" ]] \
  || die "GET /prompts/active returned HTTP $STATUS. Body: $BODY"

printf '%sprompt-vault global smoke test%s  %s(API: %s, NATS: %s, run: %s)%s\n' \
  "$BOLD" "$RESET" "$DIM" "$API_URL" "$NATS_URL" "$RUN_ID" "$RESET"

nats sub 'prompt.events.>' >"$EVENTS_LOG" 2>&1 &
SUB_PID=$!
wait_for_text "$EVENTS_LOG" "Subscribing on" || die "could not subscribe to prompt.events.>"

# ------------------------------------------------------------------ conectividade

section "Connectivity (HTTP -> NATS -> core)"

pass "NATS answers at $NATS_URL"
pass "core answers via NATS (prompt.list.active)"
pass "api answers over HTTP (GET /prompts/active)"

# ------------------------------------------------------------------ fluxo HTTP + contrato

section "Flow over HTTP: contract validated with the api DTOs"

http POST /prompts "{\"name\":\"global-smoke-$RUN_ID\",\"content\":\"Hello\\nworld\"}"
expect_ok "POST /prompts"
validate "POST /prompts" PromptResponse
PID="$(json_get "$BODY" id)"
[[ "$PID" =~ ^[0-9a-f-]{36}$ ]] || { fail "POST /prompts -> id" "body: $BODY"; die "no id, cannot continue"; }
V1_ID="$(json_get "$BODY" active_version_id)"

http POST "/prompts/$PID/versions" '{"content":"Hi\nworld"}'
expect_ok "POST /prompts/{id}/versions"
validate "POST versions" PromptVersionResponse

http PUT "/prompts/$PID/content" '{"content":"Hey\nworld\nend"}'
expect_ok "PUT /prompts/{id}/content"
validate "PUT content" PromptVersionResponse
V3_ID="$(json_get "$BODY" id)"

http GET "/prompts/$PID"
expect_ok "GET /prompts/{id}"
validate "GET prompt" PromptDetailResponse
expect_eq "GET prompt -> active_version_id is the one of version 3" "$V3_ID" "$(json_get "$BODY" active_version_id)"
same_as_core "GET prompt" prompt.get "{\"prompt_id\":\"$PID\"}"

http GET "/prompts/$PID/versions"
expect_ok "GET /prompts/{id}/versions"
validate "GET versions" "list[PromptVersionResponse]"
same_as_core "GET versions" prompt.versions.list "{\"prompt_id\":\"$PID\"}"

http POST "/prompts/$PID/activate" '{"version_number":1}'
expect_ok "POST /prompts/{id}/activate"
validate "POST activate" PromptResponse
expect_eq "POST activate -> active_version_id is the one of version 1" "$V1_ID" "$(json_get "$BODY" active_version_id)"

http POST "/prompts/$PID/compare" '{"from_version":1,"to_version":3}'
expect_ok "POST /prompts/{id}/compare"
validate "POST compare" VersionDiffResponse
expect_eq "POST compare -> version ids" "$V1_ID $V3_ID" "$(json_get "$BODY" version_id_before) $(json_get "$BODY" version_id_after)"
same_as_core "POST compare" prompt.versions.compare "{\"prompt_id\":\"$PID\",\"from_version\":1,\"to_version\":3}"

http GET /prompts/active
expect_ok "GET /prompts/active"
validate "GET active" "list[PromptResponse]"
expect_contains "GET active -> contains the prompt" "$PID" "$(json_get "$BODY" '*.id')"
same_as_core "GET active" prompt.list.active '{}'

http DELETE "/prompts/$PID"
expect_ok "DELETE /prompts/{id}"
validate "DELETE" PromptResponse
expect_eq "DELETE -> status deleted" "deleted" "$(json_get "$BODY" status)"

http GET /prompts/deleted
expect_ok "GET /prompts/deleted"
validate "GET deleted" "list[PromptResponse]"
expect_contains "GET deleted -> contains the prompt" "$PID" "$(json_get "$BODY" '*.id')"
same_as_core "GET deleted" prompt.list.deleted '{}'

http POST "/prompts/$PID/recover"
expect_ok "POST /prompts/{id}/recover"
validate "POST recover" PromptResponse
expect_eq "POST recover -> status active" "active" "$(json_get "$BODY" status)"

# ------------------------------------------------------------------ os dois lados enxergam o mesmo estado

section "Same state on both sides"

nats_req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt created over HTTP exists in the core (NATS)" "$PID" "$(json_get "$NRESP" data.id)"

nats_req prompt.create "{\"name\":\"global-smoke-nats-$RUN_ID\",\"content\":\"via nats\"}"
NATS_PID="$(json_get "$NRESP" data.id)"
[[ "$NATS_PID" =~ ^[0-9a-f-]{36}$ ]] && pass "prompt created straight on NATS ($NATS_PID)" \
  || fail "prompt created straight on NATS" "response: $NRESP"
http GET "/prompts/$NATS_PID"
expect_ok "GET prompt created on NATS"
expect_eq "prompt created on NATS is visible over HTTP" "global-smoke-nats-$RUN_ID" "$(json_get "$BODY" name)"

section "Domain events (prompt.events.>)"

wait_for_text "$EVENTS_LOG" "$PID" || true
EVENTS="$(cat "$EVENTS_LOG")"
for name in created version_added version_activated deleted restored; do
  expect_contains "creating/changing over HTTP published prompt.events.$name" "prompt.events.$name" "$EVENTS"
done
expect_contains "events reference the prompt created over HTTP" "$PID" "$EVENTS"

# ------------------------------------------------------------------ erros

section "Core errors reach HTTP (standardized format)"

RANDOM_UUID="$("$API_PY" -I -c 'import uuid; print(uuid.uuid4())')"

http GET "/prompts/$RANDOM_UUID"
expect_error "unknown prompt" 404 PROMPT_NOT_FOUND
expect_eq "error -> details present" "{}" "$(json_get "$BODY" error.details)"

http POST "/prompts/$PID/activate" '{"version_number":99}'
expect_error "unknown version" 404 VERSION_NOT_FOUND

http POST "/prompts/$PID/compare" '{"from_version":2,"to_version":2}'
expect_error "comparing a version with itself" 422 INVALID_VERSION_COMPARISON

http POST "/prompts/$PID/recover"
expect_error "restoring a prompt that is not deleted" 409 PROMPT_NOT_DELETED

http POST /prompts '{"name":"   ","content":"x"}'
expect_error "blank name" 409 DOMAIN_RULE_VIOLATION

http GET /prompts/not-a-uuid
expect_error "invalid UUID (rejected by the api, never reaches the core)" 422 INVALID_REQUEST

http POST /prompts '{"name":"no content"}'
expect_error "incomplete body (rejected by the api)" 422 INVALID_REQUEST

# cleanup: the test prompts end up deleted (soft delete)
http DELETE "/prompts/$PID"
http DELETE "/prompts/$NATS_PID"

# ------------------------------------------------------------------ resultado

TOTAL=$((PASSED + FAILED))
printf '\n%s== Result ==%s\n' "$BOLD" "$RESET"
printf 'Total: %d | %sPassed: %d%s | %sFailed: %d%s\n' \
  "$TOTAL" "$GREEN" "$PASSED" "$RESET" "$RED" "$FAILED" "$RESET"

if ((FAILED > 0)); then
  printf '\nFailed:\n'
  for item in "${FAILURES[@]}"; do printf '  - %s\n' "$item"; done
  exit 1
fi
printf '%sAll good.%s\n' "$GREEN" "$RESET"
