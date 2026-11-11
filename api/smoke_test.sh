#!/usr/bin/env bash
# Smoke test da API HTTP do prompt-vault, usando apenas curl e python3.
# Percorre o fluxo completo HTTP -> NATS -> core -> SQLite.
#
# Pré-requisitos: NATS, core e API rodando.
#   (core)  docker compose up -d && uv run src/main.py
#   (api)   uv run uvicorn main:app
#
# Uso: ./smoke_test.sh
# Variáveis: API_URL (http://localhost:8000), SMOKE_TIMEOUT (10s por requisição)
# Efeito colateral: cria prompts "api-smoke-<id>" no banco do core (ficam deletados no fim).
#
# Os checks validam status 200, os campos dos DTOs (PromptResponse, PromptVersionResponse,
# VersionDiffResponse...) e o formato padronizado dos erros.

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
  if [[ "$3" == "$2" ]]; then pass "$1"; else fail "$1" "esperado: $2 | obtido: $3 | corpo: $BODY"; fi
}

expect_contains() { # <descrição> <trecho> <texto>
  if [[ "$3" == *"$2"* ]]; then pass "$1"; else fail "$1" "não encontrado: $2 | em: $3"; fi
}

# Lê $BODY (JSON) e imprime o valor do caminho. Ex.: error.code, versions.#, *.id
# '#' = tamanho da lista, '*' = todos os itens (separados por espaço). Ausente -> <ausente>.
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
    print("<ausente>")
    sys.exit(0)

def fmt(v):
    return "true" if v is True else "false" if v is False else "null" if v is None else v

print(" ".join(str(fmt(i)) for i in value) if isinstance(value, list) else fmt(value))
PY
}

# call <METHOD> <path> [json]  ->  $STATUS e $BODY
call() {
  local method=$1 path=$2 payload=${3:-}
  local args=(-s -o "$WORKDIR/body" -w '%{http_code}' --max-time "$TIMEOUT" -X "$method" "$API_URL$path")
  [[ -n "$payload" ]] && args+=(-H 'Content-Type: application/json' -d "$payload")
  STATUS="$(curl "${args[@]}" 2>/dev/null)" || STATUS="000"
  BODY="$(cat "$WORKDIR/body" 2>/dev/null)"
}

expect_ok() { # <descrição>  (status 200)
  expect_eq "$1 -> HTTP 200" "200" "$STATUS"
}

expect_error() { # <descrição> <status> <código>
  expect_eq "$1 -> HTTP $2" "$2" "$STATUS"
  expect_eq "$1 -> código $3" "$3" "$(json_get error.code)"
}

# ------------------------------------------------------------------ pré-requisitos

command -v curl >/dev/null || die "curl não encontrado no PATH"
command -v python3 >/dev/null || die "python3 não encontrado no PATH"

call GET /prompts/active
[[ "$STATUS" == "000" ]] && die "sem conexão com a API em $API_URL (uv run uvicorn main:app)"
[[ "$STATUS" == "200" ]] \
  || die "GET /prompts/active devolveu HTTP $STATUS (NATS e core estão no ar?). Corpo: $BODY"

printf '%sprompt-vault API smoke test%s  %s(API: %s, run: %s)%s\n' \
  "$BOLD" "$RESET" "$DIM" "$API_URL" "$RUN_ID" "$RESET"

# ------------------------------------------------------------------ fluxo principal

section "Prompts e versões"

call POST /prompts "{\"name\":\"api-smoke-$RUN_ID\",\"content\":\"Ola\\nmundo\"}"
expect_ok "POST /prompts"
PID="$(json_get id)"
[[ "$PID" =~ ^[0-9a-f-]{36}$ ]] && pass "POST /prompts -> id é um UUID ($PID)" \
  || { fail "POST /prompts -> id é um UUID" "corpo: $BODY"; die "sem id, não dá para continuar"; }
expect_eq "POST /prompts -> status active" "active" "$(json_get status)"
expect_eq "POST /prompts -> devolve o content" "$(printf 'Ola\nmundo')" "$(json_get content)"
V1_ID="$(json_get active_version_id)"
[[ "$V1_ID" =~ ^[0-9a-f-]{36}$ ]] && pass "POST /prompts -> active_version_id é um UUID" \
  || fail "POST /prompts -> active_version_id é um UUID" "obtido: $V1_ID"

call POST "/prompts/$PID/versions" '{"content":"Oi\nmundo"}'
expect_ok "POST /prompts/{id}/versions"
expect_eq "POST versions -> version_number 2" "2" "$(json_get version_number)"
expect_eq "POST versions -> prompt_id" "$PID" "$(json_get prompt_id)"
expect_eq "POST versions -> is_active false" "false" "$(json_get is_active)"

call PUT "/prompts/$PID/content" '{"content":"E ai\nmundo\nfim"}'
expect_ok "PUT /prompts/{id}/content"
expect_eq "PUT content -> version_number 3" "3" "$(json_get version_number)"
expect_eq "PUT content -> is_active true" "true" "$(json_get is_active)"
V3_ID="$(json_get id)"

call GET "/prompts/$PID"
expect_ok "GET /prompts/{id}"
expect_eq "GET prompt -> id" "$PID" "$(json_get id)"
expect_eq "GET prompt -> 3 versões" "3" "$(json_get versions.#)"
expect_eq "GET prompt -> active_version_id é o da versão 3" "$V3_ID" "$(json_get active_version_id)"

call GET "/prompts/$PID/versions"
expect_ok "GET /prompts/{id}/versions"
expect_eq "GET versions -> array com 3 versões" "3" "$(json_get '#')"
expect_eq "GET versions -> números" "1 2 3" "$(json_get '*.version_number')"

call POST "/prompts/$PID/activate" '{"version_number":1}'
expect_ok "POST /prompts/{id}/activate"
expect_eq "POST activate -> devolve o prompt com a versão 1 ativa" "$V1_ID" "$(json_get active_version_id)"

call POST "/prompts/$PID/compare" '{"from_version":1,"to_version":3}'
expect_ok "POST /prompts/{id}/compare"
expect_eq "POST compare -> has_changes" "true" "$(json_get has_changes)"
expect_eq "POST compare -> ids das versões" "$V1_ID $V3_ID" "$(json_get version_id_before) $(json_get version_id_after)"
expect_eq "POST compare -> tipos das linhas" "removed added unchanged added" "$(json_get 'lines.*.kind')"

section "Listagens, delete e recover"

call GET /prompts/active
expect_ok "GET /prompts/active"
expect_contains "GET /prompts/active -> array com o prompt" "$PID" "$(json_get '*.id')"

call DELETE "/prompts/$PID"
expect_ok "DELETE /prompts/{id}"
expect_eq "DELETE -> devolve o prompt deleted" "deleted" "$(json_get status)"

call GET /prompts/deleted
expect_ok "GET /prompts/deleted"
expect_contains "GET /prompts/deleted -> array com o prompt" "$PID" "$(json_get '*.id')"

call POST "/prompts/$PID/recover"
expect_ok "POST /prompts/{id}/recover"
expect_eq "POST recover -> devolve o prompt active" "active" "$(json_get status)"

# ------------------------------------------------------------------ erros

section "Erros (formato padronizado: error.code, error.message, error.details)"

RANDOM_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

call GET "/prompts/$RANDOM_UUID"
expect_error "prompt inexistente" 404 PROMPT_NOT_FOUND
expect_eq "erro traz message" "true" "$([[ "$(json_get error.message)" != "<ausente>" ]] && echo true || echo false)"
expect_eq "erro traz details" "{}" "$(json_get error.details)"

call GET /prompts/nao-e-uuid
expect_error "UUID inválido no path" 422 INVALID_REQUEST

call POST /prompts '{"name":"sem conteudo"}'
expect_error "corpo sem campo obrigatório" 422 INVALID_REQUEST

call POST "/prompts/$PID/activate" '{"version_number":99}'
expect_error "ativar versão inexistente" 404 VERSION_NOT_FOUND

call POST "/prompts/$PID/compare" '{"from_version":2,"to_version":2}'
expect_error "comparar a mesma versão" 422 INVALID_VERSION_COMPARISON

call POST "/prompts/$PID/recover"
expect_error "recuperar prompt que não está deletado" 409 PROMPT_NOT_DELETED

call POST /prompts '{"name":"   ","content":"x"}'
expect_eq "nome em branco -> HTTP 409" "409" "$STATUS"

# limpeza: o prompt do teste volta a ficar deletado (soft delete), sem lixo ativo
call DELETE "/prompts/$PID"

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
