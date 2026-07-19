import type { InputHTMLAttributes, LabelHTMLAttributes, ReactNode } from "react";

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="text-muted">{label}</span>
      {children}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`bg-ink-0 border border-ink-border rounded-sm px-3 py-2 font-data text-sm text-parchment
        focus:outline-none focus:border-ledger transition-colors ${props.className ?? ""}`}
    />
  );
}

export function Select({
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`bg-ink-0 border border-ink-border rounded-sm px-3 py-2 text-sm text-parchment
        focus:outline-none focus:border-ledger transition-colors ${props.className ?? ""}`}
    >
      {children}
    </select>
  );
}

export function Button({
  children,
  variant = "primary",
  ...props
}: {
  children: ReactNode;
  variant?: "primary" | "ghost";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base = "px-4 py-2 rounded-sm text-sm font-medium transition-colors disabled:opacity-40";
  const variantClass =
    variant === "primary"
      ? "bg-ledger-dim text-parchment hover:bg-ledger"
      : "border border-ink-border text-muted hover:text-parchment hover:border-parchment";
  return (
    <button {...props} className={`${base} ${variantClass} ${props.className ?? ""}`}>
      {children}
    </button>
  );
}

export type { LabelHTMLAttributes };
