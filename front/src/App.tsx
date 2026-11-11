import { ArrowLeft, GitCompareArrows } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "./api/client";
import { getPrompt, listActivePrompts } from "./api/prompts";
import ComparePage from "./components/ComparePage";
import CreatePromptModal from "./components/CreatePromptModal";
import FloatingAddButton from "./components/FloatingAddButton";
import GeometricBackground from "./components/GeometricBackground";
import PromptDetailModal from "./components/PromptDetailModal";
import PromptList from "./components/PromptList";
import ThemeToggle from "./components/ThemeToggle";
import Toaster, { useToasts } from "./components/Toaster";
import type { PromptItem, PromptResponse } from "./types";

type Route = { name: "list" } | { name: "compare"; promptId?: string };

/** Tiny hash router: "#/compare" and "#/compare/{promptId}". Everything else is the list. */
function parseRoute(): Route {
  const match = location.hash.match(/^#\/compare(?:\/([0-9a-fA-F-]{36}))?\/?$/);
  return match ? { name: "compare", promptId: match[1] } : { name: "list" };
}

function useRoute(): Route {
  const [route, setRoute] = useState(parseRoute);
  useEffect(() => {
    const onChange = () => setRoute(parseRoute());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

/** Loads the active prompts and, for each one, its versions (the list endpoint has no content). */
async function loadPrompts(): Promise<{ items: PromptItem[]; failed: number }> {
  const summaries = await listActivePrompts();
  const details = await Promise.allSettled(summaries.map((summary) => getPrompt(summary.id)));
  let failed = 0;
  const items = summaries.map((summary, index): PromptItem => {
    const detail = details[index];
    if (detail.status === "fulfilled") return detail.value;
    failed += 1;
    return summary;
  });
  items.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  return { items, failed };
}

const navLink =
  "inline-flex h-10 items-center justify-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 text-sm font-medium text-slate-700 shadow-sm backdrop-blur transition hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 sm:px-4 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-200 dark:hover:bg-slate-800";

export default function App() {
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const { toasts, dismiss, notify } = useToasts();
  const route = useRoute();
  const comparing = route.name === "compare";

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { items, failed } = await loadPrompts();
      setPrompts(items);
      if (failed > 0) notify("error", `${failed} prompt(s) carregaram sem as versões.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const reloadOne = useCallback(async (promptId: string) => {
    const detail = await getPrompt(promptId);
    setPrompts((all) => [detail, ...all.filter((prompt) => prompt.id !== promptId)]);
  }, []);

  const onCreated = async (created: PromptResponse) => {
    setCreating(false);
    try {
      await reloadOne(created.id);
      notify("success", `Prompt "${created.name}" criado.`);
    } catch {
      await refresh();
      notify("success", `Prompt "${created.name}" criado.`);
    }
  };

  const detail = prompts.find((prompt) => prompt.id === detailId) ?? null;

  return (
    <div className="relative min-h-screen">
      <GeometricBackground />

      <header className={`mx-auto flex w-full items-center justify-between gap-3 px-4 pb-6 pt-8 sm:pt-12 ${comparing ? "max-w-5xl" : "max-w-2xl"}`}>
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-bold tracking-tight sm:text-3xl">{comparing ? "Comparar versões" : "Prompt Vault"}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {comparing ? "Veja o que mudou entre duas versões de um prompt." : "Seus prompts e versões em um só lugar."}
          </p>
        </div>
        <nav aria-label="Principal" className="flex shrink-0 items-center gap-2">
          {comparing ? (
            <a href="#/" className={navLink}>
              <ArrowLeft className="size-4" aria-hidden />
              <span className="hidden sm:inline">Prompts</span>
              <span className="sr-only sm:hidden">Voltar para os prompts</span>
            </a>
          ) : (
            <a href="#/compare" className={navLink} title="Comparar versões">
              <GitCompareArrows className="size-4" aria-hidden />
              <span className="hidden sm:inline">Comparar</span>
              <span className="sr-only sm:hidden">Comparar versões</span>
            </a>
          )}
          <ThemeToggle />
        </nav>
      </header>

      {comparing ? (
        <main className="mx-auto w-full max-w-5xl px-4 pb-16">
          <ComparePage
            promptId={route.promptId}
            onSelectPrompt={(id) => {
              location.hash = `#/compare/${id}`;
            }}
            onError={(message) => notify("error", message)}
          />
        </main>
      ) : (
        <>
          <main className="px-4 pb-32">
            <PromptList
              prompts={prompts}
              loading={loading}
              error={error}
              onRetry={() => void refresh()}
              onTimeline={() => notify("info", "A linha do tempo estará disponível em breve.")}
              onDetails={(prompt) => setDetailId(prompt.id)}
            />
          </main>
          <FloatingAddButton onClick={() => setCreating(true)} />
        </>
      )}

      {creating && (
        <CreatePromptModal
          onClose={() => setCreating(false)}
          onCreated={(created) => void onCreated(created)}
          onError={(message) => notify("error", message)}
        />
      )}

      {detail && (
        <PromptDetailModal
          key={detail.id}
          prompt={detail}
          onClose={() => setDetailId(null)}
          onSaved={reloadOne}
          onNotify={notify}
        />
      )}

      <Toaster toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
