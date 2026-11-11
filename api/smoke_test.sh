#!/usr/bin/env bash
# Smoke test of the prompt-vault HTTP API, using only curl and python3.
# It walks through the whole flow HTTP -> NATS -> core -> SQLite.
#
# Prerequisites: NATS, core and API running.
#   (core)  docker compose up -d && uv run src/main.py
#   (api)   uv run uvicorn main:app
#
# Usage: ./smoke_test.sh
# Variables: API_URL (http://localhost:8000), SMOKE_TIMEOUT (10s per request)
# Side effect: creates prompts "api-smoke-<id>" in the core database (they end up deleted).
#
# The checks validate status 200, the DTO fields (PromptResponse, PromptVersionResponse,
# VersionDiffResponse...) and the standardized error format.

set -uo pipefail

API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT="${SMOKE_TIMEOUT:-10}"
RUN_ID="$(date +%s)-$RANDOM"
WORKDIR="$(mktemp -d)"
STATUS=""
BODY=""

if [[ -t 1 ]]; then
  GREEN=$'\033[32m' RED=$'\033[31m' DIM=$'\033[2m' BOLD=$'\033[1m' RESET=$'\033[0m'
else
  GREEN='' RED='' DIM='' BOLD='' RESET=''
fi

PASSED=0
FAILED=0
FAILURES=()

trap 'rm -rf "$WORKDIR"' EXIT

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
  if [[ "$3" == "$2" ]]; then pass "$1"; else fail "$1" "expected: $2 | actual: $3 | body: $BODY"; fi
}

expect_contains() { # <description> <snippet> <text>
  if [[ "$3" == *"$2"* ]]; then pass "$1"; else fail "$1" "not found: $2 | in: $3"; fi
}

# Reads $BODY (JSON) and prints the value at the path. E.g. error.code, versions.#, *.id
# '#' = list length, '*' = every item (space separated). Missing -> <missing>.
json_get() {
  python3 - "$1" "$BODY" <<'PY'
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

# call <METHOD> <path> [json]  ->  $STATUS and $BODY
call() {
  local method=$1 path=$2 payload=${3:-}
  local args=(-s -o "$WORKDIR/body" -w '%{http_code}' --max-time "$TIMEOUT" -X "$method" "$API_URL$path")
  [[ -n "$payload" ]] && args+=(-H 'Content-Type: application/json' -d "$payload")
  STATUS="$(curl "${args[@]}" 2>/dev/null)" || STATUS="000"
  BODY="$(cat "$WORKDIR/body" 2>/dev/null)"
}

expect_ok() { # <description>  (status 200)
  expect_eq "$1 -> HTTP 200" "200" "$STATUS"
}

expect_error() { # <description> <status> <code>
  expect_eq "$1 -> HTTP $2" "$2" "$STATUS"
  expect_eq "$1 -> code $3" "$3" "$(json_get error.code)"
}

# ------------------------------------------------------------------ prerequisites

command -v curl >/dev/null || die "curl not found in PATH"
command -v python3 >/dev/null || die "python3 not found in PATH"

call GET /prompts/active
[[ "$STATUS" == "000" ]] && die "cannot connect to the API at $API_URL (uv run uvicorn main:app)"
[[ "$STATUS" == "200" ]] \
  || die "GET /prompts/active returned HTTP $STATUS (are NATS and the core up?). Body: $BODY"

printf '%sprompt-vault API smoke test%s  %s(API: %s, run: %s)%s\n' \
  "$BOLD" "$RESET" "$DIM" "$API_URL" "$RUN_ID" "$RESET"

# ------------------------------------------------------------------ fluxo principal

section "Prompts and versions"

call POST /prompts "{\"name\":\"api-smoke-$RUN_ID\",\"content\":\"Hello\\nworld\"}"
expect_ok "POST /prompts"
PID="$(json_get id)"
[[ "$PID" =~ ^[0-9a-f-]{36}$ ]] && pass "POST /prompts -> id is a UUID ($PID)" \
  || { fail "POST /prompts -> id is a UUID" "body: $BODY"; die "no id, cannot continue"; }
expect_eq "POST /prompts -> status active" "active" "$(json_get status)"
expect_eq "POST /prompts -> returns the content" "$(printf 'Hello\nworld')" "$(json_get content)"
V1_ID="$(json_get active_version_id)"
[[ "$V1_ID" =~ ^[0-9a-f-]{36}$ ]] && pass "POST /prompts -> active_version_id is a UUID" \
  || fail "POST /prompts -> active_version_id is a UUID" "actual: $V1_ID"

call POST "/prompts/$PID/versions" '{"content":"Hi\nworld"}'
expect_ok "POST /prompts/{id}/versions"
expect_eq "POST versions -> version_number 2" "2" "$(json_get version_number)"
expect_eq "POST versions -> prompt_id" "$PID" "$(json_get prompt_id)"
expect_eq "POST versions -> is_active false" "false" "$(json_get is_active)"

call PUT "/prompts/$PID/content" '{"content":"Hey\nworld\nend"}'
expect_ok "PUT /prompts/{id}/content"
expect_eq "PUT content -> version_number 3" "3" "$(json_get version_number)"
expect_eq "PUT content -> is_active true" "true" "$(json_get is_active)"
V3_ID="$(json_get id)"

call GET "/prompts/$PID"
expect_ok "GET /prompts/{id}"
expect_eq "GET prompt -> id" "$PID" "$(json_get id)"
expect_eq "GET prompt -> 3 versions" "3" "$(json_get versions.#)"
expect_eq "GET prompt -> active_version_id is the one of version 3" "$V3_ID" "$(json_get active_version_id)"

call GET "/prompts/$PID/versions"
expect_ok "GET /prompts/{id}/versions"
expect_eq "GET versions -> array with 3 versions" "3" "$(json_get '#')"
expect_eq "GET versions -> numbers" "1 2 3" "$(json_get '*.version_number')"

call POST "/prompts/$PID/activate" '{"version_number":1}'
expect_ok "POST /prompts/{id}/activate"
expect_eq "POST activate -> returns the prompt with version 1 active" "$V1_ID" "$(json_get active_version_id)"

call POST "/prompts/$PID/compare" '{"from_version":1,"to_version":3}'
expect_ok "POST /prompts/{id}/compare"
expect_eq "POST compare -> has_changes" "true" "$(json_get has_changes)"
expect_eq "POST compare -> version ids" "$V1_ID $V3_ID" "$(json_get version_id_before) $(json_get version_id_after)"
expect_eq "POST compare -> line kinds" "removed added unchanged added" "$(json_get 'lines.*.kind')"

section "Listings, delete and recover"

call GET /prompts/active
expect_ok "GET /prompts/active"
expect_contains "GET /prompts/active -> array with the prompt" "$PID" "$(json_get '*.id')"

call DELETE "/prompts/$PID"
expect_ok "DELETE /prompts/{id}"
expect_eq "DELETE -> returns the deleted prompt" "deleted" "$(json_get status)"

call GET /prompts/deleted
expect_ok "GET /prompts/deleted"
expect_contains "GET /prompts/deleted -> array with the prompt" "$PID" "$(json_get '*.id')"

call POST "/prompts/$PID/recover"
expect_ok "POST /prompts/{id}/recover"
expect_eq "POST recover -> returns the active prompt" "active" "$(json_get status)"

# ------------------------------------------------------------------ erros

section "Errors (standardized format: error.code, error.message, error.details)"

RANDOM_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

call GET "/prompts/$RANDOM_UUID"
expect_error "unknown prompt" 404 PROMPT_NOT_FOUND
expect_eq "error carries message" "true" "$([[ "$(json_get error.message)" != "<missing>" ]] && echo true || echo false)"
expect_eq "error carries details" "{}" "$(json_get error.details)"

call GET /prompts/not-a-uuid
expect_error "invalid UUID in the path" 422 INVALID_REQUEST

call POST /prompts '{"name":"no content"}'
expect_error "body without a required field" 422 INVALID_REQUEST

call POST "/prompts/$PID/activate" '{"version_number":99}'
expect_error "activating an unknown version" 404 VERSION_NOT_FOUND

call POST "/prompts/$PID/compare" '{"from_version":2,"to_version":2}'
expect_error "comparing a version with itself" 422 INVALID_VERSION_COMPARISON

call POST "/prompts/$PID/recover"
expect_error "recovering a prompt that is not deleted" 409 PROMPT_NOT_DELETED

call POST /prompts '{"name":"   ","content":"x"}'
expect_eq "blank name -> HTTP 409" "409" "$STATUS"

# cleanup: the test prompt ends up deleted (soft delete), leaving no active garbage
call DELETE "/prompts/$PID"

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
