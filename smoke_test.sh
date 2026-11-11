#!/usr/bin/env bash
# Smoke test global do prompt-vault: prova que HTTP -> api -> NATS -> core -> SQLite funciona
# e que os dois projetos concordam sobre o contrato.
#
# O que ele valida além dos smoke tests de cada projeto:
#   1. os três saltos respondem (NATS, core via NATS, api via HTTP);
#   2. cada corpo HTTP é válido contra os DTOs da api (api/models/response_models.py);
#   3. cada query HTTP devolve exatamente o `data` da mesma query feita direto no NATS
#      (o gateway só transporta);
#   4. um prompt criado por HTTP é visto no NATS e um criado no NATS é visto por HTTP;
#   5. criar por HTTP publica o evento de domínio no NATS (prompt.events.created);
#   6. erros do core chegam ao HTTP com o status e o código padronizados.
#
# Pré-requisitos (nada é iniciado por este script):
#   (core) docker compose up -d && uv run src/main.py
#   (api)  uv run uvicorn main:app          # dentro de api/ (uv sync feito)
#
# Uso: ./smoke_test.sh
# Variáveis: API_URL (http://localhost:8000), NATS_URL (nats://localhost:4222), SMOKE_TIMEOUT (10)
# Efeito colateral: cria prompts "global-smoke-<id>" no banco do core (ficam deletados no fim).

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

# json_get <json> <caminho>: valor no caminho (ex.: data.id, *.id, lines.#). Ausente -> <ausente>.
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
    print("<ausente>")
    sys.exit(0)

def fmt(v):
    return "true" if v is True else "false" if v is False else "null" if v is None else v

print(" ".join(str(fmt(i)) for i in value) if isinstance(value, list) else fmt(value))
PY
}

# http <METHOD> <path> [json]  ->  $STATUS e $BODY
http() {
  local method=$1 path=$2 payload=${3:-}
  local args=(-s -o "$WORKDIR/body" -w '%{http_code}' --max-time "$TIMEOUT" -X "$method" "$API_URL$path")
  [[ -n "$payload" ]] && args+=(-H 'Content-Type: application/json' -d "$payload")
  STATUS="$(curl "${args[@]}" 2>/dev/null)" || STATUS="000"
  BODY="$(cat "$WORKDIR/body" 2>/dev/null)"
}

# nats_req <subject> <json>  ->  envelope do core em $NRESP
nats_req() {
  NRESP="$(nats request "$1" "$2" --timeout "${TIMEOUT}s" --raw 2>/dev/null)" || NRESP="<sem resposta>"
}

# O `data` do envelope do core (JSON compacto e ordenado).
nats_data() {
  "$API_PY" -I -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["data"], sort_keys=True))' "$NRESP" 2>/dev/null
}

# Corpo HTTP normalizado, para comparar com nats_data.
http_body_norm() {
  "$API_PY" -I -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1]), sort_keys=True))' "$BODY" 2>/dev/null
}

# validate <tipo>: valida $BODY contra um DTO da api (ex.: PromptResponse, list[PromptVersionResponse]).
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
)" && pass "$label -> corpo válido como $spec" || fail "$label -> corpo válido como $spec" "$out | corpo: $BODY"
}

# same_as_core <descrição> <subject> <json>: corpo HTTP atual == data da query direta no NATS.
same_as_core() {
  local label=$1 http_norm
  http_norm="$(http_body_norm)"
  nats_req "$2" "$3"
  expect_eq "$label -> HTTP idêntico ao data do core no NATS" "$(nats_data)" "$http_norm"
}

expect_ok() { expect_eq "$1 -> HTTP 200" "200" "$STATUS"; }

expect_error() { # <descrição> <status> <código>
  expect_eq "$1 -> HTTP $2" "$2" "$STATUS"
  expect_eq "$1 -> código $3" "$3" "$(json_get "$BODY" error.code)"
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

command -v curl >/dev/null || die "curl não encontrado no PATH"
command -v nats >/dev/null || die "NATS CLI não encontrado no PATH"
[[ -x "$API_PY" ]] || die "venv da api não encontrado ($API_PY). Rode: (cd api && uv sync)"

nats pub _smoke.ping ping >/dev/null 2>&1 \
  || die "sem conexão com o NATS em $NATS_URL (cd core && docker compose up -d)"

nats_req prompt.list.active '{}'
[[ "$(json_get "$NRESP" ok)" == "true" ]] \
  || die "o core não respondeu em prompt.list.active (cd core && uv run src/main.py). Resposta: $NRESP"

http GET /prompts/active
[[ "$STATUS" == "000" ]] && die "sem conexão com a api em $API_URL (cd api && uv run uvicorn main:app)"
[[ "$STATUS" == "200" ]] \
  || die "GET /prompts/active devolveu HTTP $STATUS. Corpo: $BODY"

printf '%sprompt-vault smoke test global%s  %s(API: %s, NATS: %s, run: %s)%s\n' \
  "$BOLD" "$RESET" "$DIM" "$API_URL" "$NATS_URL" "$RUN_ID" "$RESET"

nats sub 'prompt.events.>' >"$EVENTS_LOG" 2>&1 &
SUB_PID=$!
wait_for_text "$EVENTS_LOG" "Subscribing on" || die "não consegui assinar prompt.events.>"

# ------------------------------------------------------------------ conectividade

section "Conectividade (HTTP -> NATS -> core)"

pass "NATS responde em $NATS_URL"
pass "core responde via NATS (prompt.list.active)"
pass "api responde via HTTP (GET /prompts/active)"

# ------------------------------------------------------------------ fluxo HTTP + contrato

section "Fluxo via HTTP: contrato validado com os DTOs da api"

http POST /prompts "{\"name\":\"global-smoke-$RUN_ID\",\"content\":\"Ola\\nmundo\"}"
expect_ok "POST /prompts"
validate "POST /prompts" PromptResponse
PID="$(json_get "$BODY" id)"
[[ "$PID" =~ ^[0-9a-f-]{36}$ ]] || { fail "POST /prompts -> id" "corpo: $BODY"; die "sem id, não dá para continuar"; }
V1_ID="$(json_get "$BODY" active_version_id)"

http POST "/prompts/$PID/versions" '{"content":"Oi\nmundo"}'
expect_ok "POST /prompts/{id}/versions"
validate "POST versions" PromptVersionResponse

http PUT "/prompts/$PID/content" '{"content":"E ai\nmundo\nfim"}'
expect_ok "PUT /prompts/{id}/content"
validate "PUT content" PromptVersionResponse
V3_ID="$(json_get "$BODY" id)"

http GET "/prompts/$PID"
expect_ok "GET /prompts/{id}"
validate "GET prompt" PromptDetailResponse
expect_eq "GET prompt -> active_version_id é o da versão 3" "$V3_ID" "$(json_get "$BODY" active_version_id)"
same_as_core "GET prompt" prompt.get "{\"prompt_id\":\"$PID\"}"

http GET "/prompts/$PID/versions"
expect_ok "GET /prompts/{id}/versions"
validate "GET versions" "list[PromptVersionResponse]"
same_as_core "GET versions" prompt.versions.list "{\"prompt_id\":\"$PID\"}"

http POST "/prompts/$PID/activate" '{"version_number":1}'
expect_ok "POST /prompts/{id}/activate"
validate "POST activate" PromptResponse
expect_eq "POST activate -> active_version_id é o da versão 1" "$V1_ID" "$(json_get "$BODY" active_version_id)"

http POST "/prompts/$PID/compare" '{"from_version":1,"to_version":3}'
expect_ok "POST /prompts/{id}/compare"
validate "POST compare" VersionDiffResponse
expect_eq "POST compare -> ids das versões" "$V1_ID $V3_ID" "$(json_get "$BODY" version_id_before) $(json_get "$BODY" version_id_after)"
same_as_core "POST compare" prompt.versions.compare "{\"prompt_id\":\"$PID\",\"from_version\":1,\"to_version\":3}"

http GET /prompts/active
expect_ok "GET /prompts/active"
validate "GET active" "list[PromptResponse]"
expect_contains "GET active -> contém o prompt" "$PID" "$(json_get "$BODY" '*.id')"
same_as_core "GET active" prompt.list.active '{}'

http DELETE "/prompts/$PID"
expect_ok "DELETE /prompts/{id}"
validate "DELETE" PromptResponse
expect_eq "DELETE -> status deleted" "deleted" "$(json_get "$BODY" status)"

http GET /prompts/deleted
expect_ok "GET /prompts/deleted"
validate "GET deleted" "list[PromptResponse]"
expect_contains "GET deleted -> contém o prompt" "$PID" "$(json_get "$BODY" '*.id')"
same_as_core "GET deleted" prompt.list.deleted '{}'

http POST "/prompts/$PID/recover"
expect_ok "POST /prompts/{id}/recover"
validate "POST recover" PromptResponse
expect_eq "POST recover -> status active" "active" "$(json_get "$BODY" status)"

# ------------------------------------------------------------------ os dois lados enxergam o mesmo estado

section "Mesmo estado nos dois lados"

nats_req prompt.get "{\"prompt_id\":\"$PID\"}"
expect_eq "prompt criado por HTTP existe no core (NATS)" "$PID" "$(json_get "$NRESP" data.id)"

nats_req prompt.create "{\"name\":\"global-smoke-nats-$RUN_ID\",\"content\":\"via nats\"}"
NATS_PID="$(json_get "$NRESP" data.id)"
[[ "$NATS_PID" =~ ^[0-9a-f-]{36}$ ]] && pass "prompt criado direto no NATS ($NATS_PID)" \
  || fail "prompt criado direto no NATS" "resposta: $NRESP"
http GET "/prompts/$NATS_PID"
expect_ok "GET prompt criado no NATS"
expect_eq "prompt criado no NATS é visível por HTTP" "global-smoke-nats-$RUN_ID" "$(json_get "$BODY" name)"

section "Eventos de domínio (prompt.events.>)"

wait_for_text "$EVENTS_LOG" "$PID" || true
EVENTS="$(cat "$EVENTS_LOG")"
for name in created version_added version_activated deleted restored; do
  expect_contains "criar/alterar por HTTP publicou prompt.events.$name" "prompt.events.$name" "$EVENTS"
done
expect_contains "eventos referenciam o prompt criado por HTTP" "$PID" "$EVENTS"

# ------------------------------------------------------------------ erros

section "Erros do core chegam ao HTTP (formato padronizado)"

RANDOM_UUID="$("$API_PY" -I -c 'import uuid; print(uuid.uuid4())')"

http GET "/prompts/$RANDOM_UUID"
expect_error "prompt inexistente" 404 PROMPT_NOT_FOUND
expect_eq "erro -> details presente" "{}" "$(json_get "$BODY" error.details)"

http POST "/prompts/$PID/activate" '{"version_number":99}'
expect_error "versão inexistente" 404 VERSION_NOT_FOUND

http POST "/prompts/$PID/compare" '{"from_version":2,"to_version":2}'
expect_error "comparar a mesma versão" 422 INVALID_VERSION_COMPARISON

http POST "/prompts/$PID/recover"
expect_error "restaurar prompt não deletado" 409 PROMPT_NOT_DELETED

http POST /prompts '{"name":"   ","content":"x"}'
expect_error "nome em branco" 409 DOMAIN_RULE_VIOLATION

http GET /prompts/nao-e-uuid
expect_error "UUID inválido (barrado na api, não chega ao core)" 422 INVALID_REQUEST

http POST /prompts '{"name":"sem conteudo"}'
expect_error "corpo incompleto (barrado na api)" 422 INVALID_REQUEST

# limpeza: os prompts do teste terminam deletados (soft delete)
http DELETE "/prompts/$PID"
http DELETE "/prompts/$NATS_PID"

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
