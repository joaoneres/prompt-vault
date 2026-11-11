# Prompt Vault: front

Dashboard to browse, search, create and edit prompts. React + Vite + TypeScript + Tailwind CSS + Axios.
All data comes from the API gateway (`../api`); nothing is stored by the front except the theme preference.

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

Needs NATS, the core and the API running (see the root README). In dev, Vite forwards `/api/*` to
`http://localhost:8000` (the API has no CORS). Copy `.env.example` to `.env` to change it:

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/api` | Base URL of the Axios client |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Where the dev proxy forwards `/api` |

## API contract

`openapi.json` is a snapshot of the API's Swagger; `src/api/schema.d.ts` is generated from it.
After the API contract changes:

```bash
(cd ../api && uv run python -c "import main, json; print(json.dumps(main.app.openapi(), indent=2, ensure_ascii=False))") > openapi.json
npm run gen:api
```

The Axios service layer is in `src/api/` (`client.ts` normalizes the gateway's `{error: {code, message}}`,
`prompts.ts` wraps the endpoints).

## Screens

| Route | Screen |
|---|---|
| `#/` | Prompt list: search, create, details (copy, edit, delete) |
| `#/compare` | Version comparison: pick a prompt, then base (before) and compared (after) |
| `#/compare/{promptId}` | Same, with the prompt already selected (the compare icon on each card) |
| `#/compare/{promptId}?from=1&to=3` | Same, with both versions already selected (quick actions of the timeline) |
| `#/timeline/{promptId}` | Version timeline (the timeline icon on each card); activate a version |
| `#/trash` | Trash: deleted prompts, recover |

The comparison calls `POST /prompts/{id}/compare`. The core returns the line diff, so the front only
renders it (`DiffViewer`): split or unified view, additions in green, removals in red, no diff library.
Routing is a tiny hash router in `App.tsx` (no extra dependency).

The timeline calls `GET /prompts/{id}/versions` and lists the versions newest first, like a commit
history: version, date, a two-line summary, the active version highlighted. Clicking a version expands its
full content (with copy), and each one has quick links to compare it with the previous or the active version.

Version handling: editing offers "Salvar e ativar" (`PUT /prompts/{id}/content`, new version in use) and
"Salvar sem ativar" (`POST /prompts/{id}/versions`, kept in the history only). In the timeline, any version
that is not the active one has "Ativar esta versão" (`POST /prompts/{id}/activate`, with confirmation), which
also works as a rollback.

Deleting a prompt (from its details modal, with confirmation) is a soft delete: versions are kept and the
prompt goes to the trash (`DELETE /prompts/{id}`, `GET /prompts/deleted`). "Recuperar" brings it back
(`POST /prompts/{id}/recover`). The trash shows `updated_at`, which the core sets when deleting.

All 11 endpoints of the API are now used by the front.

## Scope

Not in this front yet: pagination/filtering of versions, undo toast after deleting, deleting from the card.
