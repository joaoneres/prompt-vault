import { Check, ChevronDown, Copy, GitCompareArrows } from "lucide-react";
import { useState } from "react";
import type { PromptVersionResponse } from "../types";

interface Props {
  promptId: string;
  /** Newest first. */
  versions: PromptVersionResponse[];
  onNotify: (kind: "success" | "error", message: string) => void;
}

const SUMMARY_MAX = 120;
const SUMMARY_LINES = 2;

/** The first non-empty lines (shortened) plus how many more lines the version has. */
function summarize(content: string): { lines: string[]; more: number } {
  const filled = content.split("\n").map((line) => line.trim()).filter((line) => line !== "");
  const shown = filled.slice(0, SUMMARY_LINES).map((line) => (line.length > SUMMARY_MAX ? `${line.slice(0, SUMMARY_MAX - 1).trimEnd()}…` : line));
  return { lines: shown, more: filled.length - shown.length };
}

const relative = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31_536_000],
  ["month", 2_592_000],
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

function timeAgo(iso: string): string {
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit);
  }
  return "agora há pouco";
}

const quickLink =
  "inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 focus-visible:outline-2 focus-visible:outline-indigo-500 dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigo-700 dark:hover:bg-slate-800 dark:hover:text-indigo-300";

export default function VersionTimeline({ promptId, versions, onNotify }: Props) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const active = versions.find((version) => version.is_active);
  const numbers = versions.map((version) => version.version_number);
  const compareHref = (a: number, b: number) =>
    `#/compare/${promptId}?from=${Math.min(a, b)}&to=${Math.max(a, b)}`;

  const copy = async (version: PromptVersionResponse) => {
    try {
      await navigator.clipboard.writeText(version.content);
      setCopiedId(version.id);
      setTimeout(() => setCopiedId((id) => (id === version.id ? null : id)), 1800);
      onNotify("success", `Conteúdo da v${version.version_number} copiado.`);
    } catch {
      onNotify("error", "Não foi possível copiar o conteúdo.");
    }
  };

  return (
    <ol className="relative">
      {versions.map((version, index) => {
        const isOpen = openId === version.id;
        const isLast = index === versions.length - 1;
        const { lines: summary, more } = summarize(version.content);
        const previous = version.version_number - 1;
        const canComparePrevious = previous >= 1 && numbers.includes(previous);
        const canCompareActive = !!active && !version.is_active;
        const panelId = `version-${version.id}`;

        return (
          <li key={version.id} className="relative flex gap-4 pb-6 last:pb-0">
            {/* Connector: runs from this node down to the next one. */}
            {!isLast && (
              <span aria-hidden className="absolute left-[11px] top-6 h-[calc(100%-1.5rem)] w-0.5 bg-slate-200 dark:bg-slate-700" />
            )}
            <span
              aria-hidden
              className={`relative z-10 mt-4 size-6 shrink-0 rounded-full border-2 ${
                version.is_active
                  ? "border-indigo-600 bg-indigo-600 ring-4 ring-indigo-200 dark:border-indigo-400 dark:bg-indigo-400 dark:ring-indigo-900"
                  : "border-slate-300 bg-white dark:border-slate-600 dark:bg-slate-900"
              }`}
            />

            <div
              className={`min-w-0 flex-1 rounded-2xl border bg-white/85 shadow-sm backdrop-blur dark:bg-slate-900/80 ${
                version.is_active
                  ? "border-indigo-400 ring-1 ring-indigo-200 dark:border-indigo-600 dark:ring-indigo-900"
                  : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : version.id)}
                aria-expanded={isOpen}
                aria-controls={panelId}
                className="flex w-full items-start gap-3 rounded-2xl p-4 text-left focus-visible:outline-2 focus-visible:outline-indigo-500"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-sm font-semibold dark:bg-slate-800">
                      v{version.version_number}
                    </span>
                    {version.is_active && (
                      <span className="rounded-full bg-indigo-600 px-2.5 py-0.5 text-xs font-medium text-white dark:bg-indigo-500">
                        ativa
                      </span>
                    )}
                    <time dateTime={version.created_at} className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(version.created_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
                      <span className="text-slate-400 dark:text-slate-500"> · {timeAgo(version.created_at)}</span>
                    </time>
                  </div>
                  {summary.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-500">(conteúdo vazio)</p>
                  ) : (
                    summary.map((line, i) => (
                      <p key={i} className={`truncate text-sm text-slate-700 dark:text-slate-300 ${i === 0 ? "mt-2" : "mt-0.5"}`}>
                        {line}
                      </p>
                    ))
                  )}
                  {more > 0 && (
                    <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                      +{more} {more === 1 ? "linha" : "linhas"}
                    </p>
                  )}
                </div>
                <ChevronDown
                  aria-hidden
                  className={`mt-1 size-5 shrink-0 text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
                />
              </button>

              {isOpen && (
                <div id={panelId} className="border-t border-slate-200 px-4 pb-4 pt-3 dark:border-slate-800">
                  <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-[13px] leading-relaxed dark:border-slate-800 dark:bg-slate-950">
                    {version.content}
                  </pre>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button type="button" onClick={() => void copy(version)} className={quickLink}>
                      {copiedId === version.id ? <Check className="size-3.5" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
                      {copiedId === version.id ? "Copiado" : "Copiar"}
                    </button>
                  </div>
                </div>
              )}

              {(canComparePrevious || canCompareActive) && (
                <div className="flex flex-wrap gap-2 border-t border-slate-100 px-4 py-2.5 dark:border-slate-800/70">
                  {canComparePrevious && (
                    <a href={compareHref(previous, version.version_number)} className={quickLink}>
                      <GitCompareArrows className="size-3.5" aria-hidden />
                      Comparar com anterior (v{previous})
                    </a>
                  )}
                  {canCompareActive && active && (
                    <a href={compareHref(version.version_number, active.version_number)} className={quickLink}>
                      <GitCompareArrows className="size-3.5" aria-hidden />
                      Comparar com a ativa (v{active.version_number})
                    </a>
                  )}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
