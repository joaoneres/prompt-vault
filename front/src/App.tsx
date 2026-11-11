import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "./api/client";
import { getPrompt, listActivePrompts } from "./api/prompts";
import CreatePromptModal from "./components/CreatePromptModal";
import FloatingAddButton from "./components/FloatingAddButton";
import GeometricBackground from "./components/GeometricBackground";
import PromptDetailModal from "./components/PromptDetailModal";
import PromptList from "./components/PromptList";
import ThemeToggle from "./components/ThemeToggle";
import Toaster, { useToasts } from "./components/Toaster";
import type { PromptItem, PromptResponse } from "./types";

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

export default function App() {
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const { toasts, dismiss, notify } = useToasts();

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

      <header className="mx-auto flex w-full max-w-2xl items-center justify-between px-4 pb-6 pt-8 sm:pt-12">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Prompt Vault</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Seus prompts e versões em um só lugar.</p>
        </div>
        <ThemeToggle />
      </header>

      <main className="px-4 pb-32">
        <PromptList
          prompts={prompts}
          loading={loading}
          error={error}
          onRetry={() => void refresh()}
          onTimeline={() => notify("info", "A linha do tempo estará disponível em breve.")}
          onCompare={() => notify("info", "A comparação de versões estará disponível em breve.")}
          onDetails={(prompt) => setDetailId(prompt.id)}
        />
      </main>

      <FloatingAddButton onClick={() => setCreating(true)} />

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
