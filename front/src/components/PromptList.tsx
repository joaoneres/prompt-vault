import { RefreshCw, Search, SearchX } from "lucide-react";
import { useMemo, useState } from "react";
import type { PromptItem } from "../types";
import PromptCard from "./PromptCard";

interface Props {
  prompts: PromptItem[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onTimeline: (prompt: PromptItem) => void;
  onCompare: (prompt: PromptItem) => void;
  onDetails: (prompt: PromptItem) => void;
}

export default function PromptList({ prompts, loading, error, onRetry, onTimeline, onCompare, onDetails }: Props) {
  const [query, setQuery] = useState("");

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    return term ? prompts.filter((prompt) => prompt.name.toLowerCase().includes(term)) : prompts;
  }, [prompts, query]);

  return (
    <section className="mx-auto w-full max-w-2xl">
      <div className="relative mb-6">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 z-10 size-5 -translate-y-1/2 text-slate-400" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar prompt pelo nome..."
          aria-label="Buscar prompt pelo nome"
          className="w-full rounded-xl border border-slate-300 bg-white/90 py-3 pl-11 pr-4 text-sm shadow-sm outline-none backdrop-blur transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 dark:border-slate-700 dark:bg-slate-900/80"
        />
      </div>

      {loading ? (
        <ul className="space-y-4" aria-label="Carregando prompts" aria-busy="true">
          {[0, 1, 2].map((key) => (
            <li key={key} className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white/70 dark:border-slate-800 dark:bg-slate-900/60" />
          ))}
        </ul>
      ) : error ? (
        <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900 dark:bg-rose-950/60">
          <p className="font-medium text-rose-900 dark:text-rose-100">Não foi possível carregar os prompts</p>
          <p className="mt-1 text-sm text-rose-700 dark:text-rose-300">{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-500"
          >
            <RefreshCw className="size-4" aria-hidden />
            Tentar novamente
          </button>
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <SearchX className="mx-auto size-8 text-slate-400" aria-hidden />
          <p className="mt-3 font-medium">{prompts.length === 0 ? "Nenhum prompt ainda" : "Nenhum prompt encontrado"}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {prompts.length === 0 ? "Use o botão + para criar o primeiro." : "Tente outro termo de busca."}
          </p>
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-4">
          {visible.map((prompt) => (
            <li key={prompt.id}>
              <PromptCard prompt={prompt} onTimeline={onTimeline} onCompare={onCompare} onDetails={onDetails} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
