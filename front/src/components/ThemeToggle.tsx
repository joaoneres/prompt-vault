import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

const isDark = () => document.documentElement.classList.contains("dark");

export default function ThemeToggle() {
  const [dark, setDark] = useState(isDark);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      /* the preference just won't be remembered */
    }
  }, [dark]);

  return (
    <button
      type="button"
      onClick={() => setDark((value) => !value)}
      aria-label={dark ? "Ativar modo claro" : "Ativar modo escuro"}
      title={dark ? "Modo claro" : "Modo escuro"}
      className="inline-flex size-10 items-center justify-center rounded-full border border-slate-200 bg-white/80 text-slate-700 shadow-sm backdrop-blur transition hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-200 dark:hover:bg-slate-800"
    >
      {dark ? <Sun className="size-5" /> : <Moon className="size-5" />}
    </button>
  );
}
