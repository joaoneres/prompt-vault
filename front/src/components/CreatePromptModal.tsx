import { Loader2 } from "lucide-react";
import { type FormEvent, useState } from "react";
import { createPrompt } from "../api/prompts";
import { errorMessage } from "../api/client";
import type { PromptResponse } from "../types";
import Modal from "./Modal";

interface Props {
  onClose: () => void;
  onCreated: (prompt: PromptResponse) => void;
  onError: (message: string) => void;
}

const field =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950 dark:placeholder:text-slate-500";

export default function CreatePromptModal({ onClose, onCreated, onError }: Props) {
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  const valid = name.trim() !== "" && content.trim() !== "";

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid || saving) return;
    setSaving(true);
    try {
      const created = await createPrompt({ name: name.trim(), content });
      onCreated(created);
    } catch (error) {
      onError(errorMessage(error));
      setSaving(false);
    }
  };

  return (
    <Modal title="Novo prompt" onClose={onClose} busy={saving}>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label htmlFor="prompt-name" className="mb-1.5 block text-sm font-medium">
            Nome
          </label>
          <input
            id="prompt-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={saving}
            autoFocus
            maxLength={200}
            placeholder="Ex.: Resumo de reunião"
            className={field}
          />
        </div>
        <div>
          <label htmlFor="prompt-content" className="mb-1.5 block text-sm font-medium">
            Conteúdo
          </label>
          <textarea
            id="prompt-content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={saving}
            rows={10}
            placeholder="Escreva o conteúdo do prompt..."
            className={`${field} resize-y font-mono`}
          />
        </div>
        <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-500 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={!valid || saving}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
            Criar Prompt
          </button>
        </div>
      </form>
    </Modal>
  );
}
