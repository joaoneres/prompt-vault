import { Loader2 } from "lucide-react";
import { useState } from "react";
import Modal from "./Modal";

interface Props {
  title: string;
  message: string;
  confirmLabel: string;
  tone?: "danger" | "primary";
  /** The caller closes the modal (unmounts it) when this resolves. */
  onConfirm: () => Promise<void>;
  onCancel: () => void;
}

const tones = {
  danger: "bg-rose-600 hover:bg-rose-500 focus-visible:outline-rose-500",
  primary: "bg-indigo-600 hover:bg-indigo-500 focus-visible:outline-indigo-500",
};

export default function ConfirmModal({ title, message, confirmLabel, tone = "primary", onConfirm, onCancel }: Props) {
  const [busy, setBusy] = useState(false);

  const confirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={title} onClose={onCancel} busy={busy}>
      <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{message}</p>
      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-500 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={() => void confirm()}
          disabled={busy}
          className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm transition focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${tones[tone]}`}
        >
          {busy && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
