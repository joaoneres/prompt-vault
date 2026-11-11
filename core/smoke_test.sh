#!/usr/bin/env bash
# Smoke test dos subjects NATS do prompt-vault, usando apenas o NATS CLI.
#
# Pré-requisitos: NATS e o app rodando.
#   docker compose up -d
#   uv run src/main.py
#
# Uso: ./smoke_test.sh
# Variáveis: NATS_URL (nats://localhost:4222), SMOKE_TIMEOUT (3s)
# Efeito colateral: cria prompts com nome "smoke-<id>" no banco do app.

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
  printf '%sErro:%s %s\n' "$RED" "$RESET" "$1" >&2
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

expect_eq() { # <descrição> <esperado> <obtido>
  if [[ "$3" == "$2" ]]; then pass "$1"; else fail "$1" "esperado: $2 | obtido: $3"; fi
}

expect_contains() { # <descrição> <trecho> <texto>
  if [[ "$3" == *"$2"* ]]; then pass "$1"; else fail "$1" "não encontrado: $2 | em: $3"; fi
}

# Lê $RESP (JSON) e imprime o valor do caminho. Ex.: data.prompt_id, data.versions.#
# '#' = tamanho da lista, '*' = todos os itens da lista (separados por espaço).
json_get() {
  python3 - "$1" "$RESP" <<'PY'
import json, sys

path, raw = sys.argv[1], sys.argv[2]
try:
    cur = json.loads(raw)
except ValueError:
    print("<resposta não é JSON>")
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
    print("<ausente>")
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

# req <subject> <json> [correlation_id]  ->  resposta em $RESP
req() {
  local subject=$1 payload=$2 cid=${3:-}
  local args=(request "$subject" "$payload" --timeout "$TIMEOUT" --raw)
  [[ -n "$cid" ]] && args+=(-H "X-Correlation-Id:$cid")
  RESP="$(nats "${args[@]}" 2>/dev/null)" || RESP="<sem resposta em $TIMEOUT>"
}

# pub <subject> <json> [correlation_id]  (fire-and-forget, sem reply)
pub() {
  local subject=$1 payload=$2 cid=${3:-}
  local args=(pub "$subject" "$payload")
  [[ -n "$cid" ]] && args+=(-H "X-Correlation-Id:$cid")
  nats "${args[@]}" >/dev/null 2>&1
}

start_sub() { # <subject> <arquivo>
  nats sub "$1" >"$2" 2>&1 &
  SUB_PIDS+=("$!")
  wait_for_text "$2" "Subscribing on" || die "não consegui assinar $1"
}

wait_for_text() { # <arquivo> <texto> [tentativas de 0,1s]
  local file=$1 text=$2 tries=${3:-30}
  for ((i = 0; i < tries; i++)); do
    grep -qF -- "$text" "$file" 2>/dev/null && return 0
    sleep 0.1
  done
  return 1
}

# ------------------------------------------------------------------ pré-requisitos

command -v nats >/dev/null || die "NATS CLI não encontrado no PATH"
command -v python3 >/dev/null || die "python3 não encontrado no PATH"

nats pub _smoke.ping ping >/dev/null 2>&1 \
  || die "sem conexão com o NATS em $NATS_URL (docker compose up -d)"

req prompt.list.active '{}'
[[ "$(json_get ok)" == "true" ]] \
  || die "o app não respondeu em prompt.list.active (uv run src/main.py). Resposta: $RESP"

printf '%sprompt-vault smoke test%s  %s(NATS: %s, run: %s)%s\n' \
  "$BOLD" "$RESET" "$DIM" "$NATS_URL" "$RUN_ID" "$RESET"

start_sub 'prompt.events.>' "$EVENTS_LOG"
start_sub 'prompt.errors' "$ERRORS_LOG"

# ------------------------------------------------------------------ commands + queries

CID="smoke-$RUN_ID"

section "Commands (request/reply)"

req prompt.create "{\"name\":\"smoke-$RUN_ID\",\"content\":\"Ola\\nmundo\"}" "$CID"
expect_eq "prompt.create -> ok" "true" "$(json_get ok)"
expect_eq "prompt.create -> devolve o correlation id enviado" "$CID" "$(json_get correlation_id)"
PID="$(json_get data.id)"
[[ "$PID" =~ ^[0-9a-f-]{36}$ ]] && pass "prompt.create -> id é um UUID ($PID)" \
  || fail "prompt.create -> id é um UUID" "obtido: $PID"
expect_eq "prompt.create -> status active" "active" "$(json_get data.status)"
expect_eq "prompt.create -> devolve o content" "$(printf 'Ola\nmundo')" "$(json_get data.content)"
V1_ID="$(json_get data.active_version_id)"
[[ "$V1_ID" =~ ^[0-9a-f-]{36}$ ]] && pass "prompt.create -> active_version_id é um UUID" \
  || fail "prompt.create -> active_version_id é um UUID" "obtido: $V1_ID"

req prompt.version.create "{\"prompt_id\":\"$PID\",\"content\":\"Oi\\nmundo\"}"
expect_eq "prompt.version.create -> versão 2" "2" "$(json_get data.version_number)"
expect_eq "prompt.version.create -> prompt_id" "$PID" "$(json_get data.prompt_id)"
expect_eq "prompt.version.create -> não ativa a nova versão" "false" "$(json_get data.is_active)"

req prompt.content.update "{\"prompt_id\":\"$PID\",\"content\":\"E ai\\nmundo\\nfim\"}"
expect_eq "prompt.content.update -> versão 3" "3" "$(json_get data.version_number)"
expect_eq "prompt.content.update -> versão 3 ativa" "true" "$(json_get data.is_active)"
V3_ID="$(json_get data.id)"

req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> 3 versões" "3" "$(json_get data.versions.#)"
expect_eq "prompt.get -> active_version_id é o da versão 3" "$V3_ID" "$(json_get data.active_version_id)"
expect_eq "prompt.get -> status active" "active" "$(json_get data.status)"

req prompt.version.activate "{\"prompt_id\":\"$PID\",\"version_number\":1}"
expect_eq "prompt.version.activate(1) -> ok" "true" "$(json_get ok)"
expect_eq "prompt.version.activate(1) -> devolve o prompt com a versão 1 ativa" "$V1_ID" "$(json_get data.active_version_id)"
req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> versão 1 ativa após rollback" "$V1_ID" "$(json_get data.active_version_id)"
expect_eq "prompt.get -> histórico preservado (3 versões)" "3" "$(json_get data.versions.#)"

section "Queries (request/reply)"

req prompt.versions.list "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.versions.list -> array com 3 versões" "3" "$(json_get data.#)"
expect_eq "prompt.versions.list -> números das versões" "1 2 3" "$(json_get 'data.*.version_number')"
expect_eq "prompt.versions.list -> só a versão 1 está ativa" "True False False" "$(json_get 'data.*.is_active')"

req prompt.versions.compare "{\"prompt_id\":\"$PID\",\"from_version\":1,\"to_version\":3}"
expect_eq "prompt.versions.compare -> has_changes" "true" "$(json_get data.has_changes)"
expect_eq "prompt.versions.compare -> ids das versões" "$V1_ID $V3_ID" "$(json_get data.version_id_before) $(json_get data.version_id_after)"
expect_eq "prompt.versions.compare -> números das versões" "1 3" "$(json_get data.version_number_before) $(json_get data.version_number_after)"
expect_eq "prompt.versions.compare -> tipos das linhas (modified vira removed + added)" \
  "removed added unchanged added" "$(json_get 'data.lines.*.kind')"

req prompt.list.active '{}'
expect_contains "prompt.list.active -> array com o prompt" "$PID" "$(json_get 'data.*.id')"

section "Soft delete e recuperação"

req prompt.delete "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.delete -> ok" "true" "$(json_get ok)"
expect_eq "prompt.delete -> devolve o prompt deleted" "deleted" "$(json_get data.status)"
req prompt.list.deleted '{}'
expect_contains "prompt.list.deleted -> array com o prompt" "$PID" "$(json_get 'data.*.id')"
req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> status deleted" "deleted" "$(json_get data.status)"
expect_eq "prompt.get -> versões preservadas" "3" "$(json_get data.versions.#)"

req prompt.restore "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.restore -> ok" "true" "$(json_get ok)"
expect_eq "prompt.restore -> devolve o prompt active" "active" "$(json_get data.status)"
req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt.get -> status active após restore" "active" "$(json_get data.status)"

# ------------------------------------------------------------------ erros

section "Erros (código devolvido na resposta)"

RANDOM_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

req prompt.create '{not json'
expect_eq "JSON inválido -> invalid_payload" "invalid_payload" "$(json_get error.code)"
req prompt.create '{"name":"sem conteudo"}'
expect_eq "campo faltando -> invalid_payload" "invalid_payload" "$(json_get error.code)"
req prompt.get '{"prompt_id":"nao-e-uuid"}'
expect_eq "UUID inválido -> invalid_payload" "invalid_payload" "$(json_get error.code)"
req prompt.get "{\"prompt_id\":\"$RANDOM_UUID\"}"
expect_eq "prompt inexistente -> not_found" "not_found" "$(json_get error.code)"
req prompt.version.activate "{\"prompt_id\":\"$PID\",\"version_number\":99}"
expect_eq "versão inexistente -> version_not_found" "version_not_found" "$(json_get error.code)"
req prompt.versions.compare "{\"prompt_id\":\"$PID\",\"from_version\":2,\"to_version\":2}"
expect_eq "comparar a mesma versão -> invalid_version_comparison" "invalid_version_comparison" "$(json_get error.code)"
req prompt.create '{"name":"   ","content":"x"}'
expect_eq "nome em branco -> invalid_prompt" "invalid_prompt" "$(json_get error.code)"
req prompt.restore "{\"prompt_id\":\"$PID\"}"
expect_eq "restaurar prompt que não está deletado -> prompt_not_deleted" "prompt_not_deleted" "$(json_get error.code)"

# ------------------------------------------------------------------ eventos

section "Eventos publicados (prompt.events.>)"

ASYNC_CID="smoke-async-$RUN_ID"
pub prompt.create "{\"name\":\"smoke-async-$RUN_ID\",\"content\":\"x\"}" "$ASYNC_CID"
wait_for_text "$EVENTS_LOG" "$ASYNC_CID" || true

EVENTS="$(cat "$EVENTS_LOG")"
for name in created version_added version_activated deleted restored; do
  expect_contains "evento prompt.events.$name publicado" "prompt.events.$name" "$EVENTS"
done
expect_contains "evento carrega o correlation id da request" "X-Correlation-Id: $CID" "$EVENTS"
expect_contains "command sem reply executou (evento created)" "smoke-async-$RUN_ID" "$EVENTS"
expect_contains "command sem reply mantém o correlation id no evento" "X-Correlation-Id: $ASYNC_CID" "$EVENTS"

section "Command sem reply que falha (prompt.errors)"

ERR_CID="smoke-err-$RUN_ID"
pub prompt.delete "{\"prompt_id\":\"$RANDOM_UUID\"}" "$ERR_CID"
wait_for_text "$ERRORS_LOG" "$ERR_CID" || true
ERRORS="$(cat "$ERRORS_LOG")"
expect_contains "erro publicado em prompt.errors" "not_found" "$ERRORS"
expect_contains "erro traz o correlation id" "$ERR_CID" "$ERRORS"
expect_contains "erro traz o subject de origem" "prompt.delete" "$ERRORS"

section "Query sem reply"

pub prompt.list.active '{}'
sleep 0.3
req prompt.list.active '{}'
expect_eq "app segue saudável após query sem reply" "true" "$(json_get ok)"

# limpeza: o prompt principal volta a ficar deletado (soft delete), sem lixo ativo
req prompt.delete "{\"prompt_id\":\"$PID\"}"

# ------------------------------------------------------------------ resultado

TOTAL=$((PASSED + FAILED))
printf '\n%s== Resultado ==%s\n' "$BOLD" "$RESET"
printf 'Total: %d | %sOK: %d%s | %sFalhas: %d%s\n' \
  "$TOTAL" "$GREEN" "$PASSED" "$RESET" "$RED" "$FAILED" "$RESET"

if ((FAILED > 0)); then
  printf '\nFalharam:\n'
  for item in "${FAILURES[@]}"; do printf '  - %s\n' "$item"; done
  exit 1
fi
printf '%sTudo certo.%s\n' "$GREEN" "$RESET"
