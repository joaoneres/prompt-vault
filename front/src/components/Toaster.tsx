import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";

export type ToastKind = "success" | "error" | "info";
export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), []);

  const notify = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId.current++;
      setToasts((all) => [...all, { id, kind, message }]);
      setTimeout(() => dismiss(id), kind === "error" ? 6000 : 3500);
    },
    [dismiss],
  );

  return { toasts, dismiss, notify };
}

const styles: Record<ToastKind, { icon: typeof Info; classes: string }> = {
  success: {
    icon: CheckCircle2,
    classes: "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-100",
  },
  error: {
    icon: AlertCircle,
    classes: "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-100",
  },
  info: {
    icon: Info,
    classes: "border-indigo-200 bg-indigo-50 text-indigo-900 dark:border-indigo-900 dark:bg-indigo-950 dark:text-indigo-100",
  },
};

export default function Toaster({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 top-4 z-[60] flex flex-col items-center gap-2 px-4 sm:items-end sm:px-6"
    >
      {toasts.map(({ id, kind, message }) => {
        const { icon: Icon, classes } = styles[kind];
        return (
          <div
            key={id}
            role={kind === "error" ? "alert" : "status"}
            className={`animate-toast-in pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border p-3 shadow-lg ${classes}`}
          >
            <Icon className="mt-0.5 size-5 shrink-0" aria-hidden />
            <p className="flex-1 text-sm leading-snug">{message}</p>
            <button
              type="button"
              onClick={() => onDismiss(id)}
              aria-label="Fechar notificação"
              className="rounded p-0.5 opacity-60 transition hover:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              <X className="size-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
