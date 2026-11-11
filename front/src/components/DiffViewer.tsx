import { Columns2, Rows3 } from "lucide-react";
import { useMemo, useState } from "react";
import type { DiffLineResponse } from "../types";

type Mode = "split" | "unified";
type Kind = DiffLineResponse["kind"];

const tone: Record<string, { row: string; num: string; sign: string }> = {
  added: {
    row: "bg-emerald-50 dark:bg-emerald-950/40",
    num: "bg-emerald-100/80 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    sign: "text-emerald-600 dark:text-emerald-400",
  },
  removed: {
    row: "bg-rose-50 dark:bg-rose-950/40",
    num: "bg-rose-100/80 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
    sign: "text-rose-600 dark:text-rose-400",
  },
  unchanged: {
    row: "",
    num: "text-slate-400 dark:text-slate-500",
    sign: "text-transparent",
  },
  empty: {
    row: "bg-slate-50/70 dark:bg-slate-900/40",
    num: "bg-slate-50/70 dark:bg-slate-900/40",
    sign: "text-transparent",
  },
};

const SIGN: Record<string, string> = { added: "+", removed: "−", unchanged: " " };
const toneOf = (kind: Kind) => tone[kind] ?? tone.unchanged;

interface Row {
  left?: DiffLineResponse;
  right?: DiffLineResponse;
}

/** Pairs each run of removed lines with the added lines that follow it, side by side. */
function toRows(lines: DiffLineResponse[]): Row[] {
  const rows: Row[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.kind === "unchanged") {
      rows.push({ left: line, right: line });
      i += 1;
      continue;
    }
    const removed: DiffLineResponse[] = [];
    const added: DiffLineResponse[] = [];
    while (i < lines.length && lines[i].kind !== "unchanged") {
      (lines[i].kind === "removed" ? removed : added).push(lines[i]);
      i += 1;
    }
    for (let k = 0; k < Math.max(removed.length, added.length); k += 1) {
      rows.push({ left: removed[k], right: added[k] });
    }
  }
  return rows;
}

const numCell = "w-12 min-w-12 select-none px-2 text-right align-top text-xs leading-6";
const textCell = "whitespace-pre px-2 align-top leading-6";
// Split view: two equal halves. The table is at least as wide as two copies of the longest line
// (monospace, so `ch` is exact) and the wrapper scrolls horizontally instead of overlapping text.
const halfCell = textCell;
const HALF_CHROME_REM = 6; // line number + sign + padding of one half

function Num({ value, kind }: { value: number | null | undefined; kind: string }) {
  return <td className={`${numCell} ${toneOf(kind).num}`}>{value ?? ""}</td>;
}

function Unified({ lines }: { lines: DiffLineResponse[] }) {
  return (
    <table className="w-full border-collapse">
      <tbody>
        {lines.map((line, index) => {
          const t = toneOf(line.kind);
          return (
            <tr key={index} className={t.row} aria-label={line.kind === "added" ? "Linha adicionada" : line.kind === "removed" ? "Linha removida" : undefined}>
              <Num value={line.line_number_before} kind={line.kind} />
              <Num value={line.line_number_after} kind={line.kind} />
              <td className={`w-5 select-none text-center align-top leading-6 ${t.sign}`}>{SIGN[line.kind] ?? " "}</td>
              <td className={textCell}>{line.content || " "}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Split({ lines }: { lines: DiffLineResponse[] }) {
  const rows = useMemo(() => toRows(lines), [lines]);
  const longest = useMemo(() => lines.reduce((max, line) => Math.max(max, line.content.length), 0), [lines]);
  return (
    <table
      className="w-full table-fixed border-collapse"
      style={{ minWidth: `calc(${2 * longest}ch + ${2 * HALF_CHROME_REM}rem)` }}
    >
      <colgroup>
        <col className="w-12" />
        <col className="w-5" />
        <col />
        <col className="w-12" />
        <col className="w-5" />
        <col />
      </colgroup>
      <tbody>
        {rows.map(({ left, right }, index) => {
          const lt = left ? toneOf(left.kind) : tone.empty;
          const rt = right ? toneOf(right.kind) : tone.empty;
          return (
            <tr key={index}>
              <td className={`${numCell} ${lt.num}`}>{left?.line_number_before ?? ""}</td>
              <td className={`select-none text-center align-top leading-6 ${lt.row} ${lt.sign}`}>{left ? SIGN[left.kind] : ""}</td>
              <td className={`${halfCell} ${lt.row} border-r border-slate-200 dark:border-slate-800`}>{left ? left.content || " " : ""}</td>
              <td className={`${numCell} ${rt.num}`}>{right?.line_number_after ?? ""}</td>
              <td className={`select-none text-center align-top leading-6 ${rt.row} ${rt.sign}`}>{right ? SIGN[right.kind] : ""}</td>
              <td className={`${halfCell} ${rt.row}`}>{right ? right.content || " " : ""}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function DiffViewer({ lines }: { lines: DiffLineResponse[] }) {
  const [mode, setMode] = useState<Mode>("split");
  const added = lines.filter((line) => line.kind === "added").length;
  const removed = lines.filter((line) => line.kind === "removed").length;

  const toggle = (value: Mode, text: string, Icon: typeof Columns2) => (
    <button
      type="button"
      onClick={() => setMode(value)}
      aria-pressed={mode === value}
      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition focus-visible:outline-2 focus-visible:outline-indigo-500 ${
        mode === value
          ? "bg-white text-indigo-700 shadow-sm dark:bg-slate-700 dark:text-indigo-200"
          : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
      }`}
    >
      <Icon className="size-3.5" aria-hidden />
      {text}
    </button>
  );

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-900">
        <p className="text-xs font-medium" aria-label={`${added} linhas adicionadas, ${removed} removidas`}>
          <span className="text-emerald-600 dark:text-emerald-400">+{added}</span>{" "}
          <span className="text-rose-600 dark:text-rose-400">−{removed}</span>
        </p>
        <div role="group" aria-label="Modo de visualização" className="flex rounded-lg bg-slate-200/70 p-0.5 dark:bg-slate-800">
          {toggle("split", "Dividido", Columns2)}
          {toggle("unified", "Unificado", Rows3)}
        </div>
      </div>
      <div className="overflow-x-auto font-mono text-[13px]">
        {lines.length === 0 ? null : mode === "split" ? <Split lines={lines} /> : <Unified lines={lines} />}
      </div>
    </div>
  );
}
