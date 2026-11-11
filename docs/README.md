# Prompt Vault: study material

Teaching material for the whole project (core, api and front), written in English. It follows the real code: the guide copies its code listings straight from the source files.

| File | What it is |
|---|---|
| [`prompt-vault-study-guide.pdf`](prompt-vault-study-guide.pdf) | The study guide (about 85 pages): Python essentials, hexagonal architecture, the core layer by layer, the HTTP api, the React front end, one request end to end, how it is verified and hands-on exercises. Includes a glossary, a file map and the answers to the checkpoints. |
| [`prompt-vault-map.html`](prompt-vault-map.html) | An interactive map: open it in any browser (no server needed). Nine views: the whole system, layers, the dependency rule (with a tester), a message inside the core, the journey from the browser, a simulator of the domain rules, subjects and routes, error mapping and the wiring of `main.py`. |
| [`guide/`](guide) | The source of the PDF: Markdown chapters, the stylesheet, the SVG figures and the build script. |

## Rebuilding the guide

The PDF is generated from `guide/chapters/*.md` with Chrome or Chromium (set `CHROME_PATH` if it is not found automatically):

```bash
uv run --with markdown --with pygments --with playwright --with pypdf python docs/guide/build.py
```

- Code listings use `@code path/to/file.py:first-last`. The build fails if the file or the line range no longer exists, so a refactor cannot silently leave the guide stale.
- Figures are drawn by `guide/figures.py`; the chapters reference them with `@figure name "Caption"`.
- The table of contents and its page numbers are computed in two passes.

## Keeping the map up to date

`prompt-vault-map.html` is a single hand-written file (CSS, markup and JavaScript). Names of classes, subjects, routes and error codes are the project's own; when one of them changes, search the file for the old name.
