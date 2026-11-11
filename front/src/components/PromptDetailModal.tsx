import { Check, Copy, Loader2, Pencil } from "lucide-react";
import { useState } from "react";
import { updateContent } from "../api/prompts";
import { errorMessage } from "../api/client";
import { activeVersion, type PromptItem } from "../types";
import Modal from "./Modal";

interface Props {
  prompt: PromptItem;
  onClose: () => void;
  /** Called after a new version was saved so the parent can reload the prompt. */
  onSaved: (promptId: string) => Promise<void>;
  onNotify: (kind: "success" | "error", message: string) => void;
}

const button =
  "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
const secondary = `${button} border border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800`;
const primary = `${button} bg-indigo-600 font-semibold text-white shadow-sm hover:bg-indigo-500`;

export default function PromptDetailModal({ prompt, onClose, onSaved, onNotify }: Props) {
  const active = activeVersion(prompt);
  const current = active?.content ?? "";

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(current);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  const changed = draft.trim() !== "" && draft !== current;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(current);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
      onNotify("success", "Conteúdo copiado para a área de transferência.");
    } catch {
      onNotify("error", "Não foi possível copiar o conteúdo.");
    }
  };

  const startEditing = () => {
    setDraft(current);
    setEditing(true);
  };

  const save = async () => {
    if (!changed || saving) return;
    setSaving(true);
    try {
      const version = await updateContent(prompt.id, draft);
      await onSaved(prompt.id);
      onNotify("success", `Nova versão v${version.version_number} salva e ativada.`);
      onClose();
    } catch (error) {
      onNotify("error", errorMessage(error));
      setSaving(false);
    }
  };

  return (
    <Modal title={prompt.name} onClose={onClose} busy={saving}>
      <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
        <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
          {active ? `v${active.version_number} ativa` : "sem versão ativa"}
        </span>
        {prompt.versions && <span>{prompt.versions.length} versão(ões)</span>}
        <span>Atualizado em {new Date(prompt.updated_at).toLocaleString("pt-BR")}</span>
      </div>

      {editing ? (
        <>
          <label htmlFor="edit-content" className="sr-only">
            Conteúdo do prompt
          </label>
          <textarea
            id="edit-content"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            disabled={saving}
            rows={14}
            autoFocus
            className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950"
          />
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Salvar cria uma nova versão e a torna a versão ativa. O histórico é preservado.
          </p>
        </>
      ) : active ? (
        <pre className="max-h-[50vh] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-slate-50 p-4 font-mono text-sm leading-relaxed dark:border-slate-800 dark:bg-slate-950">
          {current}
        </pre>
      ) : (
        <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700">
          Não há versão ativa para exibir.
        </p>
      )}

      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        {editing ? (
          <>
            <button type="button" onClick={() => setEditing(false)} disabled={saving} className={secondary}>
              Cancelar
            </button>
            <button type="button" onClick={save} disabled={!changed || saving} className={primary}>
              {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
              Salvar nova versão
            </button>
          </>
        ) : (
          <>
            <button type="button" onClick={startEditing} disabled={!active} className={secondary}>
              <Pencil className="size-4" aria-hidden />
              Editar
            </button>
            <button type="button" onClick={copy} disabled={!active} className={primary}>
              {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
              {copied ? "Copiado" : "Copiar"}
            </button>
          </>
        )}
      </div>
    </Modal>
  );
}
