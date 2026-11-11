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

## Scope

Implemented: prompt list with search, create modal, details modal (copy, edit = new version), toasts, light/dark theme.
The timeline and version comparison screens are not part of this iteration; their icons only show a notice.
