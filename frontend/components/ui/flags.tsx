export function FlagsCallout({ flags }: { flags: string[] }) {
  if (flags.length === 0) return null;

  return (
    <div className="border border-amber-700/40 bg-amber-950/30 rounded-sm p-4 flex flex-col gap-2">
      <span className="text-[11px] uppercase tracking-wider text-amber-500">
        {flags.length === 1 ? "Assumption flag" : `Assumption flags (${flags.length})`}
      </span>
      <ul className="flex flex-col gap-2">
        {flags.map((flag, i) => (
          <li key={i} className="text-sm text-amber-200/90 leading-relaxed">
            {flag}
          </li>
        ))}
      </ul>
    </div>
  );
}
