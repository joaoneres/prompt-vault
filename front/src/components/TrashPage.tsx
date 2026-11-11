import { Loader2, RefreshCw, RotateCcw, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../api/client";
import { listDeletedPrompts, recoverPrompt } from "../api/prompts";
import type { PromptResponse } from "../types";

interface Props {
  /** Called after a prompt was recovered so the main list can bring it back. */
  onRecovered: (promptId: string) => Promise<void>;
  onNotify: (kind: "success" | "error", message: string) => void;
}

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; prompts: PromptResponse[] };

export default function TrashPage({ onRecovered, onNotify }: Props) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [retry, setRetry] = useState(0);
  const [recovering, setRecovering] = useState<string | null>(null);
  const notifyRef = useRef(onNotify);
  notifyRef.current = onNotify;

  useEffect(() => {
    let current = true;
    setState({ status: "loading" });
    listDeletedPrompts()
      .then((prompts) => {
        if (!current) return;
        setState({ status: "ready", prompts: [...prompts].sort((a, b) => b.updated_at.localeCompare(a.updated_at)) });
      })
      .catch((error) => {
        if (!current) return;
        setState({ status: "error", message: errorMessage(error) });
        notifyRef.current("error", errorMessage(error));
      });
    return () => {
      current = false;
    };
  }, [retry]);

  const recover = async (prompt: PromptResponse) => {
    setRecovering(prompt.id);
    try {
      await recoverPrompt(prompt.id);
      setState((s) => (s.status === "ready" ? { status: "ready", prompts: s.prompts.filter((p) => p.id !== prompt.id) } : s));
      await onRecovered(prompt.id).catch(() => undefined);
      onNotify("success", `Prompt "${prompt.name}" recuperado.`);
    } catch (error) {
      onNotify("error", errorMessage(error));
    } finally {
      setRecovering(null);
    }
  };

  return (
    <section aria-live="polite" aria-busy={state.status === "loading"}>
      {state.status === "loading" && (
        <ul className="space-y-4" aria-label="Carregando lixeira">
          {[0, 1].map((key) => (
            <li key={key} className="h-20 animate-pulse rounded-2xl border border-slate-200 bg-white/70 dark:border-slate-800 dark:bg-slate-900/60" />
          ))}
        </ul>
      )}

      {state.status === "error" && (
        <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900 dark:bg-rose-950/60">
          <p className="font-medium text-rose-900 dark:text-rose-100">Não foi possível carregar a lixeira</p>
          <p className="mt-1 text-sm text-rose-700 dark:text-rose-300">{state.message}</p>
          <button
            type="button"
            onClick={() => setRetry((value) => value + 1)}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-500"
          >
            <RefreshCw className="size-4" aria-hidden />
            Tentar novamente
          </button>
        </div>
      )}

      {state.status === "ready" &&
        (state.prompts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center dark:border-slate-700 dark:bg-slate-900/50">
            <Trash2 className="mx-auto size-8 text-slate-400" aria-hidden />
            <p className="mt-3 font-medium">A lixeira está vazia</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Prompts excluídos aparecem aqui e podem ser recuperados.</p>
          </div>
        ) : (
          <ul className="space-y-4">
            {state.prompts.map((prompt) => (
              <li
                key={prompt.id}
                className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm backdrop-blur sm:p-5 dark:border-slate-800 dark:bg-slate-900/80"
              >
                <div className="min-w-0">
                  <h3 className="truncate text-base font-semibold" title={prompt.name}>
                    {prompt.name}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Excluído em{" "}
                    <time dateTime={prompt.updated_at}>
                      {new Date(prompt.updated_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
                    </time>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void recover(prompt)}
                  disabled={recovering !== null}
                  aria-label={`Recuperar ${prompt.name}`}
                  className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {recovering === prompt.id ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <RotateCcw className="size-4" aria-hidden />}
                  Recuperar
                </button>
              </li>
            ))}
          </ul>
        ))}
    </section>
  );
}
