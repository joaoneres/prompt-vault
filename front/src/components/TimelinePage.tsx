import { RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../api/client";
import { listVersions } from "../api/prompts";
import type { PromptVersionResponse } from "../types";
import VersionTimeline from "./VersionTimeline";

interface Props {
  promptId: string;
  onNotify: (kind: "success" | "error", message: string) => void;
}

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; versions: PromptVersionResponse[] };

export default function TimelinePage({ promptId, onNotify }: Props) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [retry, setRetry] = useState(0);
  const notifyRef = useRef(onNotify);
  notifyRef.current = onNotify;

  useEffect(() => {
    let current = true;
    setState({ status: "loading" });
    listVersions(promptId)
      .then((versions) => {
        if (!current) return;
        // Newest first, like a commit history.
        setState({ status: "ready", versions: [...versions].sort((a, b) => b.version_number - a.version_number) });
      })
      .catch((error) => {
        if (!current) return;
        setState({ status: "error", message: errorMessage(error) });
        notifyRef.current("error", errorMessage(error));
      });
    return () => {
      current = false;
    };
  }, [promptId, retry]);

  return (
    <section aria-live="polite" aria-busy={state.status === "loading"}>
      {state.status === "loading" && (
        <ol className="space-y-6" aria-label="Carregando versões">
          {[0, 1, 2].map((key) => (
            <li key={key} className="flex gap-4">
              <span className="mt-4 size-6 shrink-0 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
              <div className="h-24 flex-1 animate-pulse rounded-2xl border border-slate-200 bg-white/70 dark:border-slate-800 dark:bg-slate-900/60" />
            </li>
          ))}
        </ol>
      )}

      {state.status === "error" && (
        <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900 dark:bg-rose-950/60">
          <p className="font-medium text-rose-900 dark:text-rose-100">Não foi possível carregar a linha do tempo</p>
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
        (state.versions.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
            Este prompt ainda não tem versões.
          </p>
        ) : (
          <>
            <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
              {state.versions.length} {state.versions.length === 1 ? "versão" : "versões"} · da mais recente para a mais antiga
            </p>
            <VersionTimeline promptId={promptId} versions={state.versions} onNotify={onNotify} />
          </>
        ))}
    </section>
  );
}
