import { Check, Copy, Loader2, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { addVersion, updateContent } from "../api/prompts";
import { errorMessage } from "../api/client";
import { activeVersion, type PromptItem } from "../types";
import ConfirmModal from "./ConfirmModal";
import Modal from "./Modal";

interface Props {
  prompt: PromptItem;
  onClose: () => void;
  /** Called after a new version was saved so the parent can reload the prompt. */
  onSaved: (promptId: string) => Promise<void>;
  /** Soft deletes the prompt. The parent removes it from the list and closes this modal. */
  onDelete: (promptId: string) => Promise<void>;
  onNotify: (kind: "success" | "error", message: string) => void;
}

const button =
  "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
const secondary = `${button} border border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800`;
const primary = `${button} bg-indigo-600 font-semibold text-white shadow-sm hover:bg-indigo-500`;

export default function PromptDetailModal({ prompt, onClose, onSaved, onDelete, onNotify }: Props) {
  const active = activeVersion(prompt);
  const current = active?.content ?? "";

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(current);
  const [saving, setSaving] = useState<"activate" | "draft" | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
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

  /** "Salvar e ativar" creates the version and makes it active; "sem ativar" only creates it. */
  const save = async (activate: boolean) => {
    if (!changed || saving) return;
    setSaving(activate ? "activate" : "draft");
    try {
      const version = activate ? await updateContent(prompt.id, draft) : await addVersion(prompt.id, draft);
      await onSaved(prompt.id);
      onNotify(
        "success",
        activate
          ? `Nova versão v${version.version_number} salva e ativada.`
          : `Versão v${version.version_number} criada (não ativada).`,
      );
      onClose();
    } catch (error) {
      onNotify("error", errorMessage(error));
      setSaving(null);
    }
  };

  return (
    <Modal title={prompt.name} onClose={onClose} busy={saving !== null || confirmingDelete}>
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
            disabled={saving !== null}
            rows={14}
            autoFocus
            className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950"
          />
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            "Salvar e ativar" cria uma nova versão e a torna a versão em uso. "Salvar sem ativar" só guarda a versão no histórico. O histórico é sempre preservado.
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
            <button type="button" onClick={() => setEditing(false)} disabled={saving !== null} className={secondary}>
              Cancelar
            </button>
            <button type="button" onClick={() => void save(false)} disabled={!changed || saving !== null} className={secondary}>
              {saving === "draft" && <Loader2 className="size-4 animate-spin" aria-hidden />}
              Salvar sem ativar
            </button>
            <button type="button" onClick={() => void save(true)} disabled={!changed || saving !== null} className={primary}>
              {saving === "activate" && <Loader2 className="size-4 animate-spin" aria-hidden />}
              Salvar e ativar
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              aria-label={`Excluir ${prompt.name}`}
              className={`${button} text-rose-600 hover:bg-rose-50 sm:mr-auto dark:text-rose-400 dark:hover:bg-rose-950/50`}
            >
              <Trash2 className="size-4" aria-hidden />
              Excluir
            </button>
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
      {confirmingDelete && (
        <ConfirmModal
          title="Excluir prompt?"
          message={`Excluir "${prompt.name}"? As versões serão preservadas e o prompt poderá ser recuperado na lixeira.`}
          confirmLabel="Excluir"
          tone="danger"
          onCancel={() => setConfirmingDelete(false)}
          onConfirm={async () => {
            try {
              await onDelete(prompt.id);
            } finally {
              // On success the parent unmounts this modal; on error just return to it.
              setConfirmingDelete(false);
            }
          }}
        />
      )}
    </Modal>
  );
}
