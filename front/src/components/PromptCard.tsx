import { GitCompareArrows, History, Maximize2 } from "lucide-react";
import { activeVersion, type PromptItem } from "../types";

interface Props {
  prompt: PromptItem;
  onTimeline: (prompt: PromptItem) => void;
  onCompare: (prompt: PromptItem) => void;
  onDetails: (prompt: PromptItem) => void;
}

const iconButton =
  "inline-flex size-9 items-center justify-center rounded-lg text-slate-500 transition hover:bg-indigo-50 hover:text-indigo-600 focus-visible:outline-2 focus-visible:outline-indigo-500 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-indigo-300";

export default function PromptCard({ prompt, onTimeline, onCompare, onDetails }: Props) {
  const active = activeVersion(prompt);

  return (
    <article className="group rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm backdrop-blur transition hover:border-indigo-300 hover:shadow-md sm:p-5 dark:border-slate-800 dark:bg-slate-900/80 dark:hover:border-indigo-700">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold" title={prompt.name}>
            {prompt.name}
          </h3>
          <span
            className={`mt-1.5 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              active
                ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
            }`}
          >
            {active ? `v${active.version_number} ativa` : prompt.versions ? "sem versão ativa" : "versão indisponível"}
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-0.5">
          <a
            href={`/prompts/${prompt.id}/timeline`}
            onClick={(event) => {
              event.preventDefault();
              onTimeline(prompt);
            }}
            aria-label={`Linha do tempo de ${prompt.name}`}
            title="Linha do tempo"
            className={iconButton}
          >
            <History className="size-5" />
          </a>
          <a
            href={`/prompts/${prompt.id}/compare`}
            onClick={(event) => {
              event.preventDefault();
              onCompare(prompt);
            }}
            aria-label={`Comparar versões de ${prompt.name}`}
            title="Comparar versões"
            className={iconButton}
          >
            <GitCompareArrows className="size-5" />
          </a>
          <button
            type="button"
            onClick={() => onDetails(prompt)}
            aria-label={`Detalhes de ${prompt.name}`}
            title="Detalhes"
            className={iconButton}
          >
            <Maximize2 className="size-5" />
          </button>
        </div>
      </div>

      {active && (
        <p className="mt-3 line-clamp-3 whitespace-pre-line break-words text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {active.content}
        </p>
      )}
    </article>
  );
}
