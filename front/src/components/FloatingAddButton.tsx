import { Plus } from "lucide-react";

export default function FloatingAddButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Adicionar novo prompt"
      title="Novo prompt"
      className="fixed bottom-6 right-6 z-40 inline-flex size-14 items-center justify-center rounded-full bg-indigo-600 text-white shadow-xl shadow-indigo-600/30 transition hover:scale-105 hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-500 active:scale-95 sm:bottom-8 sm:right-8"
    >
      <Plus className="size-7" strokeWidth={2.5} />
    </button>
  );
}
