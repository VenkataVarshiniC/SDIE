export function Stat({
  label,
  value,
  tone = "neutral",
  suffix,
}: {
  label: string;
  value: string;
  tone?: "neutral" | "up" | "down";
  suffix?: string;
}) {
  const toneClass =
    tone === "up" ? "text-signal-up" : tone === "down" ? "text-signal-down" : "text-parchment";

  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wider text-muted">{label}</span>
      <span className={`font-data text-2xl tabular-nums ${toneClass}`}>
        {value}
        {suffix && <span className="text-sm text-muted ml-1">{suffix}</span>}
      </span>
    </div>
  );
}
