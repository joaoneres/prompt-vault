import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../api/client";
import { compareVersions, getPrompt, listActivePrompts } from "../api/prompts";
import type { PromptDetailResponse, PromptResponse, VersionDiffResponse } from "../types";
import DiffViewer from "./DiffViewer";
import VersionSelector from "./VersionSelector";

interface Props {
  /** Prompt taken from the route (#/compare/{id}); the page never keeps its own copy of it. */
  promptId?: string;
  /** Versions to start with (#/compare/{id}?from=..&to=..), used when they exist and differ. */
  initialFrom?: number;
  initialTo?: number;
  onSelectPrompt: (promptId: string) => void;
  onError: (message: string) => void;
}

type DiffState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: VersionDiffResponse };

const card = "rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm backdrop-blur sm:p-5 dark:border-slate-800 dark:bg-slate-900/80";

export default function ComparePage({ promptId, initialFrom, initialTo, onSelectPrompt, onError }: Props) {
  const [prompts, setPrompts] = useState<PromptResponse[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [detail, setDetail] = useState<PromptDetailResponse | null>(null);
  const [before, setBefore] = useState<number | null>(null);
  const [after, setAfter] = useState<number | null>(null);
  const [diff, setDiff] = useState<DiffState>({ status: "idle" });
  const [retry, setRetry] = useState(0);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  // 1. Prompts for the selector.
  useEffect(() => {
    let current = true;
    listActivePrompts()
      .then((list) => current && setPrompts(list))
      .catch((error) => {
        if (!current) return;
        setListError(errorMessage(error));
        onErrorRef.current(errorMessage(error));
      });
    return () => {
      current = false;
    };
  }, [retry]);

  // 2. Versions of the selected prompt. Defaults to comparing the last two.
  useEffect(() => {
    setDiff({ status: "idle" });
    setDetail(null);
    setBefore(null);
    setAfter(null);
    if (!promptId) return;
    let current = true;
    getPrompt(promptId)
      .then((data) => {
        if (!current) return;
        const numbers = data.versions.map((version) => version.version_number).sort((a, b) => a - b);
        setDetail(data);
        const wanted =
          initialFrom !== undefined &&
          initialTo !== undefined &&
          initialFrom !== initialTo &&
          numbers.includes(initialFrom) &&
          numbers.includes(initialTo);
        if (wanted) {
          setBefore(initialFrom);
          setAfter(initialTo);
        } else if (numbers.length >= 2) {
          setBefore(numbers[numbers.length - 2]);
          setAfter(numbers[numbers.length - 1]);
        }
      })
      .catch((error) => {
        if (!current) return;
        setDiff({ status: "error", message: errorMessage(error) });
        onErrorRef.current(errorMessage(error));
      });
    return () => {
      current = false;
    };
  }, [promptId, initialFrom, initialTo, retry]);

  // 3. The diff itself, always from the API. A newer selection discards an older answer.
  useEffect(() => {
    if (!promptId || !detail || before === null || after === null || before === after) {
      return;
    }
    let current = true;
    setDiff({ status: "loading" });
    compareVersions(promptId, before, after)
      .then((data) => current && setDiff({ status: "ready", data }))
      .catch((error) => {
        if (!current) return;
        setDiff({ status: "error", message: errorMessage(error) });
        onErrorRef.current(errorMessage(error));
      });
    return () => {
      current = false;
    };
  }, [promptId, detail, before, after, retry]);

  const select = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => event.target.value && onSelectPrompt(event.target.value),
    [onSelectPrompt],
  );

  const versions = detail ? [...detail.versions].sort((a, b) => a.version_number - b.version_number) : [];
  const options = detail && !prompts.some((prompt) => prompt.id === detail.id) ? [...prompts, detail] : prompts;

  return (
    <div className="space-y-5">
      <section className={card} aria-label="Seleção">
        <div className="mb-4">
          <label htmlFor="compare-prompt" className="mb-1.5 block text-sm font-medium">
            Prompt
          </label>
          <select
            id="compare-prompt"
            value={promptId ?? ""}
            onChange={select}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="" disabled>
              {listError ? "Falha ao carregar os prompts" : "Selecione um prompt"}
            </option>
            {options.map((prompt) => (
              <option key={prompt.id} value={prompt.id}>
                {prompt.name}
              </option>
            ))}
          </select>
        </div>

        {detail && versions.length >= 2 && (
          <VersionSelector
            versions={versions}
            before={before}
            after={after}
            onChange={(nextBefore, nextAfter) => {
              setBefore(nextBefore);
              setAfter(nextAfter);
            }}
          />
        )}
        {detail && versions.length < 2 && (
          <p className="rounded-lg border border-dashed border-slate-300 p-4 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
            Este prompt tem apenas {versions.length} versão. Crie uma nova versão para poder comparar.
          </p>
        )}
      </section>

      <section aria-live="polite" aria-busy={diff.status === "loading"}>
        {!promptId && (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
            Escolha um prompt para comparar duas versões.
          </p>
        )}

        {diff.status === "loading" && (
          <div className="space-y-2 rounded-xl border border-slate-200 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-900/60" aria-label="Carregando comparação">
            {[70, 90, 55, 80, 65].map((width, index) => (
              <div key={index} className="h-5 animate-pulse rounded bg-slate-200 dark:bg-slate-800" style={{ width: `${width}%` }} />
            ))}
          </div>
        )}

        {diff.status === "error" && (
          <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900 dark:bg-rose-950/60">
            <p className="font-medium text-rose-900 dark:text-rose-100">Não foi possível comparar as versões</p>
            <p className="mt-1 text-sm text-rose-700 dark:text-rose-300">{diff.message}</p>
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

        {diff.status === "ready" && (
          <>
            <h2 className="mb-2 text-sm font-medium text-slate-600 dark:text-slate-400">
              v{diff.data.version_number_before} → v{diff.data.version_number_after}
            </h2>
            {diff.data.has_changes ? (
              <DiffViewer lines={diff.data.lines} />
            ) : (
              <p className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
                Sem diferenças entre as duas versões.
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
