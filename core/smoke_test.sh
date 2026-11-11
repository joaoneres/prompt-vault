#!/usr/bin/env bash
# Smoke test of the prompt-vault NATS subjects, using only the NATS CLI.
#
# Prerequisites: NATS and the app running.
#   docker compose up -d
#   uv run src/main.py
#
# Usage: ./smoke_test.sh
# Variables: NATS_URL (nats://localhost:4222), SMOKE_TIMEOUT (3s)
# Side effect: creates prompts named "smoke-<id>" in the app database.

set -uo pipefail

export NATS_URL="${NATS_URL:-nats://localhost:4222}"
TIMEOUT="${SMOKE_TIMEOUT:-3s}"
RUN_ID="$(date +%s)-$RANDOM"
WORKDIR="$(mktemp -d)"
EVENTS_LOG="$WORKDIR/events.log"
ERRORS_LOG="$WORKDIR/errors.log"
SUB_PIDS=()
RESP=""

if [[ -t 1 ]]; then
  GREEN=$'\033[32m' RED=$'\033[31m' DIM=$'\033[2m' BOLD=$'\033[1m' RESET=$'\033[0m'
else
  GREEN='' RED='' DIM='' BOLD='' RESET=''
fi

PASSED=0
FAILED=0
FAILURES=()

cleanup() {
  for pid in "${SUB_PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null
  done
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

# Reads $RESP (JSON) and prints the value at the path. E.g. data.id, data.versions.#
# '#' = list length, '*' = every item of the list (space separated).
json_get() {
  python3 - "$1" "$RESP" <<'PY'
import json, sys

path, raw = sys.argv[1], sys.argv[2]
try:
    cur = json.loads(raw)
except ValueError:
    print("<response is not JSON>")
    sys.exit(0)

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
    value = walk(cur, path.split("."))
except (KeyError, IndexError, ValueError, TypeError):
    print("<missing>")
    sys.exit(0)

if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print("null")
elif isinstance(value, list):
    print(" ".join(str(item) for item in value))
else:
    print(value)
PY
}

# req <subject> <json> [correlation_id]  ->  response in $RESP
req() {
  local subject=$1 payload=$2 cid=${3:-}
  local args=(request "$subject" "$payload" --timeout "$TIMEOUT" --raw)
  [[ -n "$cid" ]] && args+=(-H "X-Correlation-Id:$cid")
  RESP="$(nats "${args[@]}" 2>/dev/null)" || RESP="<no response within $TIMEOUT>"
}

# pub <subject> <json> [correlation_id]  (fire-and-forget, no reply)
pub() {
  local subject=$1 payload=$2 cid=${3:-}
  local args=(pub "$subject" "$payload")
  [[ -n "$cid" ]] && args+=(-H "X-Correlation-Id:$cid")
  nats "${args[@]}" >/dev/null 2>&1
}

start_sub() { # <subject> <file>
  nats sub "$1" >"$2" 2>&1 &
  SUB_PIDS+=("$!")
  wait_for_text "$2" "Subscribing on" || die "could not subscribe to $1"
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

command -v nats >/dev/null || die "NATS CLI not found in PATH"
command -v python3 >/dev/null || die "python3 not found in PATH"

nats pub _smoke.ping ping >/dev/null 2>&1 \
  || die "cannot connect to NATS at $NATS_URL (docker compose up -d)"

req prompt.list.active '{}'
[[ "$(json_get ok)" == "true" ]] \
  || die "the app did not answer on prompt.list.active (uv run src/main.py). Response: $RESP"

printf '%sprompt-vault smoke test%s  %s(NATS: %s, run: %s)%s\n' \
  "$BOLD" "$RESET" "$DIM" "$NATS_URL" "$RUN_ID" "$RESET"

start_sub 'prompt.events.>' "$EVENTS_LOG"
start_sub 'prompt.errors' "$ERRORS_LOG"

# ------------------------------------------------------------------ commands + queries

CID="smoke-$RUN_ID"

section "Commands (request/reply)"

req prompt.create "{\"name\":\"smoke-$RUN_ID\",\"content\":\"Hello\\nworld\"}" "$CID"
expect_eq "prompt.create -> ok" "true" "$(json_get ok)"
expect_eq "prompt.create -> returns the correlation id that was sent" "$CID" "$(json_get correlation_id)"
PID="$(json_get data.id)"
[[ "$PID" =~ ^[0-9a-f-]{36}$ ]] && pass "prompt.create -> id is a UUID ($PID)" \
  || fail "prompt.create -> id is a UUID" "actual: $PID"
expect_eq "prompt.create -> status active" "active" "$(json_get data.status)"
expect_eq "prompt.create -> returns the content" "$(printf 'Hello\nworld')" "$(json_get data.content)"
V1_ID="$(json_get data.active_version_id)"
[[ "$V1_ID" =~ ^[0-9a-f-]{36}$ ]] && pass "prompt.create -> active_version_id is a UUID" \
  || fail "prompt.create -> active_version_id is a UUID" "actual: $V1_ID"

req prompt.version.create "{\"prompt_id\":\"$PID\",\"content\":\"Hi\\nworld\"}"
expect_eq "prompt.version.create -> version 2" "2" "$(json_get data.version_number)"
expect_eq "prompt.version.create -> prompt_id" "$PID" "$(json_get data.prompt_id)"
expect_eq "prompt.version.create -> does not activate the new version" "false" "$(json_get data.is_active)"

req prompt.content.update "{\"prompt_id\":\"$PID\",\"content\":\"Hey\\nworld\\nend\"}"
expect_eq "prompt.content.update -> version 3" "3" "$(json_get data.version_number)"
expect_eq "prompt.content.update -> version 3 active" "true" "$(json_get data.is_active)"
V3_ID="$(json_get data.id)"

req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> 3 versions" "3" "$(json_get data.versions.#)"
expect_eq "prompt.get -> active_version_id is the one of version 3" "$V3_ID" "$(json_get data.active_version_id)"
expect_eq "prompt.get -> status active" "active" "$(json_get data.status)"

req prompt.version.activate "{\"prompt_id\":\"$PID\",\"version_number\":1}"
expect_eq "prompt.version.activate(1) -> ok" "true" "$(json_get ok)"
expect_eq "prompt.version.activate(1) -> returns the prompt with version 1 active" "$V1_ID" "$(json_get data.active_version_id)"
req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> version 1 active after rollback" "$V1_ID" "$(json_get data.active_version_id)"
expect_eq "prompt.get -> history preserved (3 versions)" "3" "$(json_get data.versions.#)"

section "Queries (request/reply)"

req prompt.versions.list "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.versions.list -> array with 3 versions" "3" "$(json_get data.#)"
expect_eq "prompt.versions.list -> version numbers" "1 2 3" "$(json_get 'data.*.version_number')"
expect_eq "prompt.versions.list -> only version 1 is active" "True False False" "$(json_get 'data.*.is_active')"

req prompt.versions.compare "{\"prompt_id\":\"$PID\",\"from_version\":1,\"to_version\":3}"
expect_eq "prompt.versions.compare -> has_changes" "true" "$(json_get data.has_changes)"
expect_eq "prompt.versions.compare -> version ids" "$V1_ID $V3_ID" "$(json_get data.version_id_before) $(json_get data.version_id_after)"
expect_eq "prompt.versions.compare -> version numbers" "1 3" "$(json_get data.version_number_before) $(json_get data.version_number_after)"
expect_eq "prompt.versions.compare -> line kinds (modified becomes removed + added)" \
  "removed added unchanged added" "$(json_get 'data.lines.*.kind')"

req prompt.list.active '{}'
expect_contains "prompt.list.active -> array with the prompt" "$PID" "$(json_get 'data.*.id')"

section "Soft delete and recovery"

req prompt.delete "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.delete -> ok" "true" "$(json_get ok)"
expect_eq "prompt.delete -> returns the deleted prompt" "deleted" "$(json_get data.status)"
req prompt.list.deleted '{}'
expect_contains "prompt.list.deleted -> array with the prompt" "$PID" "$(json_get 'data.*.id')"
req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> status deleted" "deleted" "$(json_get data.status)"
expect_eq "prompt.get -> versions preserved" "3" "$(json_get data.versions.#)"

req prompt.restore "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.restore -> ok" "true" "$(json_get ok)"
expect_eq "prompt.restore -> returns the active prompt" "active" "$(json_get data.status)"
req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> status active after restore" "active" "$(json_get data.status)"

# ------------------------------------------------------------------ erros

section "Errors (code returned in the response)"

RANDOM_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

req prompt.create '{not json'
expect_eq "invalid JSON -> invalid_payload" "invalid_payload" "$(json_get error.code)"
req prompt.create '{"name":"no content"}'
expect_eq "missing field -> invalid_payload" "invalid_payload" "$(json_get error.code)"
req prompt.get '{"prompt_id":"not-a-uuid"}'
expect_eq "invalid UUID -> invalid_payload" "invalid_payload" "$(json_get error.code)"
req prompt.get "{\"prompt_id\":\"$RANDOM_UUID\"}"
expect_eq "unknown prompt -> not_found" "not_found" "$(json_get error.code)"
req prompt.version.activate "{\"prompt_id\":\"$PID\",\"version_number\":99}"
expect_eq "unknown version -> version_not_found" "version_not_found" "$(json_get error.code)"
req prompt.versions.compare "{\"prompt_id\":\"$PID\",\"from_version\":2,\"to_version\":2}"
expect_eq "comparing a version with itself -> invalid_version_comparison" "invalid_version_comparison" "$(json_get error.code)"
req prompt.create '{"name":"   ","content":"x"}'
expect_eq "blank name -> invalid_prompt" "invalid_prompt" "$(json_get error.code)"
req prompt.restore "{\"prompt_id\":\"$PID\"}"
expect_eq "restoring a prompt that is not deleted -> prompt_not_deleted" "prompt_not_deleted" "$(json_get error.code)"

# ------------------------------------------------------------------ eventos

section "Published events (prompt.events.>)"

ASYNC_CID="smoke-async-$RUN_ID"
pub prompt.create "{\"name\":\"smoke-async-$RUN_ID\",\"content\":\"x\"}" "$ASYNC_CID"
wait_for_text "$EVENTS_LOG" "$ASYNC_CID" || true

EVENTS="$(cat "$EVENTS_LOG")"
for name in created version_added version_activated deleted restored; do
  expect_contains "event prompt.events.$name published" "prompt.events.$name" "$EVENTS"
done
expect_contains "event carries the request correlation id" "X-Correlation-Id: $CID" "$EVENTS"
expect_contains "command without reply ran (created event)" "smoke-async-$RUN_ID" "$EVENTS"
expect_contains "command without reply keeps the correlation id in the event" "X-Correlation-Id: $ASYNC_CID" "$EVENTS"

section "Command without reply that fails (prompt.errors)"

ERR_CID="smoke-err-$RUN_ID"
pub prompt.delete "{\"prompt_id\":\"$RANDOM_UUID\"}" "$ERR_CID"
wait_for_text "$ERRORS_LOG" "$ERR_CID" || true
ERRORS="$(cat "$ERRORS_LOG")"
expect_contains "error published on prompt.errors" "not_found" "$ERRORS"
expect_contains "error carries the correlation id" "$ERR_CID" "$ERRORS"
expect_contains "error carries the source subject" "prompt.delete" "$ERRORS"

section "Query without reply"

pub prompt.list.active '{}'
sleep 0.3
req prompt.list.active '{}'
expect_eq "app stays healthy after a query without reply" "true" "$(json_get ok)"

# cleanup: the main prompt ends up deleted (soft delete), leaving no active garbage
req prompt.delete "{\"prompt_id\":\"$PID\"}"

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
