import type { ReactNode } from "react";

export function Panel({
  title,
  eyebrow,
  children,
  className = "",
}: {
  title?: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`bg-ink-1 border border-ink-border rounded-sm ${className}`}>
      {(title || eyebrow) && (
        <div className="px-5 pt-4 pb-3 border-b border-ink-border">
          {eyebrow && (
            <div className="text-[11px] uppercase tracking-wider text-ledger mb-1">{eyebrow}</div>
          )}
          {title && <h2 className="font-display text-[18px] text-parchment">{title}</h2>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}
