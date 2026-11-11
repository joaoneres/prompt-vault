import { ArrowLeftRight } from "lucide-react";
import type { PromptVersionResponse } from "../types";

interface Props {
  versions: PromptVersionResponse[];
  before: number | null;
  after: number | null;
  onChange: (before: number | null, after: number | null) => void;
  disabled?: boolean;
}

const select =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950";

const label = (version: PromptVersionResponse) =>
  `v${version.version_number}${version.is_active ? " · ativa" : ""} · ${new Date(version.created_at).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  })}`;

export default function VersionSelector({ versions, before, after, onChange, disabled = false }: Props) {
  const parse = (value: string) => (value === "" ? null : Number(value));

  const renderOptions = (other: number | null) =>
    versions.map((version) => (
      // The same version can't be on both sides: the API rejects it, so it isn't offered.
      <option key={version.id} value={version.version_number} disabled={version.version_number === other}>
        {label(version)}
      </option>
    ));

  return (
    <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[1fr_auto_1fr]">
      <div>
        <label htmlFor="version-before" className="mb-1.5 block text-sm font-medium">
          Base <span className="font-normal text-slate-500 dark:text-slate-400">(antes)</span>
        </label>
        <select
          id="version-before"
          value={before ?? ""}
          disabled={disabled}
          onChange={(event) => onChange(parse(event.target.value), after)}
          className={select}
        >
          <option value="" disabled>
            Selecione a versão base
          </option>
          {renderOptions(after)}
        </select>
      </div>

      <button
        type="button"
        onClick={() => onChange(after, before)}
        disabled={disabled || before === null || after === null}
        aria-label="Inverter base e comparada"
        title="Inverter"
        className="mx-auto inline-flex size-10 items-center justify-center rounded-lg border border-slate-300 text-slate-600 transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-500 disabled:opacity-40 sm:mb-0 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        <ArrowLeftRight className="size-4 rotate-90 sm:rotate-0" aria-hidden />
      </button>

      <div>
        <label htmlFor="version-after" className="mb-1.5 block text-sm font-medium">
          Comparada <span className="font-normal text-slate-500 dark:text-slate-400">(depois)</span>
        </label>
        <select
          id="version-after"
          value={after ?? ""}
          disabled={disabled}
          onChange={(event) => onChange(before, parse(event.target.value))}
          className={select}
        >
          <option value="" disabled>
            Selecione a versão comparada
          </option>
          {renderOptions(before)}
        </select>
      </div>
    </div>
  );
}
