/** Fixed decorative background: a grid, triangles and soft color blobs. Pure SVG/CSS. */
export default function GeometricBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-32 -top-32 size-[28rem] rounded-full bg-indigo-300/30 blur-3xl dark:bg-indigo-600/20" />
      <div className="absolute -bottom-40 -right-24 size-[30rem] rounded-full bg-fuchsia-300/25 blur-3xl dark:bg-fuchsia-600/15" />

      <svg className="absolute inset-0 size-full text-slate-400/25 dark:text-slate-500/20">
        <defs>
          <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" fill="none" stroke="currentColor" strokeWidth="1" />
          </pattern>
          <pattern id="shapes" width="240" height="240" patternUnits="userSpaceOnUse">
            <polygon points="30,70 70,70 50,36" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <rect x="150" y="40" width="34" height="34" fill="none" stroke="currentColor" strokeWidth="1.5" transform="rotate(18 167 57)" />
            <circle cx="60" cy="180" r="18" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <polygon points="170,170 196,185 196,215 170,230 144,215 144,185" fill="none" stroke="currentColor" strokeWidth="1.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <rect width="100%" height="100%" fill="url(#shapes)" className="text-indigo-500/40 dark:text-indigo-400/25" />
      </svg>

      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-slate-50 dark:to-slate-950" />
    </div>
  );
}
