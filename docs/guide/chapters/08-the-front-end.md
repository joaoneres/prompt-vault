::: chapter 8 "The front end" "How the browser application turns the api into screens"

::: question
How does a web page ask the api for data, keep it in sync with what the user does, and show errors without breaking?
:::

The `front/` project is a **single-page application** (SPA): the browser downloads one HTML page and one JavaScript bundle, and from then on JavaScript draws every screen and talks to the api in the background. It is about 1,900 lines of TypeScript. This chapter assumes you have never used React; the next section gives the five ideas you need.

## 8.1 React in five minutes

| Idea | What it means | Example in the project |
|---|---|---|
| **Component** | A function that returns a piece of screen (JSX, which looks like HTML inside TypeScript). | `PromptCard` draws one card. |
| **Props** | The inputs of a component, like function arguments. | `<PromptCard prompt={p} onDetails={...} />` |
| **State** | Data a component remembers between draws. Changing it redraws the component. | `const [query, setQuery] = useState("")` |
| **Effect** | Code that runs after a draw, usually to fetch data or subscribe to something. Its cleanup function runs before the next effect. | `useEffect(() => { loadVersions() }, [promptId])` |
| **Lifting state up** | When two components need the same data, the parent owns it and passes it down. | `App` owns the list of prompts. |

TypeScript adds types to JavaScript, the same idea you met in Chapter 2: `prompt: PromptItem` documents what a component receives, and the compiler refuses a wrong call. The project is built with **Vite** (a fast development server and bundler), styled with **Tailwind CSS** (utility classes written right in the markup) and calls the api with **Axios** (an HTTP client library).

## 8.2 The map of the front end

@figure front_arch "The front end: App owns the state and the route; screens are components; one thin layer talks HTTP."

Read it top-down. `main.tsx` starts React and renders `App`. `App` keeps three things: the list of prompts, the current **route** (derived from the URL), and the **toasts** (the small notifications). It chooses which screen to show. Every screen reaches the api only through `api/prompts.ts`, and that file goes through one shared Axios instance in `api/client.ts`.

## 8.3 The service layer: Axios and the contract

Every call to the api lives in one file, one function per endpoint:

```ts title="front/src/api/prompts.ts · excerpt"
/** GET /prompts/{prompt_id} */
export const getPrompt = async (promptId: string): Promise<PromptDetailResponse> =>
  (await http.get<PromptDetailResponse>(`/prompts/${promptId}`)).data;

/** POST /prompts/{prompt_id}/activate: makes that version the one in use (rollback or promote). */
export const activateVersion = async (promptId: string, versionNumber: number): Promise<PromptResponse> =>
  (await http.post<PromptResponse>(`/prompts/${promptId}/activate`, { version_number: versionNumber })).data;
```

Where do the types `PromptDetailResponse` and `PromptResponse` come from? **From the api itself.** The api publishes an OpenAPI document (Chapter 7); the front end keeps a snapshot of it (`openapi.json`) and runs the tool `openapi-typescript` to generate `src/api/schema.d.ts`. If the api changes a field name, regenerating the types makes the front end *fail to compile* exactly where it used the old name. The contract is enforced by the compiler.

The shared Axios instance also normalizes errors, so that every screen can treat a failure the same way:

@code front/src/api/client.ts:1-41 "front/src/api/client.ts"

The interceptor reads the standard error JSON of the api (`{error: {code, message}}`) and throws an `ApiError` carrying the message. If there is no response at all (the api is down), it throws a "could not connect" error. Screens never parse HTTP errors themselves.

::: concept CORS and the Vite proxy
Browsers refuse, by default, to let a page served from `localhost:5173` call an API on `localhost:8000`: that is the *same-origin policy*, relaxed only if the API opts in with CORS headers. The api has no CORS configuration. In development, Vite solves this with a **proxy**: the front end calls `/api/...` on its own address, and Vite forwards the request to the api, removing the `/api` prefix. From the browser's point of view there is only one server.
:::

## 8.4 State and routing in App

There is no router library. The current screen is encoded in the URL **hash** (the part after `#`), and a few lines parse it:

@code front/src/App.tsx:25-52 "front/src/App.tsx · a tiny hash router"

`useRoute` listens for the browser's `hashchange` event and redraws when the URL changes. Because the screen is in the URL, the back button works, and a link such as `#/timeline/<id>` can be bookmarked or shared. These are the screens:

| Route | Screen |
|---|---|
| `#/` | The list of prompts: search, create, details. |
| `#/compare`, `#/compare/{id}`, `#/compare/{id}?from=1&to=3` | Compare two versions. The prompt and versions can be pre-selected from a link. |
| `#/timeline/{id}` | The version history of one prompt. |
| `#/trash` | Deleted prompts, with recovery. |

## 8.5 Loading data: why one request per card

The list endpoint, `GET /prompts/active`, returns a *summary* of each prompt: name, status, dates and the id of the active version. It does **not** include the content or the version number. But a card must show "v3 active" and a preview of the active content. So after the list arrives, the front end asks for the detail of every prompt in parallel:

```ts title="front/src/App.tsx · loadPrompts (shortened)"
const summaries = await listActivePrompts();
const details = await Promise.allSettled(summaries.map((s) => getPrompt(s.id)));
// fulfilled -> use the detail; rejected -> keep the summary and warn the user
```

`Promise.allSettled` is the important choice: if one detail fails, the others still arrive, and the card of the failed one simply shows "version unavailable". It is a trade-off. For a handful of prompts it is fine; for hundreds it would be many requests, and the right fix would be on the api side (a list endpoint that includes the active version). Honest limitations like this are worth writing down.

After a change, the front end does not refetch everything; it reloads just the prompt that changed:

@code front/src/App.tsx:104-107 "front/src/App.tsx · reloadOne"

`reloadOne` fetches one prompt and puts it at the top of the list, replacing the old copy. It is passed down to the screens as a callback, which is how a timeline page can tell the main list "this prompt changed".

## 8.6 The screens

### The list and the cards

`PromptList` owns the search box (a state variable) and filters the prompts by name on the client, in memory. Each `PromptCard` shows the name, a badge for the active version, a preview of the active content (`line-clamp` cuts it to three lines) and three icons: timeline, compare and details.

### Create, edit, activate

Creating a prompt opens a modal with a name and a content field, sends `POST /prompts` and inserts the result into the list. The details modal shows the active content, with **Copy** and **Edit** buttons. Editing offers two ways to save, matching two different endpoints:

@code front/src/components/PromptDetailModal.tsx:52-64 "front/src/components/PromptDetailModal.tsx · two ways to save"

"Save and activate" calls `PUT .../content` (the new version becomes the active one). "Save without activating" calls `POST .../versions` (the version is kept in the history and the current one stays in force). The difference is the one Chapter 4 called "versions" versus "the pointer".

### Comparing versions

The compare screen has three parts: a prompt selector, a pair of version selectors, and the diff viewer. Whenever the prompt or either version changes, it asks the api for the diff. Two subtleties deserve attention.

First, the **stale response guard**. If the user changes the selection quickly, two requests are in flight, and the *older* one might answer *last*. Without protection, the screen would show a diff that no longer matches the selectors. Each effect therefore marks itself as current, and its cleanup function marks it as stale:

@code front/src/components/ComparePage.tsx:90-100 "front/src/components/ComparePage.tsx · ignoring stale answers"

Second, the **split view**. The api returns a flat list of lines, each `added`, `removed` or `unchanged`. A side-by-side view needs rows with a left and a right cell. A tiny algorithm pairs each run of removed lines with the added lines that follow it:

@code front/src/components/DiffViewer.tsx:39-61 "front/src/components/DiffViewer.tsx · pairing lines for the split view"

Notice what the front end does *not* do: it does not compute the diff. The comparison algorithm lives in the core (Chapter 4); the front end only arranges the result on screen. The unified view simply lists the lines in order. Additions are green, removals red, and long lines scroll horizontally instead of wrapping or overlapping.

### The timeline

The timeline lists the versions newest first, like a commit history. Each node shows the version number, the date, a two-line summary and a highlighted badge for the active one. The summary is a small pure function:

@code front/src/components/VersionTimeline.tsx:18-23 "front/src/components/VersionTimeline.tsx · summarize"

Clicking a node expands its full content. Each non-active node also offers **Activate this version**, which is how the user performs a rollback:

@code front/src/components/TimelinePage.tsx:47-57 "front/src/components/TimelinePage.tsx · activating a version"

After activating, the page reloads its versions *in place* (no loading skeleton, so the highlight simply moves), then tells the main list to refresh that prompt, then shows a toast. The two quick links on each node, *compare with previous* and *compare with active*, are plain links to `#/compare/{id}?from=..&to=..`.

### The trash

Deleting a prompt (with a confirmation dialog) calls `DELETE /prompts/{id}`, a soft delete in the core. The trash screen lists `GET /prompts/deleted` and offers **Recover**, which calls `POST /prompts/{id}/recover`. The date shown is the prompt's `updated_at`, which the core sets at the moment of deletion; the api exposes no separate "deleted at" field, so the front end does not invent one.

## 8.7 Patterns that make it feel solid

- **Every asynchronous screen has four states:** loading (a skeleton that mimics the final layout), empty (a friendly message), error (the message from the api, plus a "Try again" button) and ready.
- **Toasts** give feedback for actions: green for success, red for errors (they stay longer).
- **Modals** trap the Escape key and block closing while a request is in flight, so a double click cannot send two requests. A confirmation modal opened *on top of* another modal closes alone on Escape.
- **Dark and light themes** are a CSS class on the page root. The choice is saved in `localStorage`, the only thing the front end persists. A tiny script in `index.html` applies it before the first paint, avoiding a flash of the wrong theme.
- **Accessibility:** buttons that are only icons have text labels for screen readers (`aria-label`), dialogs declare `role="dialog"` and `aria-modal`, and loading regions announce themselves with `aria-busy`.

::: lesson The test that failed for the wrong reason
While testing the timeline in a real browser, four checks failed. The page was right; the test was wrong: it counted the loading skeleton's placeholders as if they were the real nodes, and it searched for the word "active", which also appears in the "Compare with active" links. Browser tests are code, and flaky selectors are bugs. The fix was to wait for something only the real content has (a `<time>` element) and to match the exact badge text. A failing test deserves the same suspicion as a failing feature.
:::

::: warning What the front end does not have yet
There are no automated front-end tests: it is checked by the TypeScript compiler (`npm run build`) and by exercising the real browser against the real api, which was done repeatedly while building it. Pagination of long lists, an "undo" after deleting and deleting directly from a card are also left for later.
:::

::: checkpoint
1. Why does the front end call `/api/...` instead of `http://localhost:8000/...` directly?
2. What problem does the "stale response guard" in `ComparePage` solve?
3. Why does the front end not compute the diff itself?
:::

::: summary
- The front end is a single-page app: React components, TypeScript types, Tailwind styling and Axios for HTTP.
- One service layer wraps the endpoints; its types are generated from the api's OpenAPI document, so the compiler enforces the contract.
- The screen is encoded in the URL hash; `App` owns the list, the route and the toasts.
- The core produces the diff; the front end only arranges it (split or unified).
- Every async screen handles loading, empty, error and ready; stale answers are ignored.
:::
