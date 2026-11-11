import { X } from "lucide-react";
import { type ReactNode, useEffect, useId } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Blocks closing (Esc, backdrop, X) while a request is in flight. */
  busy?: boolean;
}

/** Shared dialog shell used by the create and detail modals. */
export default function Modal({ title, onClose, children, busy = false }: ModalProps) {
  const titleId = useId();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose, busy]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="animate-modal-in flex max-h-[92vh] w-full max-w-2xl flex-col rounded-t-2xl border border-slate-200 bg-white shadow-2xl sm:rounded-2xl dark:border-slate-800 dark:bg-slate-900"
      >
        <header className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h2 id={titleId} className="truncate text-lg font-semibold">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            aria-label="Fechar"
            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-500 disabled:opacity-40 dark:hover:bg-slate-800"
          >
            <X className="size-5" />
          </button>
        </header>
        <div className="overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}
